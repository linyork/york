#!/bin/bash
###############################################################################
# York 啟動腳本 (Docker 版本)
# 用途：啟動 mcp/york 容器並掛載必要目錄
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 載入 .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    # 如果沒有 .env，嘗試使用預設值
    export PROJECTS_DIR="${PROJECTS_DIR:-$HOME/Documents/git}"
    export YORK_KNOWLEDGE_ROOT="${YORK_KNOWLEDGE_ROOT:-$SCRIPT_DIR/york-knowledge}"
fi

# 確保知識庫目錄存在
mkdir -p "$YORK_KNOWLEDGE_ROOT"

# 定義容器內的路徑
CONTAINER_PROJECTS_DIR="/projects"
CONTAINER_KNOWLEDGE_ROOT="/knowledge"

# 啟動 Docker 容器
# -i: 保持 STDIN 開啟 (MCP 需要)
# --rm: 容器停止後自動刪除
# -v: 掛載目錄
# -e: 傳遞環境變數
docker run -i --rm \
  --name york-mcp \
  -v "$PROJECTS_DIR":"$CONTAINER_PROJECTS_DIR" \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  -e ALLOWED_PROJECTS="$ALLOWED_PROJECTS" \
  -e LOG_LEVEL="${LOG_LEVEL:-info}" \
  -e NODE_ENV="${NODE_ENV:-production}" \
  mcp/york
