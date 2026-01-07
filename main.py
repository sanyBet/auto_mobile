#!/usr/bin/env python3
"""Multi-device DroidRun automation script."""

import argparse
import asyncio
import sys
from pathlib import Path

from droidrun.config_manager.config_manager import (
    DroidrunConfig,
    AgentConfig,
    CodeActConfig,
    ManagerConfig,
    ExecutorConfig,
)

from utils import ConfigLoader, DeviceManager, MultiDeviceRunner


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DroidRun Multi-Device Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run main.py                           # Run all enabled devices
  uv run main.py --device seeker_wireless_1  # Run single device
  uv run main.py -d seeker_wireless_1 -t deep_explore  # Device + task
        """
    )
    parser.add_argument(
        "--device", "-d",
        help="Run only specified device (by name from devices.yaml)"
    )
    parser.add_argument(
        "--task", "-t",
        help="Override active_task from config"
    )
    return parser.parse_args()


async def main():
    """Main entry point for multi-device automation."""
    args = parse_args()

    # Show mode in header
    mode = f"Device: {args.device}" if args.device else "All enabled devices"
    print("🚀 DroidRun Multi-Device Automation")
    print(f"📌 Mode: {mode}")
    print("=" * 60)

    try:
        # Load configuration
        config_loader = ConfigLoader()

        # Get API configuration
        print("📝 Loading API configuration...")
        api_config = config_loader.get_api_config()

        # Get device configuration (with optional filter)
        print("📱 Loading device configuration...")
        device_configs = config_loader.get_enabled_devices(args.device)

        if not device_configs:
            print("❌ No enabled devices found in devices.yaml")
            print("   Please enable at least one device in the configuration.")
            sys.exit(1)

        print(f"✅ Found {len(device_configs)} enabled device(s)")

        # Get execution settings
        concurrency = config_loader.get_concurrency()

        # Get task configuration (with optional override)
        print("🎯 Loading task configuration...")
        task_config = config_loader.get_task_config(args.task)
        print(f"✅ Using task: {task_config.name}")
        print(f"   max_steps: {task_config.max_steps}, reasoning: {task_config.reasoning}")

        # Connect to devices
        print(f"\n{'='*60}")
        device_manager = DeviceManager()
        connected_devices = await device_manager.connect_all(device_configs)

        if not connected_devices:
            print("❌ Failed to connect to any devices")
            sys.exit(1)

        # Create DroidAgent configuration from task config
        agent_config = DroidrunConfig(
            agent=AgentConfig(
                max_steps=task_config.max_steps,
                reasoning=task_config.reasoning,
                codeact=CodeActConfig(vision=True),
                manager=ManagerConfig(vision=True),
                executor=ExecutorConfig(vision=True),
            )
        )

        # Run tasks on all devices
        runner = MultiDeviceRunner(
            devices=connected_devices,
            goal=task_config.goal,
            llm_config=api_config,
            agent_config=agent_config,
            concurrency=concurrency,
        )

        results = await runner.run_all()

        # Exit with error code if any task failed
        failed_count = sum(1 for r in results if not r.success)
        if failed_count > 0:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
