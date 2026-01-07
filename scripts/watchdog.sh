#!/bin/bash
# 守护进程脚本 - 监控并自动重启挂掉的设备进程
# 用法: ./watchdog.sh [start|stop|status]

set -e

# 配置
CHECK_INTERVAL=30      # 检查间隔（秒）
RESTART_DELAY=30       # 重启前等待（秒）
MAX_RESTARTS=5         # 单设备最大重启次数

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/logs/pids"
LOG_FILE="$PROJECT_DIR/logs/watchdog.log"
WATCHDOG_PID_FILE="$PID_DIR/watchdog.pid"

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE"
}

# 检查进程是否存活
is_running() {
    local pid=$1
    kill -0 "$pid" 2>/dev/null
}

# 获取重启计数
get_restart_count() {
    local device=$1
    local count_file="$PID_DIR/${device}.restart_count"
    if [ -f "$count_file" ]; then
        cat "$count_file"
    else
        echo "0"
    fi
}

# 增加重启计数
increment_restart_count() {
    local device=$1
    local count_file="$PID_DIR/${device}.restart_count"
    local current=$(get_restart_count "$device")
    echo $((current + 1)) > "$count_file"
}

# 重启单个设备
restart_device() {
    local device=$1
    local task=""

    # 读取任务名
    if [ -f "$PID_DIR/task.txt" ]; then
        task=$(cat "$PID_DIR/task.txt")
    fi

    # 构建命令
    local cmd="uv run main.py --device $device"
    if [ -n "$task" ]; then
        cmd="$cmd --task $task"
    fi

    # 启动进程
    local log_file="$PROJECT_DIR/logs/${device}_$(date +%Y%m%d_%H%M%S).out"
    cd "$PROJECT_DIR"
    $cmd > "$log_file" 2>&1 &
    local new_pid=$!

    # 更新 PID 文件
    echo "$new_pid" > "$PID_DIR/${device}.pid"

    log "${GREEN}✅ Restarted $device (PID: $new_pid) → $log_file${NC}"
}

# 监控循环
monitor_loop() {
    log "${GREEN}🐕 Watchdog started (interval: ${CHECK_INTERVAL}s, max_restarts: ${MAX_RESTARTS})${NC}"

    while true; do
        # 检查是否有 PID 文件
        if ! ls "$PID_DIR"/*.pid >/dev/null 2>&1; then
            log "${YELLOW}⚠️  No device PID files found, waiting...${NC}"
            sleep "$CHECK_INTERVAL"
            continue
        fi

        # 遍历所有设备 PID 文件
        for pid_file in "$PID_DIR"/*.pid; do
            # 跳过 watchdog 自己的 PID 文件
            if [ "$(basename "$pid_file")" = "watchdog.pid" ]; then
                continue
            fi

            local device=$(basename "$pid_file" .pid)
            local pid=$(cat "$pid_file")

            # 检查进程是否存活
            if ! is_running "$pid"; then
                local restart_count=$(get_restart_count "$device")

                if [ "$restart_count" -ge "$MAX_RESTARTS" ]; then
                    # 已达最大重启次数
                    if [ ! -f "$PID_DIR/${device}.failed" ]; then
                        log "${RED}❌ $device exceeded max restarts ($MAX_RESTARTS), giving up${NC}"
                        touch "$PID_DIR/${device}.failed"
                    fi
                else
                    # 需要重启
                    log "${YELLOW}⚠️  $device (PID: $pid) is down, restarting in ${RESTART_DELAY}s... (attempt $((restart_count + 1))/$MAX_RESTARTS)${NC}"
                    sleep "$RESTART_DELAY"

                    # 再次确认进程仍然不存在
                    if ! is_running "$pid"; then
                        increment_restart_count "$device"
                        restart_device "$device"
                    else
                        log "${GREEN}✅ $device recovered on its own${NC}"
                    fi
                fi
            fi
        done

        sleep "$CHECK_INTERVAL"
    done
}

# 启动守护进程
do_start() {
    mkdir -p "$PID_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"

    # 检查是否已运行
    if [ -f "$WATCHDOG_PID_FILE" ]; then
        local old_pid=$(cat "$WATCHDOG_PID_FILE")
        if is_running "$old_pid"; then
            echo -e "${YELLOW}⚠️  Watchdog already running (PID: $old_pid)${NC}"
            exit 1
        fi
    fi

    # 后台启动
    echo -e "${GREEN}🐕 Starting watchdog...${NC}"
    nohup "$0" _monitor >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$WATCHDOG_PID_FILE"
    echo -e "${GREEN}✅ Watchdog started (PID: $pid)${NC}"
    echo "   Log: $LOG_FILE"
}

# 停止守护进程
do_stop() {
    if [ ! -f "$WATCHDOG_PID_FILE" ]; then
        echo -e "${YELLOW}⚠️  Watchdog not running${NC}"
        exit 0
    fi

    local pid=$(cat "$WATCHDOG_PID_FILE")
    if is_running "$pid"; then
        echo -e "${RED}🛑 Stopping watchdog (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
        rm -f "$WATCHDOG_PID_FILE"
        echo -e "${GREEN}✅ Watchdog stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Watchdog not running (stale PID file removed)${NC}"
        rm -f "$WATCHDOG_PID_FILE"
    fi
}

# 查看状态
do_status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🐕 Watchdog Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 守护进程状态
    if [ -f "$WATCHDOG_PID_FILE" ]; then
        local pid=$(cat "$WATCHDOG_PID_FILE")
        if is_running "$pid"; then
            echo -e "Watchdog: ${GREEN}Running${NC} (PID: $pid)"
        else
            echo -e "Watchdog: ${RED}Stopped${NC} (stale PID file)"
        fi
    else
        echo -e "Watchdog: ${YELLOW}Not running${NC}"
    fi

    echo ""
    echo "Device Status:"

    # 设备状态
    if ls "$PID_DIR"/*.pid >/dev/null 2>&1; then
        for pid_file in "$PID_DIR"/*.pid; do
            if [ "$(basename "$pid_file")" = "watchdog.pid" ]; then
                continue
            fi

            local device=$(basename "$pid_file" .pid)
            local pid=$(cat "$pid_file")
            local restart_count=$(get_restart_count "$device")

            if [ -f "$PID_DIR/${device}.failed" ]; then
                echo -e "  $device: ${RED}Failed${NC} (exceeded $MAX_RESTARTS restarts)"
            elif is_running "$pid"; then
                echo -e "  $device: ${GREEN}Running${NC} (PID: $pid, restarts: $restart_count)"
            else
                echo -e "  $device: ${RED}Down${NC} (PID: $pid, restarts: $restart_count)"
            fi
        done
    else
        echo "  No devices found"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 主入口
case "${1:-}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    _monitor)
        # 内部命令，用于后台运行监控循环
        monitor_loop
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        echo ""
        echo "Commands:"
        echo "  start   Start the watchdog daemon"
        echo "  stop    Stop the watchdog daemon"
        echo "  status  Show watchdog and device status"
        exit 1
        ;;
esac
