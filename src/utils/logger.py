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

# 全域 Console 實例
console = Console(theme=custom_theme, stderr=True)


class Logger:
    """日誌記錄器"""
    
    @staticmethod
    def debug(module: str, message: str, **kwargs: Any) -> None:
        """除錯日誌"""
        console.print(f"[debug][{module}][/debug] {message}", **kwargs)
    
    @staticmethod
    def info(module: str, message: str, **kwargs: Any) -> None:
        """資訊日誌"""
        console.print(f"[info][{module}][/info] {message}", **kwargs)
    
    @staticmethod
    def success(module: str, message: str, **kwargs: Any) -> None:
        """成功日誌"""
        console.print(f"[success]✓ [{module}][/success] {message}", **kwargs)
    
    @staticmethod
    def warning(module: str, message: str, **kwargs: Any) -> None:
        """警告日誌"""
        console.print(f"[warning]⚠ [{module}][/warning] {message}", **kwargs)
    
    @staticmethod
    def error(module: str, message: str, **kwargs: Any) -> None:
        """錯誤日誌"""
        console.print(f"[error]✗ [{module}][/error] {message}", **kwargs)
    
    @staticmethod
    def fatal(module: str, message: str, exit_code: int = 1, **kwargs: Any) -> None:
        """致命錯誤日誌（會終止程式）"""
        console.print(f"[error]💥 [{module}][/error] {message}", **kwargs)
        sys.exit(exit_code)
