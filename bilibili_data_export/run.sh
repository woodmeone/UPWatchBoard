#!/bin/bash
# B站数据中心自动导出工具 - 一键启动脚本

echo "============================================================"
echo "  B站数据中心自动导出工具"
echo "  首次运行会自动安装依赖，请耐心等待"
echo "============================================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 未检测到 Python，请先安装 Python 3.8+"
    exit 1
fi

PYTHON="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON="python"
fi

# 检查并安装 playwright
$PYTHON -c "import playwright" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 正在安装 playwright..."
    pip3 install playwright 2>/dev/null || pip install playwright
    echo ""
    echo "📦 正在安装 Chromium 浏览器（可能需要几分钟）..."
    playwright install chromium
    echo ""
    echo "✅ 安装完成！"
    echo ""
fi

# 运行脚本
echo "🚀 启动导出脚本..."
echo ""
DIR="$(cd "$(dirname "$0")" && pwd)"
$PYTHON "$DIR/playwright_version.py"
