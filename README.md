# Auto Mobile - DroidRun 多设备自动化框架

基于 DroidRun 的多设备并行/串行自动化测试框架，支持通过配置文件管理多台 Android 设备，并自动处理无线调试重连问题。

## 功能特性

✅ **多设备管理**：通过 YAML 配置文件管理多台设备
✅ **自动重连**：无线调试设备自动检测并重连（解决 offline 问题）
✅ **并发控制**：支持串行/并行执行，可配置并发数
✅ **安全配置**：API Key 和敏感配置通过 .env 文件管理
✅ **独立日志**：每个设备独立的 trajectory 日志文件夹
✅ **详细输出**：实时显示每个设备的执行进度和结果汇总

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENROUTER_API_KEY
```

`.env` 文件内容：
```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o
```

### 3. 配置设备

复制 `devices.yaml.example` 为 `devices.yaml` 并配置你的设备：

```bash
cp devices.yaml.example devices.yaml
# 编辑 devices.yaml 文件，配置你的设备信息
```

#### 无线调试设备配置

1. 在手机上开启无线调试：
   - 设置 → 开发者选项 → 无线调试
   - 记录显示的 IP 地址和端口号

2. 在 `devices.yaml` 中配置：
```yaml
devices:
  my_phone:
    enabled: true
    type: wireless
    host: 192.168.1.100  # 替换为你的手机 IP
    port: 12345          # 替换为你的端口号
    description: "我的手机"
```

#### USB 连接设备配置

1. 连接手机到电脑，运行 `adb devices` 查看序列号
2. 配置：
```yaml
devices:
  my_phone_usb:
    enabled: true
    type: usb
    serial: "ABC123DEF456"  # 替换为实际序列号
    description: "USB 连接手机"
```

### 4. 运行脚本

```bash
uv run basic.py
```

## 配置说明

### devices.yaml 配置文件

```yaml
# 并发设置
concurrency: 1  # 最大并发数，1=串行执行，>1=并行执行

# 默认任务目标
default_goal: "你的任务描述"

# 设备列表
devices:
  # 设备 1
  device_name_1:
    enabled: true           # 是否启用
    type: wireless          # wireless | usb | emulator
    host: 192.168.1.100    # 无线调试 IP
    port: 12345            # 无线调试端口
    description: "设备描述"

  # 设备 2
  device_name_2:
    enabled: true
    type: usb
    serial: "ABC123"       # USB/模拟器序列号
    description: "设备描述"
```

### 设备类型说明

| 类型 | 说明 | 必需字段 |
|------|------|---------|
| `wireless` | 无线调试设备 | `host`, `port` |
| `usb` | USB 连接设备 | `serial` |
| `emulator` | Android 模拟器 | `serial` |

## 工作流程

1. **加载配置**：读取 `.env` 和 `devices.yaml`
2. **设备连接**：并行连接所有启用的设备
   - 无线设备自动检测 offline 状态并重连
   - 最多重试 3 次，每次间隔 2 秒
3. **任务执行**：根据 `concurrency` 设置执行任务
   - `concurrency: 1` → 串行执行（设备 1 → 设备 2 → ...）
   - `concurrency: n` → 最多同时运行 n 个设备
4. **结果汇总**：显示每个设备的执行结果和统计信息

## 输出示例

```
🚀 DroidRun Multi-Device Automation
============================================================
📝 Loading API configuration...
📱 Loading device configuration...
✅ Found 2 enabled device(s)

============================================================
🔌 Connecting to 2 device(s)...
  📱 [pixel_wireless] Connecting... (Pixel 8 Pro 无线调试)
  ✅ [pixel_wireless] Connected (172.19.0.1:41695)
  📱 [xiaomi_usb] Connecting... (小米手机 USB 连接)
  ✅ [xiaomi_usb] Connected (abc123def456)
✅ Successfully connected to 2/2 device(s)

============================================================
🚀 Starting batch execution
📱 Devices: 2
⚙️  Concurrency: 1
🎯 Goal: 打开首页的wallet...
============================================================

[1/2] 📱 pixel_wireless
  ├─ Serial: 172.19.0.1:41695
  ├─ Type: wireless
  └─ Description: Pixel 8 Pro 无线调试
  🤖 Initializing DroidAgent...
  ▶️  Executing task...
  ✅ Success (took 125.3s)

[2/2] 📱 xiaomi_usb
  ├─ Serial: abc123def456
  ├─ Type: usb
  └─ Description: 小米手机 USB 连接
  🤖 Initializing DroidAgent...
  ▶️  Executing task...
  ✅ Success (took 98.7s)

============================================================
📊 Execution Summary
============================================================

✅ [pixel_wireless] Success
   ├─ Duration: 125.3s
   ├─ Steps: 18
   ├─ Logs: trajectories/pixel_wireless_20251209_143645/
   └─ Output: Task completed successfully

✅ [xiaomi_usb] Success
   ├─ Duration: 98.7s
   ├─ Steps: 15
   ├─ Logs: trajectories/xiaomi_usb_20251209_143645/
   └─ Output: Task completed successfully

============================================================
✅ Successful: 2/2
❌ Failed: 0/2
⏱️  Total time: 224.0s
⚙️  Mode: sequential
============================================================
```

## 故障排除

### 1. 无线设备显示 offline

**问题**：`adb devices` 显示设备状态为 `offline`

**解决方案**：
- ✅ 脚本会自动检测并重连
- 如果仍然失败，手动重连：
  ```bash
  adb disconnect
  adb connect <IP>:<PORT>
  ```
- 检查手机无线调试是否仍然开启

### 2. 找不到 API Key

**问题**：`OPENROUTER_API_KEY not found`

**解决方案**：
1. 确保 `.env` 文件存在于项目根目录
2. 检查 `.env` 文件中是否包含 `OPENROUTER_API_KEY=...`
3. 不要在 API Key 两边加引号

### 3. 没有启用的设备

**问题**：`No enabled devices found`

**解决方案**：
1. 检查 `devices.yaml` 中至少有一个设备的 `enabled: true`
2. 确保 YAML 语法正确（注意缩进）

### 4. ModuleNotFoundError

**问题**：`ModuleNotFoundError: No module named 'utils'`

**解决方案**：
```bash
# 确保 utils 目录存在且包含所需文件
ls -la utils/
# 应该看到：__init__.py, config_loader.py, device_manager.py, multi_runner.py

# 重新安装依赖
uv sync
```

## 项目结构

```
auto_mobile/
├── .env                      # API 配置（不提交到 git）
├── .env.example              # API 配置模板
├── devices.yaml              # 设备配置（不提交到 git）
├── devices.yaml.example      # 设备配置模板
├── basic.py                  # 主入口脚本
├── pyproject.toml            # 项目依赖
├── utils/                    # 工具模块（正确位置）
│   ├── __init__.py
│   ├── config_loader.py      # 配置加载器
│   ├── device_manager.py     # 设备连接管理（含自动重连）
│   └── multi_runner.py       # 多设备并行/串行运行器
└── trajectories/             # 执行日志（不提交到 git）
    ├── device1_20251209_143645/
    └── device2_20251209_143645/
```

## 安全提示

⚠️ **不要提交敏感信息到 Git**

以下文件已自动添加到 `.gitignore`：
- `.env` - 包含 API Key
- `devices.yaml` - 可能包含内网 IP 等敏感信息
- `trajectories/` - 执行日志可能包含隐私信息

只有 `.env.example` 和 `devices.yaml.example` 会被提交到 Git。

## 高级配置

### 自定义重连参数

编辑 `basic.py`，修改 `DeviceManager` 初始化参数：

```python
device_manager = DeviceManager(
    max_retry=5,        # 最大重试次数（默认 3）
    retry_delay=3.0,    # 重试间隔秒数（默认 2.0）
)
```

### 自定义 Agent 配置

编辑 `basic.py`，修改 `agent_config`：

```python
agent_config = DroidrunConfig(
    agent=AgentConfig(
        max_steps=200,      # 最大步骤数
        reasoning=True,     # 启用推理模式
        codeact=CodeActConfig(vision=True),
        manager=ManagerConfig(vision=True),
        executor=ExecutorConfig(vision=True),
    )
)
```

## 许可证

MIT License

## 相关链接

- [DroidRun 官方文档](https://github.com/mbzuai-oryx/DroidRun)
- [OpenRouter API](https://openrouter.ai/)
