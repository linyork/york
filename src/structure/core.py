"""
專案結構核心功能
處理 project.structure.yml 的讀取與寫入
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import config
from src.utils.logger import Logger
from src.knowledge.sync import reindex_knowledge

async def get_project_structure(project_name: str) -> str:
    """
    讀取專案目前的結構配置檔 (project.structure.yml)
    
    Args:
        project_name: 專案名稱
        
    Returns:
        YAML 配置內容 (字串)
        
    Raises:
        FileNotFoundError: 如果配置檔不存在
    """
    config_path = Path(config.knowledge_root) / project_name / "project.structure.yml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"找不到專案結構配置檔: {config_path}")
        
    async with await _open_file_async(config_path, "r") as f:
        content = await f.read()
        
    return content

async def save_project_structure(project_name: str, content: str) -> str:
    """
    儲存或更新專案的結構配置檔 (project.structure.yml)
    並自動觸發重索引
    
    Args:
        project_name: 專案名稱
        content: YAML 配置內容
        
    Returns:
        成功訊息
    """
    project_dir = Path(config.knowledge_root) / project_name
    config_path = project_dir / "project.structure.yml"
    
    # 確保目錄存在
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 驗證 YAML 格式 (確保內容是有效的 YAML)
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"無效的 YAML 格式: {e}")
    
    # 寫入檔案
    async with await _open_file_async(config_path, "w") as f:
        await f.write(content)
        
    Logger.info("Structure", f"專案結構配置已儲存: {project_name}")
    
    # 自動觸發 Reindex
    Logger.info("Structure", f"觸發自動索引重建: {project_name}")
    result = await reindex_knowledge(project_name)
    
    return f"已成功儲存配置檔至: {config_path}\n已自動觸發索引更新 (成功: {result['count']} 筆, 失敗: {result['errors']} 筆)"

# 非同步檔案操作輔助函數 (Python 沒有內建 async file I/O，這裡使用 aiofiles 或 run_in_executor)
# 為了簡化依賴，這裡使用 asyncio.to_thread (Python 3.9+)
import asyncio

class AsyncFileContext:
    def __init__(self, path: Path, mode: str):
        self.path = path
        self.mode = mode
        self.file = None

    async def __aenter__(self):
        # 這裡我們其實是同步打開，但在讀寫時用線程
        # 在高併發場景下建議用 aiofiles，但這裡為了減少依賴先這樣做
        self.file = open(self.path, self.mode, encoding="utf-8")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

    async def read(self):
        return await asyncio.to_thread(self.file.read)

    async def write(self, data):
        return await asyncio.to_thread(self.file.write, data)

async def _open_file_async(path: Path, mode: str) -> AsyncFileContext:
    return AsyncFileContext(path, mode)
