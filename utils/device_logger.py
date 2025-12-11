"""Device-specific file logging for multi-device execution."""

import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from threading import Lock


class DeviceLogger:
    """Manage separate log files for each device."""

    def __init__(self, log_dir: str = "logs"):
        """Initialize device logger.

        Args:
            log_dir: Directory for log files.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_files: Dict[str, Path] = {}
        self.start_time: Optional[float] = None
        self._lock = Lock()

    def get_logger(self, device_name: str) -> logging.Logger:
        """Get or create a logger for a device.

        Args:
            device_name: Device name.

        Returns:
            Logger instance for this device.
        """
        with self._lock:
            if device_name not in self.loggers:
                # Create timestamp for log file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = self.log_dir / f"{device_name}_{timestamp}.log"
                self.log_files[device_name] = log_file

                # Create logger
                logger = logging.getLogger(f"device.{device_name}")
                logger.setLevel(logging.DEBUG)
                logger.handlers.clear()  # Remove any existing handlers

                # File handler
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S"
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

                # Prevent propagation to root logger
                logger.propagate = False

                self.loggers[device_name] = logger

            return self.loggers[device_name]

    def get_log_path(self, device_name: str) -> Optional[Path]:
        """Get log file path for a device.

        Args:
            device_name: Device name.

        Returns:
            Path to log file, or None if not created yet.
        """
        return self.log_files.get(device_name)

    def start(self) -> None:
        """Start timing."""
        self.start_time = time.time()

    def get_elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    def close_all(self) -> None:
        """Close all log file handlers."""
        with self._lock:
            for logger in self.loggers.values():
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


class ConsoleOutput:
    """Simple console output for terminal display."""

    def __init__(self, goal: str, concurrency: int, device_count: int):
        """Initialize console output.

        Args:
            goal: Task goal description.
            concurrency: Maximum concurrent executions.
            device_count: Number of devices.
        """
        self.goal = goal
        self.concurrency = concurrency
        self.device_count = device_count
        self.start_time: Optional[float] = None

    def print_header(self) -> None:
        """Print execution header."""
        self.start_time = time.time()
        goal_preview = self.goal[:60] + "..." if len(self.goal) > 60 else self.goal

        print()
        print("🚀 DroidRun Multi-Device Automation")
        print(f"📱 Devices: {self.device_count} | ⚙️ Concurrency: {self.concurrency}")
        print(f"🎯 Goal: {goal_preview}")
        print("=" * 60)
        print()

    def print_device_started(self, device_name: str, log_path: Path) -> None:
        """Print device started message.

        Args:
            device_name: Device name.
            log_path: Path to log file.
        """
        print(f"[{device_name}] Started → {log_path}")

    def print_device_done(
        self,
        device_name: str,
        success: bool,
        steps: int,
        duration: float,
        error: str = "",
    ) -> None:
        """Print device completion message.

        Args:
            device_name: Device name.
            success: Whether task succeeded.
            steps: Number of steps executed.
            duration: Execution duration in seconds.
            error: Error message if failed.
        """
        if success:
            print(f"[{device_name}] ✅ Done ({steps} steps, {duration:.1f}s)")
        else:
            error_msg = f": {error[:50]}" if error else ""
            print(f"[{device_name}] ❌ Failed{error_msg}")

    def print_summary(self, success_count: int, total_count: int) -> None:
        """Print execution summary.

        Args:
            success_count: Number of successful devices.
            total_count: Total number of devices.
        """
        elapsed = time.time() - self.start_time if self.start_time else 0

        print()
        print("=" * 60)
        print(f"📊 Summary: {success_count}/{total_count} successful | Total: {elapsed:.1f}s")
        print()
