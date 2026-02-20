"""
安全工具模組
提供各種安全相關的工具函式
"""

from typing import Optional

def escape_sql_string(s: Optional[str]) -> str:
    """
    跳脫 SQL 字串中的單引號，防止 SQL Injection

    Args:
        s: 原始字串

    Returns:
        跳脫後的字串（若輸入為 None 則回傳空字串）
    """
    if s is None:
        return ""

    return s.replace("'", "''")
