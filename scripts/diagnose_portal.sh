#!/bin/bash
# DroidRun Portal 诊断脚本

DEVICE="192.168.1.16:37941"
PORTAL_PACKAGE="com.droidrun.portal"

echo "🔍 DroidRun Portal 诊断工具"
echo "================================"
echo ""

# 检查设备连接
echo "1️⃣ 检查设备连接..."
if adb devices | grep -q "$DEVICE"; then
    echo "   ✅ 设备已连接: $DEVICE"
else
    echo "   ❌ 设备未连接: $DEVICE"
    exit 1
fi
echo ""

# 检查 Portal 应用安装
echo "2️⃣ 检查 Portal 应用..."
if adb -s "$DEVICE" shell pm list packages | grep -q "$PORTAL_PACKAGE"; then
    echo "   ✅ Portal 应用已安装"

    # 获取应用版本
    VERSION=$(adb -s "$DEVICE" shell dumpsys package "$PORTAL_PACKAGE" | grep versionName | head -1)
    echo "   📦 $VERSION"
else
    echo "   ❌ Portal 应用未安装"
    echo "   💡 请运行: adb -s $DEVICE install /path/to/droidrun_portal.apk"
    exit 1
fi
echo ""

# 检查 Portal 服务运行状态
echo "3️⃣ 检查 Portal 服务..."
if adb -s "$DEVICE" shell ps | grep -q "$PORTAL_PACKAGE"; then
    echo "   ✅ Portal 服务正在运行"
else
    echo "   ⚠️  Portal 服务未运行"
    echo "   💡 尝试启动: adb -s $DEVICE shell am start -n $PORTAL_PACKAGE/.MainActivity"
fi
echo ""

# 检查权限
echo "4️⃣ 检查应用权限..."
PERMS=$(adb -s "$DEVICE" shell dumpsys package "$PORTAL_PACKAGE" | grep "granted=true" | wc -l)
echo "   📋 已授予权限数量: $PERMS"

# 检查关键权限
echo "   🔑 关键权限检查："
adb -s "$DEVICE" shell dumpsys package "$PORTAL_PACKAGE" | grep -A 1 "android.permission.READ_EXTERNAL_STORAGE" | grep -q "granted=true" && echo "      ✅ 存储读取权限" || echo "      ❌ 存储读取权限"
adb -s "$DEVICE" shell dumpsys package "$PORTAL_PACKAGE" | grep -A 1 "android.permission.WRITE_EXTERNAL_STORAGE" | grep -q "granted=true" && echo "      ✅ 存储写入权限" || echo "      ❌ 存储写入权限"
echo ""

# 检查 ContentProvider
echo "5️⃣ 检查 ContentProvider..."
PROVIDER_TEST=$(adb -s "$DEVICE" shell content query --uri content://"$PORTAL_PACKAGE".provider/state 2>&1)
if echo "$PROVIDER_TEST" | grep -q "Error"; then
    echo "   ❌ ContentProvider 无法访问"
    echo "   错误: $PROVIDER_TEST"
    echo ""
    echo "   💡 可能的解决方案："
    echo "      1. 确保 Portal 应用正在运行"
    echo "      2. 重启 Portal 应用"
    echo "      3. 手动开启辅助功能权限（最重要！）"
    echo "         设置 → 辅助功能 → 已安装的服务 → DroidRun Portal"
else
    echo "   ✅ ContentProvider 正常工作"
fi
echo ""

echo "================================"
echo "诊断完成！"
