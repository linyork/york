#!/bin/bash
###############################################################################
# 知識遷移與重索引工具
# 用途：觸發 York 重新掃描並建立向量索引
###############################################################################

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

echo "🔄 開始重建知識庫索引..."
echo "這可能需要一些時間，視文件數量而定。"

# 使用 Docker 執行一段 Python code 呼叫 reindex_all_projects
docker run -it --rm \
  -v "$PROJECTS_DIR":"$CONTAINER_PROJECTS_DIR" \
  -v "$YORK_KNOWLEDGE_ROOT":"$CONTAINER_KNOWLEDGE_ROOT" \
  -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" \
  -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" \
  $IMAGE_NAME \
  python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from src.knowledge.sync import reindex_all_projects
from src.utils.logger import Logger

async def main():
    Logger.info('Migrate', '開始全面重索引...')
    results = await reindex_all_projects()
    
    total_count = 0
    total_errors = 0
    
    for project, stats in results.items():
        count = stats.get('count', 0)
        errors = stats.get('errors', 0)
        total_count += count
        total_errors += errors
        print(f'Project {project}: {count} files, {errors} errors')
        
    Logger.success('Migrate', f'遷移完成！總計 {total_count} 文件, {total_errors} 錯誤')

if __name__ == '__main__':
    asyncio.run(main())
"
