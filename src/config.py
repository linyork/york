"""
York MCP Server 配置模組
負責載入與驗證所有環境變數與系統設定

設計原則：
- 模組 import 本身不觸發環境變數驗證（lazy loading）
- 首次存取 config.xxx 時才建立 YorkConfig 實例
- 測試時可透過 config._reset() 重置，再設定 os.environ 後重新讀取
"""

import os
from pathlib import Path
from typing import List, Optional
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

    # 知識庫根目錄路徑（本機 .data 資料夾）
    knowledge_root: str = Field(default="", description="知識庫根目錄路徑")

    # 向量資料庫路徑（本機，避免 FUSE deadlock）
    vector_db_path: str = Field(..., description="LanceDB 向量資料庫路徑（應為本機路徑）")

    # 允許存取的專案列表（空列表表示允許所有專案）
    allowed_projects: List[str] = Field(default_factory=list, description="允許存取的專案列表")

    # 是否為生產環境
    is_production: bool = Field(default=False, description="是否為生產環境")

    # 日誌等級
    log_level: str = Field(default="info", description="日誌等級")


# === 環境變數驗證與解析 ===

def validate_required_env(name: str, value: "str | None") -> str:
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
    """取得知識庫根目錄路徑，預設為專案內的 .data 資料夾"""
    knowledge_root = os.getenv("YORK_KNOWLEDGE_ROOT")

    if not knowledge_root or knowledge_root.strip() == "":
        default_path = PROJECT_ROOT_DIR / ".data"
        print(f"[York Config] YORK_KNOWLEDGE_ROOT 未設定，使用本機預設路徑: {default_path}", file=os.sys.stderr)
        return str(default_path)

    return knowledge_root.strip()


def get_vector_db_path() -> str:
    """取得 LanceDB 向量資料庫路徑（本機路徑，避免 FUSE deadlock）

    優先使用 YORK_VECTOR_DB_PATH 環境變數。
    若未設定，預設存放在 york 專案目錄下的 .data/lancedb/ 資料夾。
    這個路徑絕對不能指向 Google Drive 等遠端掛載路徑。
    """
    vector_db_path = os.getenv("YORK_VECTOR_DB_PATH")

    if not vector_db_path or vector_db_path.strip() == "":
        default_path = PROJECT_ROOT_DIR / ".data" / "lancedb"
        print(f"[York Config] YORK_VECTOR_DB_PATH 未設定，使用本機預設路徑: {default_path}", file=os.sys.stderr)
        return str(default_path)

    return vector_db_path.strip()


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


# === Lazy Config 建構 ===

def _build_config() -> YorkConfig:
    """建立 YorkConfig 實例並印出摘要（首次呼叫時執行）"""
    instance = YorkConfig(
        projects_root=get_projects_root(),
        knowledge_root=get_knowledge_root(),
        vector_db_path=get_vector_db_path(),
        allowed_projects=get_allowed_projects(),
        is_production=is_production(),
        log_level=get_log_level(),
    )
    print(
        f"[York Config] 配置載入完成 - "
        f"projects_root={instance.projects_root}, "
        f"knowledge_root={instance.knowledge_root}, "
        f"vector_db_path={instance.vector_db_path}, "
        f"allowed_projects_count={len(instance.allowed_projects)}, "
        f"environment={'production' if instance.is_production else 'development'}, "
        f"log_level={instance.log_level}",
        file=os.sys.stderr
    )
    return instance


class _LazyConfig:
    """
    延遲初始化的 Config Proxy。

    模組 import 時不觸發環境變數驗證；
    首次存取任何屬性（如 config.knowledge_root）時才建立 YorkConfig 實例。

    測試用法：
        config._reset()
        os.environ['PROJECTS_DIR'] = '/tmp/test'
        assert config.projects_root == '/tmp/test'
    """

    _instance: Optional[YorkConfig] = None

    def __getattr__(self, name: str):
        # 建立實例（double-checked 不需要，GIL 保護單執行緒 import）
        if type(self)._instance is None:
            type(self)._instance = _build_config()
        return getattr(type(self)._instance, name)

    def _reset(self) -> None:
        """重置快取，下次存取時重新讀取環境變數（主要用於測試）"""
        type(self)._instance = None


def get_config() -> YorkConfig:
    """
    取得 YorkConfig 實例（lazy singleton）。

    等同於 config，但回傳型別明確為 YorkConfig，
    適合需要型別提示的場景。
    """
    # 觸發 _LazyConfig.__getattr__ 並返回底層實例
    if _LazyConfig._instance is None:
        _LazyConfig._instance = _build_config()
    return _LazyConfig._instance


# === 模組級單例（向後相容，所有 `from src.config import config` 不需修改） ===

config = _LazyConfig()
