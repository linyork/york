"""
測試配置模組
"""

import pytest
from src import __version__
from src.config import config
from src.constants import MCP_CONSTANTS


def test_version():
    """測試版本號"""
    assert __version__ == "1.2601.5"
    assert MCP_CONSTANTS.SERVER_VERSION == "1.2601.5"


def test_config_loading():
    """測試配置載入"""
    assert config is not None
    assert config.projects_root
    assert config.knowledge_root
    assert isinstance(config.allowed_projects, list)
    assert config.log_level in ["debug", "info", "warn", "error"]


def test_constants():
    """測試常量定義"""
    from src.constants import VECTOR_DB_CONSTANTS, KNOWLEDGE_CONSTANTS
    
    # 向量資料庫常量
    assert VECTOR_DB_CONSTANTS.TABLE_NAME == "knowledge_vectors"
    assert VECTOR_DB_CONSTANTS.VECTOR_DIMENSION == 384
    assert VECTOR_DB_CONSTANTS.MODEL_NAME == "paraphrase-multilingual-MiniLM-L12-v2"
    
    # 知識庫常量
    assert KNOWLEDGE_CONSTANTS.PROJECT_KNOWLEDGE_FILE == "friday-knowledge.md"
    assert KNOWLEDGE_CONSTANTS.PROJECT_STRUCTURE_FILE == "project.structure.yml"
