"""
知識庫型別定義
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class KnowledgeMetadata(BaseModel):
    """知識文件 Metadata"""
    
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    framework: Optional[str] = Field(None, description="所屬框架")
    framework_layer: Optional[str] = Field(None, description="框架層級")
    code_type: Optional[str] = Field(None, description="程式碼類型")
    symbol_name: Optional[str] = Field(None, description="符號名稱")
    related_files: List[str] = Field(default_factory=list, description="相關檔案")
    context_description: Optional[str] = Field(None, description="上下文描述")


class KnowledgeFile(BaseModel):
    """知識文件"""
    
    name: str = Field(..., description="檔案名稱")
    path: str = Field(..., description="檔案路徑")
    content: str = Field(..., description="檔案內容")
    metadata: KnowledgeMetadata = Field(default_factory=KnowledgeMetadata, description="Metadata")
    
    @property
    def safe_name(self) -> str:
        """安全的檔案名稱（含 .md 副檔名）"""
        if self.name.endswith('.md'):
            return self.name
        return f"{self.name}.md"
