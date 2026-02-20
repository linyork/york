"""
知識庫核心模組
提供知識文件的 CRUD 操作
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import frontmatter

from src.constants import KNOWLEDGE_CONSTANTS
from src.models.knowledge import KnowledgeFile, KnowledgeMetadata
from src.utils.logger import Logger
from src.utils.project import (
    ensure_project_dir,
    get_project_path,
    sanitize_filename,
    validate_project_access,
)


async def save_knowledge(
    project_name: str,
    name: str,
    content: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    儲存知識文件到專案知識庫
    
    Args:
        project_name: 專案名稱
        name: 知識主題或檔案名稱
        content: 要儲存的內容（Markdown 格式）
        tags: 標籤列表
        metadata: 額外的 Metadata
        
    Returns:
        包含檔案路徑的字典
    """
    # 驗證專案存取權限
    if not validate_project_access(project_name):
        raise PermissionError(f"不允許存取專案: {project_name}")
    
    # 確保專案目錄存在
    project_path = ensure_project_dir(project_name)
    
    # 清理檔案名稱
    safe_name = sanitize_filename(name, extension='.md')
    
    file_path = project_path / safe_name
    
    # 準備 Metadata
    meta = metadata or {}
    meta['tags'] = tags or []
    meta['updated_at'] = datetime.now().isoformat()
    
    # 建立 frontmatter 文件
    post = frontmatter.Post(content, **meta)
    
    # 寫入檔案
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post))
    
    Logger.success("Knowledge", f"知識文件已儲存: {project_name}/{safe_name}")
    
    return {
        "path": str(file_path),
        "name": safe_name,
        "project": project_name
    }


async def read_knowledge(
    project_name: str,
    name: str
) -> KnowledgeFile:
    """
    讀取知識文件
    
    Args:
        project_name: 專案名稱
        name: 檔案名稱
        
    Returns:
        知識文件物件
        
    Raises:
        FileNotFoundError: 檔案不存在
        PermissionError: 無權存取
    """
    # 驗證專案存取權限
    if not validate_project_access(project_name):
        raise PermissionError(f"不允許存取專案: {project_name}")
    
    project_path = get_project_path(project_name)
    
    # 清理檔案名稱
    safe_name = sanitize_filename(name, extension='.md')
    
    file_path = project_path / safe_name
    
    if not file_path.exists():
        raise FileNotFoundError(f"知識文件不存在: {project_name}/{safe_name}")
    
    # 讀取檔案
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    # 建立 Metadata
    metadata = KnowledgeMetadata(
        tags=post.metadata.get('tags', []),
        framework=post.metadata.get('framework'),
        framework_layer=post.metadata.get('framework_layer') or post.metadata.get('frameworkLayer'),
        code_type=post.metadata.get('code_type') or post.metadata.get('codeType'),
        symbol_name=post.metadata.get('symbol_name') or post.metadata.get('symbolName'),
        related_files=post.metadata.get('related_files', []) or post.metadata.get('relatedFiles', []),
        context_description=post.metadata.get('context_description') or post.metadata.get('contextDescription')
    )
    
    Logger.debug("Knowledge", f"讀取知識文件: {project_name}/{safe_name}")
    
    return KnowledgeFile(
        name=safe_name,
        path=str(file_path),
        content=post.content,
        metadata=metadata
    )


async def list_knowledge(
    project_name: str,
    tag: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    列出專案的所有知識文件
    
    Args:
        project_name: 專案名稱
        tag: 標籤過濾（選填）
        
    Returns:
        知識文件資訊列表
    """
    # 驗證專案存取權限
    if not validate_project_access(project_name):
        raise PermissionError(f"不允許存取專案: {project_name}")
    
    project_path = get_project_path(project_name)
    
    if not project_path.exists():
        Logger.warning("Knowledge", f"專案目錄不存在: {project_name}")
        return []
    
    # 找出所有 .md 檔案
    md_files = list(project_path.glob('*.md'))
    
    # 排除專案知識彙整檔案
    md_files = [
        f for f in md_files 
        if f.name != KNOWLEDGE_CONSTANTS.PROJECT_KNOWLEDGE_FILE
        and f.name != KNOWLEDGE_CONSTANTS.PROJECT_STRUCTURE_FILE.replace('.yml', '.md')
    ]
    
    results = []
    
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            file_tags = post.metadata.get('tags', [])
            
            # 標籤過濾
            if tag and tag not in file_tags:
                continue
            
            results.append({
                "name": file_path.name,
                "tags": file_tags,
                "framework": post.metadata.get('framework'),
                "code_type": post.metadata.get('code_type') or post.metadata.get('codeType'),
                "updated_at": post.metadata.get('updated_at')
            })
        
        except Exception as e:
            Logger.warning("Knowledge", f"無法讀取檔案 {file_path.name}: {e}")
            continue
    
    Logger.debug("Knowledge", f"找到 {len(results)} 個知識文件")
    
    return results


async def delete_knowledge(
    project_name: str,
    name: str
) -> None:
    """
    刪除知識文件
    
    Args:
        project_name: 專案名稱
        name: 檔案名稱
        
    Raises:
        FileNotFoundError: 檔案不存在
        PermissionError: 無權存取
    """
    # 驗證專案存取權限
    if not validate_project_access(project_name):
        raise PermissionError(f"不允許存取專案: {project_name}")
    
    project_path = get_project_path(project_name)
    
    # 清理檔案名稱
    safe_name = sanitize_filename(name, extension='.md')
    
    file_path = project_path / safe_name
    
    if not file_path.exists():
        raise FileNotFoundError(f"知識文件不存在: {project_name}/{safe_name}")
    
    # 刪除檔案
    file_path.unlink()
    
    Logger.success("Knowledge", f"知識文件已刪除: {project_name}/{safe_name}")


async def get_project_knowledge(project_name: str) -> str:
    """
    取得專案的完整知識彙整
    
    Args:
        project_name: 專案名稱
        
    Returns:
        知識彙整內容（Markdown）
    """
    # 驗證專案存取權限
    if not validate_project_access(project_name):
        raise PermissionError(f"不允許存取專案: {project_name}")
    
    project_path = get_project_path(project_name)
    knowledge_file = project_path / KNOWLEDGE_CONSTANTS.PROJECT_KNOWLEDGE_FILE
    
    if not knowledge_file.exists():
        Logger.warning("Knowledge", f"專案知識彙整檔案不存在: {project_name}")
        return f"# {project_name}\n\n尚無知識文件。"
    
    with open(knowledge_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    Logger.debug("Knowledge", f"讀取專案知識彙整: {project_name}")
    
    return content
