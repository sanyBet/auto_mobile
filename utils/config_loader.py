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

    def _get_llm_provider(self) -> str:
        """获取 LLM 提供商类型。

        Returns:
            str: 'openrouter' 或 'packyapi'，默认 'openrouter'

        Raises:
            ValueError: 如果提供商名称无效
        """
        provider = os.getenv("LLM_PROVIDER", "openrouter").lower()

        if provider not in ["openrouter", "packyapi"]:
            raise ValueError(
                f"无效的 LLM_PROVIDER: {provider}\n"
                f"有效值: openrouter, packyapi"
            )

        return provider

    def _get_packyapi_config(self) -> Dict[str, Any]:
        """获取 PackyAPI 配置。

        Returns:
            字典包含: api_base, api_key, model, needs_custom_transport

        Raises:
            ValueError: 如果必需的环境变量缺失
        """
        base_url = os.getenv("PACKYAPI_BASE_URL")
        api_key = os.getenv("PACKYAPI_API_KEY")
        model = os.getenv("PACKYAPI_MODEL", "gpt-5.1")

        if not base_url:
            raise ValueError(
                "PACKYAPI_BASE_URL 未设置。\n"
                "请在 .env 文件中添加:\n"
                "  PACKYAPI_BASE_URL=https://www.packyapi.com/v1"
            )

        if not api_key:
            raise ValueError(
                "PACKYAPI_API_KEY 未设置。\n"
                "请在 .env 文件中添加:\n"
                "  PACKYAPI_API_KEY=your_key_here"
            )

        return {
            "api_base": base_url,
            "api_key": api_key,
            "model": model,
            "needs_custom_transport": True,  # PackyAPI 需要修改 User-Agent
        }

    def get_api_config(self) -> Dict[str, Any]:
        """获取 API 配置（根据 LLM_PROVIDER 自动选择提供商）。

        Returns:
            字典包含: api_base, api_key, model, needs_custom_transport
            - needs_custom_transport (bool): 是否需要自定义 http_client

        Raises:
            ValueError: 如果必需的环境变量缺失或提供商无效
        """
        provider = self._get_llm_provider()

        if provider == "packyapi":
            return self._get_packyapi_config()
        else:  # openrouter
            api_key = os.getenv("OPENROUTER_API_KEY")
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

            if not api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY 未在环境变量中找到。\n"
                    "请在 .env 文件中添加:\n"
                    "  OPENROUTER_API_KEY=your_key_here"
                )

            return {
                "api_base": "https://openrouter.ai/api/v1",
                "api_key": api_key,
                "model": model,
                "needs_custom_transport": False,  # OpenRouter 不需要自定义传输
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

    def get_enabled_devices(self, device_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get devices from configuration.

        Args:
            device_name: If specified, return only this device (ignores enabled flag).
                         If None, returns all enabled devices.

        Returns:
            Dictionary of devices with their configurations.

        Raises:
            ValueError: If specified device_name not found.
        """
        config = self.load_devices_config()
        devices = config.get("devices", {})

        # Single device mode
        if device_name:
            if device_name not in devices:
                available = ", ".join(devices.keys())
                raise ValueError(f"Device '{device_name}' not found. Available: {available}")
            return {device_name: devices[device_name]}

        # Default: return all enabled devices
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
