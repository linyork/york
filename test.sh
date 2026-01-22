#!/bin/bash
set -e

# York 測試執行腳本
# 此腳本會在本地環境執行測試，需要安裝 uv

# 檢查 uv 是否安裝
if ! command -v uv &> /dev/null; then
    echo "❌ 錯誤：未找到 'uv' 指令。"
    echo "💡 請先安裝 uv (Python 套件管理器):"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "🔄 同步開發環境依賴..."
uv sync --frozen --extra dev

echo ""
echo "🧪 開始執行 Pytest..."
echo "================================================================"

# 執行測試
# -v: 詳細輸出
# --cov=src: 計算 src 目錄的覆蓋率
uv run pytest tests/ -v --cov=src --cov-report=term-missing

echo ""
echo "✅ 測試執行完畢！"
