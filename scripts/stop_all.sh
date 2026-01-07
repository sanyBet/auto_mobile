#!/bin/bash
# 停止所有 main.py 进程和 watchdog
# 用法: ./stop_all.sh [--keep-watchdog]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/logs/pids"

echo -e "${RED}🛑 停止所有 DroidRun 进程${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 先停止 watchdog（除非指定 --keep-watchdog）
if [ "$1" != "--keep-watchdog" ]; then
    if [ -f "$PID_DIR/watchdog.pid" ]; then
        WATCHDOG_PID=$(cat "$PID_DIR/watchdog.pid")
        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            echo -e "${YELLOW}🐕 Stopping watchdog (PID: $WATCHDOG_PID)...${NC}"
            kill "$WATCHDOG_PID" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/watchdog.pid"
    fi
fi

# 查找所有 main.py 进程
PIDS=$(pgrep -f "main.py --device" 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo "没有找到正在运行的进程"
    exit 0
fi

echo "找到以下进程:"
ps aux | grep "main.py --device" | grep -v grep || true
echo ""

# 停止进程
for PID in $PIDS; do
    echo "Killing PID $PID..."
    kill $PID 2>/dev/null || true
done

echo ""
echo -e "${GREEN}✅ 已发送停止信号${NC}"

# 清理 PID 文件
if [ -d "$PID_DIR" ]; then
    rm -f "$PID_DIR"/*.pid "$PID_DIR"/*.restart_count "$PID_DIR"/*.failed "$PID_DIR/task.txt" 2>/dev/null || true
    echo -e "${GREEN}✅ 已清理 PID 文件${NC}"
fi
