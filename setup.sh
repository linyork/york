#!/bin/bash
###############################################################################
# York 安裝精靈 (Docker 版本)
# 用途：初始化環境、生成配置檔並建置 Docker Image
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🐳 York MCP Server 安裝 (Docker)  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 檢查 Docker
echo -e "${BLUE}📋 檢查環境需求...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未找到 Docker${NC}"
    echo "請先安裝 Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

docker_version=$(docker --version)
echo -e "${GREEN}✓${NC} Docker 已安裝: ${docker_version}"

# 互動式設定
echo ""
echo -e "${BLUE}⚙️  設定環境變數${NC}"
echo ""

# PROJECTS_DIR
if [ -z "$PROJECTS_DIR" ]; then
    read -p "專案根目錄路徑 (預設: $HOME/Documents/git): " PROJECTS_DIR_INPUT
    PROJECTS_DIR="${PROJECTS_DIR_INPUT:-$HOME/Documents/git}"
fi

echo -e "${GREEN}✓${NC} 專案根目錄: ${PROJECTS_DIR}"

# YORK_KNOWLEDGE_ROOT
if [ -z "$YORK_KNOWLEDGE_ROOT" ]; then
    DEFAULT_KNOWLEDGE_ROOT="$SCRIPT_DIR/york-knowledge"
    read -p "知識庫路徑 (預設: $DEFAULT_KNOWLEDGE_ROOT): " KNOWLEDGE_ROOT_INPUT
    YORK_KNOWLEDGE_ROOT="${KNOWLEDGE_ROOT_INPUT:-$DEFAULT_KNOWLEDGE_ROOT}"
fi

mkdir -p "$YORK_KNOWLEDGE_ROOT"
echo -e "${GREEN}✓${NC} 知識庫路徑: ${YORK_KNOWLEDGE_ROOT}"

# 建立 .env 檔案
echo ""
echo -e "${BLUE}📝 生成 .env 檔案...${NC}"

cat > .env << EOF
# York 環境變數配置
PROJECTS_DIR=${PROJECTS_DIR}
YORK_KNOWLEDGE_ROOT=${YORK_KNOWLEDGE_ROOT}
ALLOWED_PROJECTS=
LOG_LEVEL=info
NODE_ENV=production
EOF

echo -e "${GREEN}✓${NC} .env 檔案已建立"

# 建置 Docker Image
echo ""
echo -e "${BLUE}🔨 開始建置 Docker Image...${NC}"
echo -e "${YELLOW}(這可能需要幾分鐘時間)${NC}"
echo ""

chmod +x ./build-image.sh
./build-image.sh

# 生成 MCP 配置
echo ""
echo -e "${BLUE}🔧 生成 MCP 配置...${NC}"
echo ""

cat << EOF

請將以下配置加入 Claude Desktop 的設定檔：

{
  "mcpServers": {
    "york": {
      "command": "${SCRIPT_DIR}/start.sh"
    }
  }
}

Claude Desktop 設定檔位置：
- macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
- Windows: %APPDATA%\\Claude\\claude_desktop_config.json

EOF

echo -e "${GREEN}✅ 安裝完成！${NC}"
echo ""
echo "執行 './start.sh' 測試啟動"
echo ""
