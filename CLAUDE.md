# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Auto Mobile** 是基于 DroidRun 的多设备并行/串行自动化测试框架，用于管理多台 Android 设备（无线/USB/模拟器）并执行自动化任务。核心特性包括自动重连、并发控制、独立日志和任务配置系统。

## Development Commands

### Environment Setup
```bash
# Install all dependencies
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate
```

### Configuration
```bash
# Copy environment template and configure API keys
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Copy device configuration template
cp devices.yaml.example devices.yaml
# Edit devices.yaml to configure your devices and tasks
```

### Device Setup
```bash
# Connect to wireless device
adb connect <ip>:<port>

# Check device connection status
adb devices

# Setup DroidRun on device (install required components)
droidrun setup --device <ip>:<port>

# Verify DroidRun installation
droidrun devices
```

### Running Tasks
```bash
# Run the main script (uses active_task from devices.yaml)
uv run main.py

# The script will:
# 1. Load .env configuration (API keys, model)
# 2. Load devices.yaml (devices, tasks, concurrency)
# 3. Connect to all enabled devices with auto-retry
# 4. Execute the active_task on devices (serial or parallel based on concurrency)
# 5. Generate logs in trajectories/ and logs/
```

## Architecture

### Core Components

**Entry Point**: `main.py`
- Orchestrates the entire workflow
- Initializes ConfigLoader, DeviceManager, MultiDeviceRunner
- Handles errors and exit codes

**Configuration System** (`utils/config_loader.py`)
- `ConfigLoader`: Loads `.env` and `devices.yaml`
  - `get_api_config()`: Returns OpenRouter API configuration
  - `get_enabled_devices()`: Filters enabled devices from devices.yaml
  - `get_task_config()`: Loads task by name or active_task
  - `get_concurrency()`: Returns max concurrent device operations
- `TaskConfig`: Dataclass for task configuration (goal, max_steps, reasoning)

**Device Management** (`utils/device_manager.py`)
- `DeviceManager`: Handles ADB device connections with auto-reconnection
  - `connect_all()`: Parallel connection to all devices with retry logic
  - `_connect_device()`: Single device connection with offline detection
  - `_reconnect_wireless()`: Disconnect and reconnect wireless devices
  - `_get_device_status()`: Check device status via adb devices
- `ConnectedDevice`: Dataclass storing device info (name, serial, type, description)
- **Auto-reconnection logic**: Detects "offline" status and automatically reconnects (max 3 retries by default)

**Task Execution** (`utils/multi_runner.py`)
- `MultiDeviceRunner`: Executes DroidAgent tasks across multiple devices
  - `run_all()`: Manages concurrency with asyncio.Semaphore
  - `_run_device_task()`: Runs task on single device (initializes ADB tools, LLM, DroidAgent)
  - `_run_agent_with_logging()`: Streams DroidAgent events to device-specific logger
- `TaskResult`: Stores execution results (success, duration, steps, logs)
- **Concurrency control**: Uses asyncio.Semaphore to limit parallel executions

**Logging** (`utils/device_logger.py`)
- `DeviceLogger`: Creates separate log files for each device
  - Logs stored in `logs/<device_name>_<timestamp>.log`
- `ConsoleOutput`: Formats and prints execution progress to terminal
  - Real-time device status updates
  - Final summary with success/failure counts

### Configuration Files

**`.env`** (not committed to git)
```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o
```

**`devices.yaml`** (not committed to git)
```yaml
concurrency: 1  # Max parallel devices (1 = sequential)
active_task: task_name  # Current task to execute

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
    description: "Device description"
```

### Data Flow

1. **Initialization**: `main.py` → `ConfigLoader` loads configs
2. **Connection**: `DeviceManager.connect_all()` connects all enabled devices in parallel
   - Wireless devices: `adb connect <host>:<port>` with retry on offline
   - USB/Emulator: Verify via `adb devices`
3. **Execution**: `MultiDeviceRunner.run_all()` executes tasks
   - Creates asyncio.Semaphore(concurrency)
   - Spawns async tasks for each device
   - Each task initializes: AdbTools → OpenAILike → DroidAgent
4. **Logging**: Events streamed to device-specific loggers
   - TaskThinkingEvent, TaskExecutionEvent, TaskEndEvent (CodeAct mode)
   - ExecutorResultEvent, ManagerPlanEvent (Manager/Executor mode)
5. **Results**: `TaskResult` objects collected and summarized

### Key Design Patterns

**Async Parallel Execution**: Uses `asyncio.gather()` for device connections and task execution
- Device connections are always parallel (faster startup)
- Task execution respects `concurrency` setting via Semaphore

**Auto-Retry Pattern** (DeviceManager):
```python
for attempt in range(1, max_retry + 1):
    status = await _get_device_status(serial)
    if status == "device":
        return connected_device
    elif status == "offline":
        await _reconnect_wireless()  # wireless only
    await asyncio.sleep(retry_delay)
```

**Event-Based Logging** (MultiDeviceRunner):
```python
async for event in handler.stream_events():
    # Match event type and log to device-specific logger
    # Events: TaskThinkingEvent, ExecutorResultEvent, etc.
```

**Task Configuration System**:
- Centralized task definitions in `devices.yaml`
- Multiple tasks can be defined, switch via `active_task`
- Each task has independent `goal`, `max_steps`, `reasoning` settings

## Important Notes

### Security
- **Never commit**: `.env`, `devices.yaml`, `trajectories/`, `logs/`
- All sensitive files are in `.gitignore`
- Only commit `.example` template files

### Device Types
- **wireless**: Requires `host` and `port`, auto-reconnects on offline
- **usb**: Requires `serial` from `adb devices`
- **emulator**: Requires `serial` (usually `emulator-5554`)

### Concurrency Modes
- `concurrency: 1` → Sequential execution (device 1 → device 2 → ...)
- `concurrency: n` → Up to n devices run in parallel
- Connection phase is always parallel regardless of concurrency setting

### Logging Output
- **Console**: Real-time progress via `ConsoleOutput` (emoji icons, device status)
- **Device logs**: Individual files in `logs/` (timestamped)
- **Trajectories**: DroidAgent execution history in `trajectories/<device>_<timestamp>/`

### Error Handling
- Connection failures: Retry 3 times with 2s delay, then skip device
- Task failures: Log error, continue with other devices, exit code 1 if any failed
- Missing config: Clear error messages pointing to `.example` files

### Extending the Framework

**Add new device**:
1. Edit `devices.yaml`, add device entry under `devices:`
2. Set `enabled: true` and configure type-specific fields
3. Run `main.py` (auto-detected and connected)

**Add new task**:
1. Edit `devices.yaml`, add task entry under `tasks:`
2. Set `active_task: new_task_name`
3. Run `main.py` (no code changes needed)

**Customize agent behavior**:
- Edit `main.py` → `agent_config` object
- Modify `max_steps`, `reasoning`, `vision` settings
- Applies to all devices uniformly

### Dependencies
- `droidrun`: Android automation framework (with multiple provider extras)
- `llama-index-llms-openrouter`: OpenRouter LLM integration
- `python-dotenv`: Environment variable loading
- `pyyaml`: YAML configuration parsing
- `rich`: Terminal output formatting
