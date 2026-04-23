"""
安全工具模組
提供各種安全相關的工具函式
"""

import re
from typing import Optional

# 欄位值最大長度（防止超大字串塞入 DB）
_MAX_FIELD_LENGTH = 1024


def escape_sql_string(s: Optional[str], max_length: int = _MAX_FIELD_LENGTH) -> str:
    """
    清理並跳脫 SQL 字串，防止 SQL Injection。

    處理：
    - None 轉空字串
    - 移除 null bytes 與控制字元（LanceDB/DuckDB 不支援）
    - 單引號 → 雙單引號（標準 SQL escaping）
    - 截斷超長字串

    Args:
        s: 原始字串
        max_length: 最大允許長度（預設 1024）

    Returns:
        清理並跳脫後的安全字串
    """
    if s is None:
        return ""

    # 移除 null bytes 與 ASCII 控制字元（\x00-\x1f，保留 \t \n \r）
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)

    # 截斷超長字串
    if len(s) > max_length:
        s = s[:max_length]

    # 單引號 → 雙單引號（標準 SQL escaping）
    s = s.replace("'", "''")

    return s


def escape_sql_like(s: str) -> str:
    """
    跳脫 SQL LIKE 模式中的特殊字元。

    處理：
    - 單引號 → 雙單引號
    - % → \\%（避免被當萬用字元）
    - _ → \\_（避免被當單字元萬用字元）
    - \\ → \\\\（逸出符號本身）

    使用方式：WHERE content LIKE '%{escape_sql_like(kw)}%' ESCAPE '\\'
    """
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    s = s.replace("\\", "\\\\")
    s = s.replace("%", "\\%")
    s = s.replace("_", "\\_")
    s = s.replace("'", "''")
    return s


def validate_metadata_field(value: Optional[str], field_name: str, max_length: int = _MAX_FIELD_LENGTH) -> Optional[str]:
    """
    驗證並清理 metadata 欄位值。

    Args:
        value: 欄位值
        field_name: 欄位名稱（用於錯誤訊息）
        max_length: 最大允許長度

    Returns:
        清理後的值，或 None

    Raises:
        ValueError: 欄位值格式不符
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"欄位 '{field_name}' 必須為字串，收到: {type(value).__name__}")

    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value).strip()

    if len(cleaned) > max_length:
        raise ValueError(f"欄位 '{field_name}' 超過最大長度 {max_length}，實際長度: {len(cleaned)}")

    return cleaned or None
