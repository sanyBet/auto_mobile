"""Multi-device parallel/sequential runner for DroidAgent."""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from droidrun import AdbTools, DroidAgent
from llama_index.llms.openai_like import OpenAILike
from droidrun.config_manager.config_manager import (
    DroidrunConfig,
    AgentConfig,
    CodeActConfig,
    ManagerConfig,
    ExecutorConfig,
)

from .device_manager import ConnectedDevice


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

    async def run_all(self) -> List[TaskResult]:
        """Run tasks on all devices with concurrency control.

        Returns:
            List of TaskResult objects.
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting batch execution")
        print(f"📱 Devices: {len(self.devices)}")
        print(f"⚙️  Concurrency: {self.concurrency}")
        print(f"🎯 Goal: {self.goal[:80]}{'...' if len(self.goal) > 80 else ''}")
        print(f"{'='*60}\n")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.concurrency)

        # Create tasks for all devices
        tasks = [
            self._run_device_task(device, idx + 1, len(self.devices), semaphore)
            for idx, device in enumerate(self.devices)
        ]

        # Run all tasks and gather results
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        # Process results
        task_results = []
        for result in results:
            if isinstance(result, TaskResult):
                task_results.append(result)
            elif isinstance(result, Exception):
                print(f"❌ Task error: {result}")

        # Print summary
        self._print_summary(task_results, total_duration)

        return task_results

    async def _run_device_task(
        self,
        device: ConnectedDevice,
        index: int,
        total: int,
        semaphore: asyncio.Semaphore,
    ) -> TaskResult:
        """Run task on a single device.

        Args:
            device: Connected device.
            index: Device index (1-based).
            total: Total number of devices.
            semaphore: Semaphore for concurrency control.

        Returns:
            TaskResult object.
        """
        result = TaskResult(device.name)

        async with semaphore:
            print(f"\n[{index}/{total}] 📱 {device.name}")
            print(f"  ├─ Serial: {device.serial}")
            print(f"  ├─ Type: {device.device_type}")
            print(f"  └─ Description: {device.description}")

            start_time = time.time()

            try:
                # Initialize tools
                tools = AdbTools(serial=device.serial)

                # Initialize LLM
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
                print(f"  🤖 Initializing DroidAgent...")
                agent = DroidAgent(
                    goal=self.goal,
                    llms=llm,
                    tools=tools,
                    config=self.agent_config,
                )

                # Run agent
                print(f"  ▶️  Executing task...")
                agent_result = await agent.run()

                # Debug: Print full agent_result
                print(f"  🐛 Debug - agent_result keys: {list(agent_result.keys())}")
                print(f"  🐛 Debug - success value: {agent_result.get('success')} (type: {type(agent_result.get('success'))})")
                if "reason" in agent_result:
                    print(f"  🐛 Debug - reason: {agent_result.get('reason')}")

                # Store results
                result.success = agent_result.get("success", False)
                result.output = agent_result.get("output", "")
                result.duration = time.time() - start_time

                # Try to get steps used (if available)
                if hasattr(agent, "steps_taken"):
                    result.steps_used = agent.steps_taken

                status = "✅ Success" if result.success else "⚠️  Completed with issues"
                print(f"  {status} (took {result.duration:.1f}s)")

            except Exception as e:
                result.success = False
                result.error = str(e)
                result.duration = time.time() - start_time
                print(f"  ❌ Failed: {e}")

        return result

    def _print_summary(self, results: List[TaskResult], total_duration: float) -> None:
        """Print execution summary.

        Args:
            results: List of task results.
            total_duration: Total execution time.
        """
        print(f"\n{'='*60}")
        print("📊 Execution Summary")
        print(f"{'='*60}\n")

        # Print individual results
        success_count = 0
        for result in results:
            if result.success:
                print(f"✅ [{result.device_name}] Success")
                success_count += 1
            else:
                print(f"❌ [{result.device_name}] Failed")

            print(f"   ├─ Duration: {result.duration:.1f}s")
            if result.steps_used > 0:
                print(f"   ├─ Steps: {result.steps_used}")
            if result.trajectory_path:
                print(f"   ├─ Logs: {result.trajectory_path}")
            if result.error:
                print(f"   └─ Error: {result.error}")
            else:
                print(f"   └─ Output: {result.output[:100]}{'...' if len(result.output) > 100 else ''}")
            print()

        # Print overall statistics
        print(f"{'='*60}")
        print(f"✅ Successful: {success_count}/{len(results)}")
        print(f"❌ Failed: {len(results) - success_count}/{len(results)}")
        print(f"⏱️  Total time: {total_duration:.1f}s")
        mode = "sequential" if self.concurrency == 1 else f"parallel (concurrency={self.concurrency})"
        print(f"⚙️  Mode: {mode}")
        print(f"{'='*60}\n")
