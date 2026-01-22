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
    *   使用 **RRF (Reciprocal Rank Fusion)** 演算法優化排序，精準度 100%。

3.  **⚡ 高效能 Python 核心**
    *   基於 `FastMCP` 與 `uv` 套件管理。
    *   內建 `LanceDB` 向量資料庫（無須額外安裝 Service）。
    *   支援 `SentenceTransformers` 本機 Embedding 模型。

---

## 🚀 快速開始 (Docker 部署)

這是最推薦的安裝方式，確保環境完全隔離且一致。

### 1. 初始化設定

執行安裝精靈，它會檢查環境、生成 `.env` 並建置 Docker Image：

```bash
./setup.sh
```

### 2. 設定 Claude Desktop

將安裝精靈生成的配置加入您的 Claude 設定檔：

macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "york": {
      "command": "/您的/絕對路徑/到/york/start.sh"
    }
  }
}
```

### 3. 重啟 Claude

重啟 Antigravity 或是 Claude Desktop 後，您應該能看到 🛠️ 圖示中出現 York 的工具。

---

## 🛠️ 可用工具 (MCP Tools)

York 提供 12 個強大的工具，分為三大類：

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
| `detect_project_structure_tool` | **自動偵測** 專案框架並生成 `project.structure.yml` 建議 |
| `get_project_structure_tool` |讀取目前的專案結構配置 |
| `save_project_structure_tool` | 儲存結構配置並觸發結構索引更新 |
| `list_projects_tool` | 列出此工作區管理的所有專案 |

### 🔗 可用資源 (Resources - 支援 @ 引用)

Resource 是讓您直接將特定知識「注入」到 AI 上下文 (Context) 的捷徑。在 Claude 中輸入 `@` 即可使用。

| URI 模式 | 用途 | 範例 |
| :--- | :--- | :--- |
| `project://{name}/structure` | **專案地圖**：讀取專案目前的目錄結構與架構說明。 | `@project://repository_name/structure` |
| `project://{name}/knowledge/{file}` | **精準知識**：讀取特定的知識文件。 | `@project://repository_name/knowledge/auth.md` |

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
├── scripts/             # 功能演示腳本 (demo.py)
├── tests/               # Pytest 測試套件
├── Dockerfile           # 生產環境映像檔定義
├── start.sh             # 容器啟動腳本
└── setup.sh             # 安裝精靈
```

---

## 🔧 維運工具

York 在根目錄提供了一系列腳本方便維護：

*   **`./inspect_db.sh`**: 查看向量資料庫內容 (CLI 介面)。
*   **`./lancedb.sh`**: 備份或重置資料庫。
*   **`./migrate_knowledge.sh`**: 強制重建所有專案的知識索引。

---

## 📝 開發者指南

若您想在本機直接開發 (不使用 Docker)：

1.  安裝 `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  安裝依賴: `uv sync --all-extras`
3.  執行測試: `uv run pytest`
4.  啟動 Server: `uv run python -m src`

---
