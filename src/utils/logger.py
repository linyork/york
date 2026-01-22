"""
York 日誌系統
使用 Rich 提供美化的終端輸出
"""

import sys
from typing import Any
from rich.console import Console
from rich.theme import Theme

# 自定義主題
custom_theme = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "debug": "dim",
})

# 全域 Console 實例 (輸出至 STDERR 以避免干擾 MCP)
console = Console(theme=custom_theme, stderr=True)

# 日誌等級權重
LOG_LEVELS = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "error": 40,
}

class Logger:
    """日誌記錄器"""
    
    @staticmethod
    def _should_log(level: str) -> bool:
        """檢查是否應該記錄該等級的日誌"""
        # 延遲導入以避免循環依賴
        from src.config import config
        
        current_level_weight = LOG_LEVELS.get(level, 20)
        config_level_weight = LOG_LEVELS.get(config.log_level.lower(), 20) # 預設 info
        
        return current_level_weight >= config_level_weight
    
    @staticmethod
    def debug(module: str, message: str, **kwargs: Any) -> None:
        """除錯日誌 (Level: debug)"""
        if Logger._should_log("debug"):
            console.print(f"[debug][{module}][/debug] {message}", **kwargs)
    
    @staticmethod
    def info(module: str, message: str, **kwargs: Any) -> None:
        """資訊日誌 (Level: info)"""
        if Logger._should_log("info"):
            console.print(f"[info][{module}][/info] {message}", **kwargs)
    
    @staticmethod
    def success(module: str, message: str, **kwargs: Any) -> None:
        """成功日誌 (Level: info)"""
        if Logger._should_log("info"):
            console.print(f"[success]✓ [{module}][/success] {message}", **kwargs)
    
    @staticmethod
    def warning(module: str, message: str, **kwargs: Any) -> None:
        """警告日誌 (Level: warn)"""
        if Logger._should_log("warn"):
            console.print(f"[warning]⚠ [{module}][/warning] {message}", **kwargs)
    
    @staticmethod
    def error(module: str, message: str, **kwargs: Any) -> None:
        """錯誤日誌 (Level: error)"""
        if Logger._should_log("error"):
            console.print(f"[error]✗ [{module}][/error] {message}", **kwargs)
    
    @staticmethod
    def fatal(module: str, message: str, exit_code: int = 1, **kwargs: Any) -> None:
        """致命錯誤日誌 (Level: error) - 始終輸出"""
        # Fatal 錯誤無法被抑制
        console.print(f"[error]💥 [{module}][/error] {message}", **kwargs)
        sys.exit(exit_code)
