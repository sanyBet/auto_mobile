# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Auto Mobile** 是基于 DroidRun 的多设备并行/串行自动化测试框架，用于管理多台 Android 设备（无线/USB/模拟器）并执行自动化任务。核心特性包括自动重连、并发控制、独立日志和任务配置系统。

## Development Commands

```bash
# Install dependencies
uv sync

# Configure (copy templates and edit)
cp .env.example .env && cp devices.yaml.example devices.yaml

# Device setup
adb connect <ip>:<port>        # Connect wireless device
droidrun setup --device <ip>:<port>  # Install DroidRun components

# Run tasks
uv run main.py                 # Execute active_task from devices.yaml
```

## Architecture

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Entry Point | `main.py` | Orchestrates workflow: ConfigLoader → DeviceManager → MultiDeviceRunner |
| Config System | `utils/config_loader.py` | Loads `.env` and `devices.yaml`, supports multi-provider LLM config |
| Device Manager | `utils/device_manager.py` | ADB connections with auto-reconnect (3 retries, 2s delay) |
| Task Runner | `utils/multi_runner.py` | Executes DroidAgent tasks with asyncio.Semaphore concurrency |
| Logging | `utils/device_logger.py` | Per-device log files + console output |
| HTTP Transport | `utils/openai_client.py` | Custom User-Agent for PackyAPI compatibility |

### Key Classes

- `ConfigLoader.get_api_config()`: Returns LLM config based on `LLM_PROVIDER` env var (openrouter/packyapi)
- `DeviceManager.connect_all()`: Parallel device connection with offline detection
- `MultiDeviceRunner.run_all()`: Event-based execution with TaskThinkingEvent/ExecutorResultEvent streaming
- `TaskConfig`: Dataclass (name, goal, max_steps, reasoning)

### Configuration Files

**`.env`** - LLM provider configuration (supports OpenRouter or PackyAPI)
```env
LLM_PROVIDER=openrouter  # or packyapi
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=openai/gpt-4o
# For PackyAPI: PACKYAPI_BASE_URL, PACKYAPI_API_KEY, PACKYAPI_MODEL
```

**`devices.yaml`** - Devices and tasks configuration
```yaml
concurrency: 1      # Max parallel devices (1 = sequential)
active_task: task_name

tasks:
  task_name:
    goal: "Task description"
    max_steps: 100
    reasoning: false

devices:
  device_name:
    enabled: true
    type: wireless|usb|emulator
    host: "192.168.x.x"  # wireless only
    port: 12345          # wireless only
    serial: "ABC123"     # usb/emulator only
```

### Data Flow

```
main.py → ConfigLoader (loads .env + devices.yaml)
       → DeviceManager.connect_all() (parallel ADB connections)
       → MultiDeviceRunner.run_all() (semaphore-controlled execution)
           → DroidAgent per device (AdbTools + LLM + event streaming)
       → Results: logs/ + trajectories/<device>_<timestamp>/
```

## Important Notes

### Security
- **Never commit**: `.env`, `devices.yaml`, `trajectories/`, `logs/`
- All sensitive files are in `.gitignore`

### Device Types
| Type | Required Fields | Auto-reconnect |
|------|-----------------|----------------|
| wireless | `host`, `port` | ✅ Yes |
| usb | `serial` | ❌ No |
| emulator | `serial` | ❌ No |

### Concurrency
- `concurrency: 1` → Sequential (device 1 → device 2 → ...)
- `concurrency: n` → Up to n devices in parallel
- Device connection phase is always parallel

### Output Locations
- **Console**: Real-time progress with emoji status
- **Device logs**: `logs/<device>_<timestamp>.log`
- **Trajectories**: `trajectories/<device>_<timestamp>/`

### Extending

**Add device**: Edit `devices.yaml` → add entry under `devices:` → set `enabled: true`

**Add task**: Edit `devices.yaml` → add entry under `tasks:` → set `active_task: new_task`

**Custom agent**: Edit `main.py` → modify `agent_config` (max_steps, reasoning, vision)
