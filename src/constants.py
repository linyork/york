"""
York 常量定義模組
"""

# === 向量資料庫常量 ===

class VectorDBConstants:
    """向量資料庫相關常量"""
    
    # 資料表名稱
    TABLE_NAME = "knowledge_vectors"
    
    # Embedding 模型名稱
    # 使用多語言模型，支援中文
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    
    # Embedding 維度 (MiniLM)
    VECTOR_DIMENSION = 384
    
    # LRU 快取大小
    CACHE_MAX_SIZE = 1000
    
    # 資料庫目錄名稱
    DB_DIR_NAME = "lancedb"
    
    # 預設搜尋結果數量
    DEFAULT_SEARCH_LIMIT = 5
    
    # Schema 重試次數
    MAX_SCHEMA_RETRIES = 3


# === 知識庫常量 ===

class KnowledgeConstants:
    """知識庫相關常量"""
    
    # 專案知識庫檔案名稱
    PROJECT_KNOWLEDGE_FILE = "friday-knowledge.md"
    
    # 專案結構配置檔名稱
    PROJECT_STRUCTURE_FILE = "project.structure.yml"
    
    # Markdown 檔案副檔名
    MARKDOWN_EXTENSION = ".md"
    
    # 預設標籤
    DEFAULT_TAGS = ["general"]
    
    # Chunk 切分的最小行數
    MIN_CHUNK_LINES = 3

    # 單一 chunk 最大字元數
    # paraphrase-multilingual-MiniLM-L12-v2 上限 512 tokens
    # 中文約 1 字 = 1.5 tokens，保守取 350 字 ≈ 525 tokens（含標題與空白行）
    MAX_CHUNK_CHARS = 500

    # 超大段落（無法從段落邊界拆開時）的句子切分長度
    MAX_SENTENCE_CHARS = 150

    # size-based 二次切分時，相鄰 sub-chunk 的 overlap 字元數
    # 取前一個 sub-chunk 的尾部加入下一個的開頭，避免邊界語意損失
    # 限定在 _subdivide 產生的 sub-chunks，header-level split 不加 overlap
    CHUNK_OVERLAP_CHARS = 100


# === 程式碼分析常量 ===

class AnalyzerConstants:
    """程式碼分析相關常量"""
    
    # 支援的程式語言
    SUPPORTED_LANGUAGES = [
        "typescript",
        "javascript", 
        "python",
        "php",
        "java",
    ]
    
    # 支援的樣式表語言
    SUPPORTED_STYLES = [
        "css",
        "scss",
        "less",
    ]
    
    # 支援的標記語言
    SUPPORTED_MARKUP = [
        "markdown",
        "json",
        "yaml",
    ]


# === MCP 常量 ===

class MCPConstants:
    """MCP 相關常量"""
    
    # Server 名稱
    SERVER_NAME = "york"
    
    # Server 版本 (與 pyproject.toml 保持一致)
    SERVER_VERSION = "1.2601.5"


# === 匯出 ===

VECTOR_DB_CONSTANTS = VectorDBConstants()
KNOWLEDGE_CONSTANTS = KnowledgeConstants()
ANALYZER_CONSTANTS = AnalyzerConstants()
MCP_CONSTANTS = MCPConstants()
