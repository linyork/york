# 🤖 York (The AI Project Brain)

York 是一個專為 AI Agent 設計的「專案知識管理大腦」。它透過 Model Context Protocol (MCP) 為 Claude 等 AI 提供深度專案認知能力，包含語意搜尋、結構感知與長期記憶管理。

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-FastMCP-000000)
![LanceDB](https://img.shields.io/badge/VectorDB-LanceDB-F85500)

## ✨ 核心特色

1.  **🧠 雙腦協作架構 (Cognitive Architecture)**
    *   **結構認知 (Structure)**: 自動偵測專案框架 (Laravel, FuelPHP, React...) 並理解目錄意義。
    *   **知識記憶 (Knowledge)**: 儲存業務邏輯、開發規範與決策紀錄。

2.  **🔍 混合檢索系統 (Hybrid Search)**
    *   結合 **關鍵字搜尋 (BM25)** 與 **語意搜尋 (Vector Embedding)**。
    *   使用 **RRF (Reciprocal Rank Fusion)** 演算法優化排序。

3.  **⚡ 高效能 Python 核心**
    *   基於 `FastMCP` 與 `uv` 套件管理。
    *   內建 `LanceDB` 向量資料庫（無須額外安裝 Service）。
    *   支援 `SentenceTransformers` 本機 Embedding 模型。

---

## 🚀 快速開始 (Docker 部署)

### 1. 建置 Docker Image

```bash
./build-image.sh
```

### 2. 設定 Claude Code / Claude Desktop

#### macOS/Linux — Claude Code

在 `~/.claude/mcp.json` 加入（不存在則新建）：

```json
{
  "mcpServers": {
    "york": {
      "command": "/你的/絕對路徑/york/start.sh"
    }
  }
}
```

#### macOS/Linux — Claude Desktop

設定檔位置: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "york": {
      "command": "/你的/絕對路徑/york/start.sh"
    }
  }
}
```

#### Windows — Claude Desktop / Antigravity

```json
{
  "mcpServers": {
    "york": {
      "command": "powershell.exe",
      "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "C:\\你的路徑\\york\\start.ps1"]
    }
  }
}
```

### 3. 重啟 Claude

重啟後應在 🛠️ 圖示中看到 York 的工具。

---

## ⚙️ 環境設定

所有資料預設存放在專案內的 `.data/` 目錄（已加入 `.gitignore`）：

```
york/.data/
├── lancedb/         ← 向量資料庫
└── {project_name}/ ← 知識 Markdown 檔案
    └── *.md
```

如需自訂路徑，複製 `.env.example` 為 `.env` 並設定：

```bash
cp .env.example .env
```

| 環境變數 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `PROJECTS_DIR` | **必填** | 本機專案根目錄 |
| `YORK_KNOWLEDGE_ROOT` | `./data` | 知識庫 md 檔存放路徑 |
| `YORK_VECTOR_DB_PATH` | `./data/lancedb` | LanceDB 向量資料庫路徑 |
| `ALLOWED_PROJECTS` | 空（允許全部） | 逗號分隔的允許專案名稱 |

---

## 🛠️ 可用工具 (MCP Tools)

York 提供 12 個工具，分為三大類：

### 📚 知識管理 (Knowledge)
| 工具名稱 | 描述 |
| :--- | :--- |
| `save_knowledge_tool` | 儲存文件到知識庫，並自動同步向量索引 |
| `read_knowledge_tool` | 讀取特定知識文件的內容與 metadata |
| `list_knowledge_tool` | 列出專案中的所有知識文件 |
| `delete_knowledge_tool` | 刪除知識文件與對應的向量數據 |
| `get_project_knowledge_tool` | 取得專案的完整知識彙整 (project-knowledge.md) |

### 🔍 搜尋與檢索 (Retrieval)
| 工具名稱 | 描述 |
| :--- | :--- |
| `search_knowledge_tool` | 混合搜尋 (關鍵字+語意)，支援 RRF 排序與結構化過濾 |
| `reindex_knowledge_tool` | 手動觸發特定專案的索引重建 |
| `get_vector_db_stats_tool` | 查看向量資料庫狀態 (統計、快取命中率) |

### 🏗️ 結構認知 (Structure)
| 工具名稱 | 描述 |
| :--- | :--- |
| `detect_project_structure_tool` | 自動偵測專案框架並生成 `project.structure.yml` 建議 |
| `get_project_structure_tool` | 讀取目前的專案結構配置 |
| `save_project_structure_tool` | 儲存結構配置並觸發結構索引更新 |
| `list_projects_tool` | 列出此工作區管理的所有專案 |

### 🔗 可用資源 (Resources - 支援 @ 引用)

| URI 模式 | 用途 |
| :--- | :--- |
| `project://{name}/structure` | 讀取專案目前的目錄結構與架構說明 |
| `project://{name}/knowledge/{file}` | 讀取特定的知識文件 |

---

## 📂 專案結構

```
york/
├── src/
│   ├── agent_server/    # MCP Server 定義與入口
│   ├── knowledge/       # 知識管理核心 (CRUD, Sync, Search)
│   ├── services/        # 基礎服務 (VectorStore: Singleton + LRU)
│   ├── structure/       # 結構認知核心 (Detector, YAML Handler)
│   ├── models/          # Pydantic 資料模型定義
│   └── utils/           # 通用工具 (Logger, Project Helper)
├── scripts/             # 功能演示腳本
├── tests/               # Pytest 測試套件
├── .data/               # 本機資料 (gitignored)
│   ├── lancedb/         # 向量資料庫
│   └── {project}/       # 知識 md 檔
├── Dockerfile
├── start.sh             # 容器啟動腳本 (macOS/Linux)
├── start.ps1            # 容器啟動腳本 (Windows)
└── build-image.sh       # Docker Image 建置
```

---

## 🔧 維運工具

| 工具 | macOS/Linux | Windows | 用途 |
| :--- | :--- | :--- | :--- |
| 知識庫儀表板 | `./dashboard.sh` | `.\dashboard.ps1` | 視覺化瀏覽知識庫（`http://localhost:8501`） |
| 資料庫檢查 | `./inspect_db.sh` | `.\inspect_db.ps1` | 查看向量資料庫詳細內容 |
| 重建索引 | `./migrate_knowledge.sh` | `.\migrate_knowledge.ps1` | 強制重建所有專案的向量索引 |
| 資料庫管理 | `./ops_db.sh [backup\|reset]` | `.\ops_db.ps1 [backup\|reset]` | 備份或重置 LanceDB |
| 測試 | `./test.sh` | `.\test.ps1` | 執行完整測試套件 |

---

## 📝 開發者指南

若您想在本機直接開發（不使用 Docker）：

```bash
# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝依賴
uv sync --all-extras

# 執行測試
uv run pytest

# 啟動 Server
uv run python -m src
```
