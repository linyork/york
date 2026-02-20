"""
專案工具模組
提供專案相關的工具函式
"""

from pathlib import Path
from typing import List, Optional

from src.config import config
from src.utils.logger import Logger


async def list_projects() -> List[str]:
    """
    列出所有可用的專案
    
    Returns:
        專案名稱列表
    """
    knowledge_root = Path(config.knowledge_root)
    
    if not knowledge_root.exists():
        Logger.warning("Project", f"知識庫目錄不存在: {knowledge_root}")
        return []
    
    # 取得所有子目錄
    projects = [
        d.name 
        for d in knowledge_root.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    # 如果有設定允許的專案列表，進行過濾
    if config.allowed_projects:
        projects = [p for p in projects if p in config.allowed_projects]
    
    Logger.debug("Project", f"找到 {len(projects)} 個專案")
    return sorted(projects)


def get_project_path(project_name: str) -> Path:
    """
    取得專案的知識庫路徑
    
    Args:
        project_name: 專案名稱
        
    Returns:
        專案路徑
    """
    return Path(config.knowledge_root) / project_name


def ensure_project_dir(project_name: str) -> Path:
    """
    確保專案目錄存在，如不存在則建立
    
    Args:
        project_name: 專案名稱
        
    Returns:
        專案路徑
    """
    project_path = get_project_path(project_name)
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path


def validate_project_access(project_name: str) -> bool:
    """
    驗證是否允許存取該專案
    
    Args:
        project_name: 專案名稱
        
    Returns:
        是否允許存取
    """
    # 如果沒有設定允許列表，則允許所有專案
    if not config.allowed_projects:
        return True
    
    return project_name in config.allowed_projects


def sanitize_filename(name: str, extension: Optional[str] = None) -> str:
    """
    清理檔案名稱，移除不安全的字元
    
    Args:
        name: 原始檔案名稱
        extension: 選填，確保檔案具有此副檔名
        
    Returns:
        安全的檔案名稱
    """
    # 移除或替換不安全的字元
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    safe_name = name
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 移除前後空白
    safe_name = safe_name.strip()
    
    # 確保不是空字串
    if not safe_name:
        safe_name = "unnamed"
    
    # 處理副檔名
    if extension:
        if not extension.startswith('.'):
            extension = f".{extension}"
        if not safe_name.endswith(extension):
            safe_name = f"{safe_name}{extension}"

    return safe_name
