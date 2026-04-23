"""
向量型別定義模組
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class VectorDoc(BaseModel):
    """向量文件模型"""
    
    id: str = Field(..., description="文件唯一識別碼")
    content: str = Field(..., description="文件內容")
    parent_id: str = Field(..., description="父文件 ID", alias="parentId")
    project_name: str = Field(..., description="專案名稱", alias="projectName")
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    
    # 結構化 Metadata
    framework: Optional[str] = Field(None, description="所屬框架")
    framework_layer: Optional[str] = Field(None, description="框架層級", alias="frameworkLayer")
    code_type: Optional[str] = Field(None, description="程式碼類型", alias="codeType")
    symbol_name: Optional[str] = Field(None, description="符號名稱", alias="symbolName")
    
    # Small-to-Big Retrieval 相關
    header_path: Optional[str] = Field(None, description="Markdown 標題路徑", alias="headerPath")
    preview: Optional[str] = Field(None, description="內容預覽")

    # Stale 偵測：儲存同步當下的 MD 檔案內容 hash（MD5 前 16 碼）
    # 搜尋時比對磁碟上目前的 hash，不符即代表檔案在 MCP 外被修改過
    content_hash: Optional[str] = Field(None, description="檔案內容 hash（stale 偵測用）", alias="contentHash")
    
    # 向量嵌入（不會儲存在文件中，僅用於查詢）
    vector: Optional[List[float]] = Field(None, description="向量嵌入")
    
    # 程式碼連結相關
    related_files: Optional[List[str]] = Field(None, description="相關檔案列表", alias="relatedFiles")
    context_description: Optional[str] = Field(None, description="上下文描述", alias="contextDescription")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # 允許 alias 與 field name 混用


class CacheStats(BaseModel):
    """快取統計資料"""
    
    hits: int = Field(0, description="快取命中次數")
    misses: int = Field(0, description="快取未命中次數")
    size: int = Field(0, description="當前快取大小")
    max_size: int = Field(1000, description="最大快取大小")
    
    @property
    def hit_rate(self) -> float:
        """計算快取命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class DatabaseStats(BaseModel):
    """資料庫統計資料"""
    
    total_count: int = Field(0, description="總文件數")
    vector_dim: Optional[int] = Field(None, description="向量維度")
    model_name: str = Field("", description="Embedding 模型名稱")
    table_exists: bool = Field(False, description="資料表是否存在")
