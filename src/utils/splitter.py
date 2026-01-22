"""
Markdown 文件切分器
實作 Small-to-Big Retrieval 策略
"""

import re
import hashlib
from typing import List, Optional
from dataclasses import dataclass
from src.constants import KNOWLEDGE_CONSTANTS


@dataclass
class ChunkNode:
    """Markdown Chunk 節點"""
    id: str
    header_path: str  # 標題路徑（麵包屑）
    content: str
    preview: str
    level: int  # 標題層級（1-6）


class MarkdownSplitter:
    """
    Markdown 文件切分器
    
    按照 Markdown 標題階層切分文件，
    實作 Small-to-Big Retrieval 策略
    """
    
    def __init__(self, parent_id: str):
        """
        初始化
        
        Args:
            parent_id: 父文件 ID（通常是檔案名稱）
        """
        self.parent_id = parent_id
    
    def split(self, content: str) -> List[ChunkNode]:
        """
        切分 Markdown 文件
        
        Args:
            content: Markdown 內容
            
        Returns:
            Chunk 節點列表
        """
        chunks: List[ChunkNode] = []
        lines = content.split('\n')
        
        # 當前標題堆疊（用於建立 header_path）
        header_stack: List[tuple[int, str]] = []
        
        # 當前 chunk 的內容
        current_content: List[str] = []
        current_level = 0
        
        for line in lines:
            # 檢查是否為標題
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # 遇到新標題，先儲存前一個 chunk
                if current_content and len(current_content) >= KNOWLEDGE_CONSTANTS.MIN_CHUNK_LINES:
                    chunk = self._create_chunk(
                        header_stack.copy(),
                        current_content,
                        current_level
                    )
                    if chunk:
                        chunks.append(chunk)
                
                # 更新標題堆疊
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # 移除比當前層級深的標題
                header_stack = [
                    (h_level, h_title) 
                    for h_level, h_title in header_stack 
                    if h_level < level
                ]
                
                # 加入當前標題
                header_stack.append((level, title))
                
                # 重置內容
                current_content = [line]
                current_level = level
            else:
                # 非標題行，加入當前內容
                current_content.append(line)
        
        # 處理最後一個 chunk
        if current_content and len(current_content) >= KNOWLEDGE_CONSTANTS.MIN_CHUNK_LINES:
            chunk = self._create_chunk(
                header_stack,
                current_content,
                current_level
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        header_stack: List[tuple[int, str]],
        content_lines: List[str],
        level: int
    ) -> Optional[ChunkNode]:
        """
        建立 Chunk 節點
        
        Args:
            header_stack: 標題堆疊
            content_lines: 內容行
            level: 標題層級
            
        Returns:
            Chunk 節點或 None
        """
        # 組合內容
        content = '\n'.join(content_lines).strip()
        
        # 如果內容太短，跳過
        if len(content) < 10:
            return None
        
        # 建立 header path（麵包屑）
        if header_stack:
            header_path = ' > '.join(title for _, title in header_stack)
        else:
            header_path = "(Root)"
        
        # 建立預覽（前 200 字元）
        preview = content[:200] + "..." if len(content) > 200 else content
        
        # 生成唯一 ID
        chunk_id = self._generate_chunk_id(header_path, content[:100])
        
        return ChunkNode(
            id=chunk_id,
            header_path=header_path,
            content=content,
            preview=preview,
            level=level
        )
    
    def _generate_chunk_id(self, header_path: str, content_sample: str) -> str:
        """
        生成 Chunk 的唯一 ID
        
        Args:
            header_path: 標題路徑
            content_sample: 內容樣本
            
        Returns:
            唯一 ID
        """
        # 使用 parent_id + header_path + content_sample 生成 hash
        hash_input = f"{self.parent_id}:{header_path}:{content_sample}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        
        return f"{self.parent_id}:{hash_value}"


def split_markdown(parent_id: str, content: str) -> List[ChunkNode]:
    """
    快捷函式：切分 Markdown 文件
    
    Args:
        parent_id: 父文件 ID
        content: Markdown 內容
        
    Returns:
        Chunk 節點列表
    """
    splitter = MarkdownSplitter(parent_id)
    return splitter.split(content)
