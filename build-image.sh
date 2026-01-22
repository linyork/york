#!/bin/bash
set -e

# 定義 Image 名稱
IMAGE_NAME="mcp/york"

# 進入腳本所在目錄
cd "$(dirname "$0")"

echo "🔨 正在建置 Docker Image: $IMAGE_NAME..."

# 檢查是否需要清理舊的容器或 Image
if [ "$(docker ps -a -q -f ancestor=$IMAGE_NAME)" ]; then
    echo "Files using image found, stopping and removing..."
    docker stop $(docker ps -a -q -f ancestor=$IMAGE_NAME) > /dev/null 2>&1 || true
    docker rm $(docker ps -a -q -f ancestor=$IMAGE_NAME) > /dev/null 2>&1 || true
fi

if [ "$(docker images -q $IMAGE_NAME)" ]; then
    echo "Removing old image..."
    docker rmi -f $IMAGE_NAME > /dev/null 2>&1 || true
fi

# 執行建置
# --platform linux/amd64 通常是通用選擇，但在 M1/M2 Mac 上不指定會更快（使用 arm64）
# 為了相容性，這裡讓 Docker 自動偵測
docker build -t $IMAGE_NAME .

echo "✅ 建置完成！"
