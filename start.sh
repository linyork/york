#!/bin/bash
###############################################################################
# York 啟動腳本 (Docker 版本)
# 用途：啟動 mcp/york 容器並掛載必要目錄
###############################################################################

set -e

# 確保 Antigravity 執行時能找到 docker 指令
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 載入 .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    # 如果沒有 .env，嘗試使用預設值
    export PROJECTS_DIR="${PROJECTS_DIR:-$HOME/Documents/git}"
fi

# 預設路徑：.data 目錄
YORK_KNOWLEDGE_ROOT="${YORK_KNOWLEDGE_ROOT:-$SCRIPT_DIR/.data}"
YORK_VECTOR_DB_PATH="${YORK_VECTOR_DB_PATH:-$SCRIPT_DIR/.data/lancedb}"

mkdir -p "$YORK_KNOWLEDGE_ROOT"
mkdir -p "$YORK_VECTOR_DB_PATH"

# 定義容器內的路徑
CONTAINER_PROJECTS_DIR="/projects"
CONTAINER_KNOWLEDGE_ROOT="/knowledge"
CONTAINER_VECTOR_DB_PATH="/lancedb"

# 啟動前先清理可能殘留的同名容器（避免重啟時發生 Conflict 錯誤）
docker rm -f york-mcp york-dashboard >/dev/null 2>&1 || true

# ── Dashboard（背景執行，port 8501）─────────────────────────────────────────
docker run -d --rm \
  --name york-dashboard \
  -p 8501:8501 \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -v "$YORK_VECTOR_DB_PATH":"$CONTAINER_VECTOR_DB_PATH" \
  -v "$SCRIPT_DIR/src:/app/src" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  -e YORK_VECTOR_DB_PATH="$CONTAINER_VECTOR_DB_PATH" \
  -e ALLOWED_PROJECTS="$ALLOWED_PROJECTS" \
  -e LOG_LEVEL="${LOG_LEVEL:-info}" \
  mcp/york \
  streamlit run src/scripts/dashboard.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true \
    --theme.base dark \
    --theme.primaryColor "#58a6ff" \
    --theme.backgroundColor "#0d1117" \
    --theme.secondaryBackgroundColor "#161b22" \
    --theme.textColor "#c9d1d9" \
  >/dev/null 2>&1 || true   # dashboard 失敗不影響 MCP 啟動

# ── MCP Server（前景執行，stdio）────────────────────────────────────────────
docker run -i --rm \
  --name york-mcp \
  -v "$PROJECTS_DIR":"$CONTAINER_PROJECTS_DIR" \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -v "$YORK_VECTOR_DB_PATH":"$CONTAINER_VECTOR_DB_PATH" \
  -v "$SCRIPT_DIR/src:/app/src" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  -e YORK_VECTOR_DB_PATH="$CONTAINER_VECTOR_DB_PATH" \
  -e ALLOWED_PROJECTS="$ALLOWED_PROJECTS" \
  -e LOG_LEVEL="${LOG_LEVEL:-info}" \
  -e NODE_ENV="${NODE_ENV:-production}" \
  mcp/york
