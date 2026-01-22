"""
York MCP Server 配置模組
負責載入與驗證所有環境變數與系統設定
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# === 路徑設定 ===

# 專案根目錄路徑
PROJECT_ROOT_DIR = Path(__file__).parent.parent.absolute()

# 載入 .env 環境變數檔案
load_dotenv(PROJECT_ROOT_DIR / ".env")


# === 配置模型 ===

class YorkConfig(BaseModel):
    """York 配置模型"""
    
    # 專案根目錄路徑
    projects_root: str = Field(..., description="專案根目錄路徑")
    
    # 知識庫根目錄路徑
    knowledge_root: str = Field(..., description="知識庫根目錄路徑")
    
    # 允許存取的專案列表（空列表表示允許所有專案）
    allowed_projects: List[str] = Field(default_factory=list, description="允許存取的專案列表")
    
    # 是否為生產環境
    is_production: bool = Field(default=False, description="是否為生產環境")
    
    # 日誌等級
    log_level: str = Field(default="info", description="日誌等級")


# === 環境變數驗證與解析 ===

def validate_required_env(name: str, value: str | None) -> str:
    """驗證必填環境變數"""
    if not value or value.strip() == "":
        error_message = f"必填環境變數 {name} 未設定。請檢查 .env 檔案。"
        print(f"[York Config Error] {error_message}", file=os.sys.stderr)
        raise ValueError(error_message)
    return value.strip()


def get_projects_root() -> str:
    """取得專案根目錄路徑"""
    projects_root = os.getenv("PROJECTS_ROOT_DIR") or os.getenv("PROJECTS_DIR")
    return validate_required_env("PROJECTS_DIR (或 PROJECTS_ROOT_DIR)", projects_root)


def get_knowledge_root() -> str:
    """取得知識庫根目錄路徑"""
    knowledge_root = os.getenv("YORK_KNOWLEDGE_ROOT")
    
    if not knowledge_root or knowledge_root.strip() == "":
        default_path = PROJECT_ROOT_DIR / "york-knowledge"
        print(f"[York Config] YORK_KNOWLEDGE_ROOT 未設定，使用預設路徑: {default_path}", file=os.sys.stderr)
        return str(default_path)
    
    return knowledge_root.strip()


def get_allowed_projects() -> List[str]:
    """取得允許存取的專案列表"""
    allowed_projects_env = os.getenv("ALLOWED_PROJECTS", "")
    
    if not allowed_projects_env or allowed_projects_env.strip() == "":
        print("[York Config] ALLOWED_PROJECTS 未設定，允許存取所有專案", file=os.sys.stderr)
        return []
    
    projects = [
        p.strip()
        for p in allowed_projects_env.split(",")
        if p.strip()
    ]
    
    print(f"[York Config] 允許存取的專案: {', '.join(projects)}", file=os.sys.stderr)
    return projects


def is_production() -> bool:
    """取得環境類型"""
    return os.getenv("NODE_ENV") == "production"


def get_log_level() -> str:
    """取得日誌等級"""
    level = os.getenv("LOG_LEVEL", "").lower()
    
    if level in ["debug", "info", "warn", "error"]:
        return level
    
    # 預設：開發環境使用 debug，生產環境使用 info
    return "info" if is_production() else "debug"


# === 匯出配置 ===

# York 完整配置物件
config = YorkConfig(
    projects_root=get_projects_root(),
    knowledge_root=get_knowledge_root(),
    allowed_projects=get_allowed_projects(),
    is_production=is_production(),
    log_level=get_log_level(),
)

# 向後相容的匯出
PROJECTS_ROOT = config.projects_root
ALLOWED_PROJECTS = config.allowed_projects
KNOWLEDGE_ROOT = config.knowledge_root

# 記錄配置載入成功
print(
    f"[York Config] 配置載入完成 - "
    f"projects_root={config.projects_root}, "
    f"knowledge_root={config.knowledge_root}, "
    f"allowed_projects_count={len(config.allowed_projects)}, "
    f"environment={'production' if config.is_production else 'development'}, "
    f"log_level={config.log_level}",
    file=os.sys.stderr
)
