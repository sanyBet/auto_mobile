"""Configuration loader for environment variables and device configs."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import yaml


@dataclass
class TaskConfig:
    """Task configuration from devices.yaml."""

    name: str
    goal: str
    max_steps: int = 200
    reasoning: bool = False


class ConfigLoader:
    """Load and manage configuration from .env and devices.yaml."""

    def __init__(self, project_root: Path = None):
        """Initialize config loader.

        Args:
            project_root: Project root directory. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.env_file = self.project_root / ".env"
        self.devices_file = self.project_root / "devices.yaml"

        # Load environment variables
        if self.env_file.exists():
            load_dotenv(self.env_file)

    def get_api_config(self) -> Dict[str, str]:
        """Get API configuration from environment variables.

        Returns:
            Dictionary with api_base, api_key, and model.

        Raises:
            ValueError: If required environment variables are missing.
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables. "
                "Please create a .env file with your API key."
            )

        return {
            "api_base": "https://openrouter.ai/api/v1",
            "api_key": api_key,
            "model": model,
        }

    def load_devices_config(self) -> Dict[str, Any]:
        """Load device configuration from devices.yaml.

        Returns:
            Dictionary with devices configuration.

        Raises:
            FileNotFoundError: If devices.yaml does not exist.
            ValueError: If devices.yaml is invalid.
        """
        if not self.devices_file.exists():
            raise FileNotFoundError(
                f"Device configuration file not found: {self.devices_file}\n"
                "Please create devices.yaml based on devices.yaml.example"
            )

        try:
            with open(self.devices_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "devices" not in config:
                raise ValueError("Invalid devices.yaml: 'devices' section is required")

            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse devices.yaml: {e}")

    def get_enabled_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get only enabled devices from configuration.

        Returns:
            Dictionary of enabled devices with their configurations.
        """
        config = self.load_devices_config()
        devices = config.get("devices", {})

        return {
            name: device_config
            for name, device_config in devices.items()
            if device_config.get("enabled", False)
        }

    def get_concurrency(self) -> int:
        """Get maximum concurrency setting.

        Returns:
            Maximum number of concurrent device operations.
        """
        config = self.load_devices_config()
        return config.get("concurrency", 1)

    def get_task_config(self, task_name: Optional[str] = None) -> TaskConfig:
        """Get task configuration by name or active task.

        Args:
            task_name: Task name to load. If None, uses active_task from config.

        Returns:
            TaskConfig object with goal, max_steps, and reasoning.

        Raises:
            ValueError: If task not found or no active_task configured.
        """
        config = self.load_devices_config()
        tasks = config.get("tasks", {})

        if not tasks:
            raise ValueError(
                "No 'tasks' section found in devices.yaml. "
                "Please define tasks with goal, max_steps, and reasoning."
            )

        # Determine which task to use
        name = task_name or config.get("active_task")
        if not name:
            raise ValueError(
                "No task specified and no 'active_task' configured in devices.yaml."
            )

        if name not in tasks:
            available = ", ".join(tasks.keys())
            raise ValueError(
                f"Task '{name}' not found. Available tasks: {available}"
            )

        task_data = tasks[name]
        return TaskConfig(
            name=name,
            goal=task_data.get("goal", ""),
            max_steps=task_data.get("max_steps", 200),
            reasoning=task_data.get("reasoning", False),
        )

    def list_tasks(self) -> Dict[str, str]:
        """List all available tasks with their descriptions.

        Returns:
            Dictionary mapping task names to their goal summaries.
        """
        config = self.load_devices_config()
        tasks = config.get("tasks", {})
        return {
            name: task.get("goal", "")[:50] + "..."
            for name, task in tasks.items()
        }
