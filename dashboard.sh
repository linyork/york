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

echo "🚀 啟動 York Knowledge Dashboard..."
echo "🌐 http://localhost:8501"

# 使用 Docker 執行 Streamlit
docker run -it --rm \
  -p 8501:8501 \
  -v "$PROJECTS_DIR":"$CONTAINER_PROJECTS_DIR" \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  $IMAGE_NAME \
  streamlit run src/scripts/dashboard.py --server.address 0.0.0.0
