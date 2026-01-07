#!/bin/bash
# 多设备并行启动脚本
# 为每个设备启动独立进程，实现进程级隔离

set -e

# 默认配置
START_NUM=${1:-1}      # 起始设备编号，默认 1
END_NUM=${2:-13}       # 结束设备编号，默认 13
TASK=${3:-""}          # 可选：指定任务名

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 启动多设备并行进程${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "设备范围: seeker_wireless_${START_NUM} ~ seeker_wireless_${END_NUM}"
if [ -n "$TASK" ]; then
    echo "任务: $TASK"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 创建 PID 目录
PID_DIR="logs/pids"
mkdir -p "$PID_DIR"

# 清理旧的 PID 文件
rm -f "$PID_DIR"/*.pid "$PID_DIR"/*.restart_count "$PID_DIR/task.txt"

# 记录任务名
if [ -n "$TASK" ]; then
    echo "$TASK" > "$PID_DIR/task.txt"
fi

# 存储 PID
PIDS=()

# 启动每个设备
for i in $(seq $START_NUM $END_NUM); do
    DEVICE="seeker_wireless_$i"

    if [ -n "$TASK" ]; then
        CMD="uv run main.py --device $DEVICE --task $TASK"
    else
        CMD="uv run main.py --device $DEVICE"
    fi

    # 启动后台进程，日志输出到文件
    LOG_FILE="logs/${DEVICE}_$(date +%Y%m%d_%H%M%S).out"
    mkdir -p logs

    echo -e "${YELLOW}▶ Starting $DEVICE${NC} → $LOG_FILE"
    $CMD > "$LOG_FILE" 2>&1 &

    PID=$!
    PIDS+=($PID)
    echo "  PID: $PID"

    # 保存 PID 到文件
    echo "$PID" > "$PID_DIR/${DEVICE}.pid"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 已启动 $((END_NUM - START_NUM + 1)) 个进程${NC}"
echo ""
echo "查看进程: ps aux | grep 'main.py'"
echo "停止所有: kill ${PIDS[*]}"
echo "查看日志: tail -f logs/seeker_wireless_*.out"
echo ""

# 可选：等待所有进程完成
# wait
