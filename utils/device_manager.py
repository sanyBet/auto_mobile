"""Device connection manager with auto-reconnection support."""

import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ConnectedDevice:
    """Represents a connected device."""

    name: str
    serial: str
    device_type: str
    description: str


class DeviceManager:
    """Manage ADB device connections with auto-reconnection."""

    def __init__(self, max_retry: int = 3, retry_delay: float = 2.0):
        """Initialize device manager.

        Args:
            max_retry: Maximum number of reconnection attempts.
            retry_delay: Delay between retry attempts in seconds.
        """
        self.max_retry = max_retry
        self.retry_delay = retry_delay

    async def connect_all(
        self, device_configs: Dict[str, Dict[str, Any]]
    ) -> List[ConnectedDevice]:
        """Connect to all devices with auto-reconnection.

        Args:
            device_configs: Dictionary of device configurations.

        Returns:
            List of successfully connected devices.
        """
        print(f"🔌 Connecting to {len(device_configs)} device(s)...")

        tasks = [
            self._connect_device(name, config)
            for name, config in device_configs.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        connected_devices = []
        for result in results:
            if isinstance(result, ConnectedDevice):
                connected_devices.append(result)
            elif isinstance(result, Exception):
                print(f"❌ Connection failed: {result}")

        print(f"✅ Successfully connected to {len(connected_devices)}/{len(device_configs)} device(s)")
        return connected_devices

    async def _connect_device(
        self, name: str, config: Dict[str, Any]
    ) -> ConnectedDevice:
        """Connect to a single device with retry logic.

        Args:
            name: Device name.
            config: Device configuration.

        Returns:
            ConnectedDevice instance.

        Raises:
            ConnectionError: If connection fails after all retries.
        """
        device_type = config.get("type", "unknown")
        description = config.get("description", "")

        print(f"  📱 [{name}] Connecting... ({description})")

        # Determine serial number based on device type
        if device_type == "wireless":
            serial = f"{config['host']}:{config['port']}"
        elif device_type in ("usb", "emulator"):
            serial = config.get("serial", "")
        else:
            raise ValueError(f"Unknown device type: {device_type}")

        # Try to connect with retries
        for attempt in range(1, self.max_retry + 1):
            try:
                # For wireless devices, ensure ADB connection
                if device_type == "wireless":
                    await self._ensure_wireless_connection(
                        config["host"], config["port"]
                    )

                # Check device status
                status = await self._get_device_status(serial)

                if status == "device":
                    print(f"  ✅ [{name}] Connected ({serial})")
                    return ConnectedDevice(
                        name=name,
                        serial=serial,
                        device_type=device_type,
                        description=description,
                    )
                elif status == "offline":
                    print(f"  ⚠️  [{name}] Device offline, attempting reconnection (attempt {attempt}/{self.max_retry})...")
                    if device_type == "wireless":
                        await self._reconnect_wireless(config["host"], config["port"])
                    await asyncio.sleep(self.retry_delay)
                else:
                    print(f"  ⚠️  [{name}] Device not found, retrying (attempt {attempt}/{self.max_retry})...")
                    if device_type == "wireless":
                        await self._reconnect_wireless(config["host"], config["port"])
                    await asyncio.sleep(self.retry_delay)

            except Exception as e:
                if attempt == self.max_retry:
                    raise ConnectionError(
                        f"Failed to connect to {name} after {self.max_retry} attempts: {e}"
                    )
                print(f"  ⚠️  [{name}] Error: {e}, retrying...")
                await asyncio.sleep(self.retry_delay)

        raise ConnectionError(f"Failed to connect to {name} after {self.max_retry} attempts")

    async def _ensure_wireless_connection(self, host: str, port: int) -> None:
        """Ensure wireless ADB connection is established.

        Args:
            host: Device IP address.
            port: Device port number.
        """
        try:
            # Try to connect
            await self._run_adb_command(["connect", f"{host}:{port}"])
        except Exception:
            # Ignore connection errors, will be handled by status check
            pass

    async def _reconnect_wireless(self, host: str, port: int) -> None:
        """Reconnect wireless device by disconnecting and connecting again.

        Args:
            host: Device IP address.
            port: Device port number.
        """
        try:
            # Disconnect first
            await self._run_adb_command(["disconnect", f"{host}:{port}"])
            await asyncio.sleep(1)
            # Reconnect
            await self._run_adb_command(["connect", f"{host}:{port}"])
        except Exception:
            # Ignore errors, will be handled by status check
            pass

    async def _get_device_status(self, serial: str) -> Optional[str]:
        """Get device status from adb devices.

        Args:
            serial: Device serial number.

        Returns:
            Device status: "device", "offline", or None if not found.
        """
        try:
            output = await self._run_adb_command(["devices"])
            lines = output.strip().split("\n")[1:]  # Skip header line

            for line in lines:
                if serial in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]  # Return status (device, offline, etc.)
            return None
        except Exception:
            return None

    async def _run_adb_command(self, args: List[str]) -> str:
        """Run ADB command asynchronously.

        Args:
            args: ADB command arguments.

        Returns:
            Command output.

        Raises:
            subprocess.CalledProcessError: If command fails.
        """
        cmd = ["adb"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, cmd, stdout, stderr
            )

        return stdout.decode("utf-8")
