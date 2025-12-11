"""Multi-device parallel/sequential runner for DroidAgent."""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from droidrun import AdbTools, DroidAgent
from droidrun.agent.droid.events import (
    ExecutorResultEvent,
    ManagerPlanEvent,
    CodeActResultEvent,
    ScripterExecutorResultEvent,
)
from llama_index.llms.openai_like import OpenAILike
from droidrun.config_manager.config_manager import (
    DroidrunConfig,
    AgentConfig,
    CodeActConfig,
    ManagerConfig,
    ExecutorConfig,
)

from .device_manager import ConnectedDevice
from .device_logger import DeviceLogger, ConsoleOutput


class TaskResult:
    """Store result of a device task execution."""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.success = False
        self.output = ""
        self.error = ""
        self.duration = 0.0
        self.steps_used = 0
        self.trajectory_path = ""
        self.log_path = ""


class MultiDeviceRunner:
    """Run DroidAgent tasks across multiple devices with concurrency control."""

    def __init__(
        self,
        devices: List[ConnectedDevice],
        goal: str,
        llm_config: Dict[str, str],
        agent_config: DroidrunConfig,
        concurrency: int = 1,
    ):
        """Initialize multi-device runner.

        Args:
            devices: List of connected devices.
            goal: Task goal/objective.
            llm_config: LLM configuration (api_base, api_key, model).
            agent_config: DroidAgent configuration.
            concurrency: Maximum concurrent tasks (1 = sequential).
        """
        self.devices = devices
        self.goal = goal
        self.llm_config = llm_config
        self.agent_config = agent_config
        self.concurrency = concurrency
        self.device_logger: Optional[DeviceLogger] = None
        self.console: Optional[ConsoleOutput] = None

    async def run_all(self) -> List[TaskResult]:
        """Run tasks on all devices with concurrency control.

        Returns:
            List of TaskResult objects.
        """
        # Initialize logging
        self.device_logger = DeviceLogger()
        self.console = ConsoleOutput(
            goal=self.goal,
            concurrency=self.concurrency,
            device_count=len(self.devices),
        )

        # Print header
        self.console.print_header()
        self.device_logger.start()

        try:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.concurrency)

            # Create tasks for all devices
            tasks = [
                self._run_device_task(device, semaphore)
                for device in self.devices
            ]

            # Run all tasks and gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            task_results = []
            for result in results:
                if isinstance(result, TaskResult):
                    task_results.append(result)
                elif isinstance(result, Exception):
                    err_result = TaskResult("unknown")
                    err_result.error = str(result)
                    task_results.append(err_result)

        finally:
            # Close all log handlers
            self.device_logger.close_all()

        # Print summary
        success_count = sum(1 for r in task_results if r.success)
        self.console.print_summary(success_count, len(task_results))

        return task_results

    async def _run_device_task(
        self,
        device: ConnectedDevice,
        semaphore: asyncio.Semaphore,
    ) -> TaskResult:
        """Run task on a single device.

        Args:
            device: Connected device.
            semaphore: Semaphore for concurrency control.

        Returns:
            TaskResult object.
        """
        result = TaskResult(device.name)

        # Get device-specific logger
        logger = self.device_logger.get_logger(device.name)
        log_path = self.device_logger.get_log_path(device.name)
        result.log_path = str(log_path)

        # Print started message
        self.console.print_device_started(device.name, log_path)

        logger.info(f"Task started for device: {device.name}")
        logger.info(f"Serial: {device.serial}")
        logger.info(f"Type: {device.device_type}")
        logger.info(f"Description: {device.description}")
        logger.info(f"Goal: {self.goal}")
        logger.info("-" * 40)

        async with semaphore:
            start_time = time.time()

            try:
                # Initialize tools
                logger.info("Initializing ADB tools...")
                tools = AdbTools(serial=device.serial)

                # Initialize LLM
                logger.info(f"Initializing LLM: {self.llm_config['model']}")
                llm = OpenAILike(
                    api_base=self.llm_config["api_base"],
                    api_key=self.llm_config["api_key"],
                    model=self.llm_config["model"],
                    is_chat_model=True,
                )

                # Create trajectory folder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                trajectory_path = Path("trajectories") / f"{device.name}_{timestamp}"
                result.trajectory_path = str(trajectory_path)

                # Create agent
                logger.info("Creating DroidAgent...")
                agent = DroidAgent(
                    goal=self.goal,
                    llms=llm,
                    tools=tools,
                    config=self.agent_config,
                )

                # Run agent with logging
                logger.info("Starting task execution...")
                agent_result = await self._run_agent_with_logging(agent, device.name, logger)

                # Store results
                result.success = agent_result.get("success", False)
                result.output = agent_result.get("output", "")
                result.duration = time.time() - start_time

                # Get steps used
                if hasattr(agent, "shared_state") and hasattr(agent.shared_state, "step_number"):
                    result.steps_used = agent.shared_state.step_number

                logger.info("-" * 40)
                logger.info(f"Task completed: success={result.success}")
                logger.info(f"Steps: {result.steps_used}")
                logger.info(f"Duration: {result.duration:.1f}s")
                if result.output:
                    logger.info(f"Output: {result.output}")

            except Exception as e:
                result.success = False
                result.error = str(e)
                result.duration = time.time() - start_time
                logger.error(f"Task failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Print completion message
        self.console.print_device_done(
            device.name,
            result.success,
            result.steps_used,
            result.duration,
            result.error,
        )

        return result

    async def _run_agent_with_logging(
        self,
        agent: DroidAgent,
        device_name: str,
        logger: "logging.Logger",  # noqa: F821
    ) -> Dict[str, Any]:
        """Run agent and log progress.

        Args:
            agent: DroidAgent instance.
            device_name: Device name.
            logger: Logger instance for this device.

        Returns:
            Agent result dictionary.
        """
        # Run agent with event streaming
        handler = agent.run()

        last_step = 0

        max_steps = self.agent_config.agent.max_steps if self.agent_config.agent else 100

        # Stream events to log progress
        async for event in handler.stream_events():
            # Log based on event type
            if isinstance(event, ExecutorResultEvent):
                # Executor completed an action
                current_step = agent.shared_state.step_number if hasattr(agent, "shared_state") else last_step
                summary = event.summary or "(action completed)"
                outcome = "✓" if event.outcome else "✗"
                logger.info(f"Step {current_step}/{max_steps} [{outcome}]: {summary}")
                if event.error:
                    logger.warning(f"  Error: {event.error}")
                last_step = current_step

            elif isinstance(event, ManagerPlanEvent):
                # Manager made a plan
                if event.current_subgoal:
                    logger.info(f"Subgoal: {event.current_subgoal}")
                if event.thought:
                    thought_preview = event.thought[:150] + "..." if len(event.thought) > 150 else event.thought
                    logger.debug(f"Thought: {thought_preview}")

            elif isinstance(event, CodeActResultEvent):
                # CodeAct mode result
                current_step = agent.shared_state.step_number if hasattr(agent, "shared_state") else last_step
                outcome = "✓" if event.success else "✗"
                logger.info(f"Step {current_step}/{max_steps} [{outcome}]: {event.reason}")
                last_step = current_step

            elif isinstance(event, ScripterExecutorResultEvent):
                # Scripter result
                outcome = "✓" if event.success else "✗"
                logger.info(f"Script [{outcome}]: {event.message}")

        # Wait for final result
        result = await handler

        return result
