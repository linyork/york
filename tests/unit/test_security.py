"""
Unit tests for security utilities
"""

import pytest
from src.utils.security import escape_sql_string

def test_escape_sql_string_basic():
    """Test basic string escaping"""
    assert escape_sql_string("hello") == "hello"
    assert escape_sql_string("don't") == "don''t"
    assert escape_sql_string("' OR '1'='1") == "'' OR ''1''=''1"

def test_escape_sql_string_empty():
    """Test escaping empty strings"""
    assert escape_sql_string("") == ""

def test_escape_sql_string_none():
    """Test escaping None"""
    assert escape_sql_string(None) == ""

def test_escape_sql_string_complex():
    """Test complex SQL injection attempt"""
    s = "'; DROP TABLE users; --"
    expected = "''; DROP TABLE users; --"
    assert escape_sql_string(s) == expected
