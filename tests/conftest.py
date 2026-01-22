"""
Pytest 配置檔案
"""

import pytest
import sys
from pathlib import Path

# 將 src 加入 Python 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))


@pytest.fixture(scope="session")
def test_data_dir():
    """測試資料目錄"""
    return Path(__file__).parent / "test_data"


from src.config import config

@pytest.fixture(scope="function")
def temp_knowledge_dir(tmp_path_factory):
    """臨時知識庫目錄"""
    return tmp_path_factory.mktemp("knowledge")

@pytest.fixture(autouse=True)
def setup_test_config(temp_knowledge_dir):
    """
    自動設定測試配置
    1. 將知識庫路徑指向臨時目錄
    2. 清空允許專案列表（允許存取所有測試專案）
    """
    original_root = config.knowledge_root
    original_allowed = config.allowed_projects
    
    config.knowledge_root = str(temp_knowledge_dir)
    config.allowed_projects = [] # 允許所有
    
    yield
    
    # 恢復
    config.knowledge_root = original_root
    config.allowed_projects = original_allowed


from src.services.vector import VectorStore

@pytest.fixture(autouse=True)
async def cleanup_vector_store():
    """
    確保每個測試都使用新的 VectorStore 實例
    這樣才能確保正確讀取被 mock 的 config.knowledge_root
    """
    # Setup
    VectorStore._instance = None
    
    yield
    
    # Teardown
    VectorStore._instance = None
