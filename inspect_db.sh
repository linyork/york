#!/bin/bash
set -e

# 定義 Image 名稱
IMAGE_NAME="mcp/york"

# 載入 .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    # 預設值
    export PROJECTS_DIR="${PROJECTS_DIR:-$HOME/Documents/git}"
    export YORK_KNOWLEDGE_ROOT="${YORK_KNOWLEDGE_ROOT:-$(pwd)/york-knowledge}"
fi

# 定義容器內的路徑
CONTAINER_PROJECTS_DIR="/projects"
CONTAINER_KNOWLEDGE_ROOT="/knowledge"

# 使用 Docker 執行檢查工具
docker run -it --rm \
  -v "$PROJECTS_DIR":"$CONTAINER_PROJECTS_DIR" \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  $IMAGE_NAME \
  python src/scripts/inspect_db.py
