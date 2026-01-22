"""
測試 MCP Server Tools 註冊狀態
"""

import pytest
import sys
from pathlib import Path

# 確保可以 import src
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.agent_server.server import (
    mcp,
    save_knowledge_tool,
    read_knowledge_tool,
    list_knowledge_tool,
    search_knowledge_tool,
    delete_knowledge_tool,
    reindex_knowledge_tool,
    get_vector_db_stats_tool,
    list_projects_tool
)

@pytest.mark.asyncio
async def test_mcp_tools_registration():
    """測試 MCP Tools 是否正確註冊為 FastMCP 物件"""
    
    tools_to_check = [
        (save_knowledge_tool, "save_knowledge_tool"),
        (read_knowledge_tool, "read_knowledge_tool"),
        (list_knowledge_tool, "list_knowledge_tool"),
        (search_knowledge_tool, "search_knowledge_tool"),
        (delete_knowledge_tool, "delete_knowledge_tool"),
        (reindex_knowledge_tool, "reindex_knowledge_tool"),
        (get_vector_db_stats_tool, "get_vector_db_stats_tool"),
        (list_projects_tool, "list_projects_tool")
    ]
    
    for tool_obj, expected_name in tools_to_check:
        # 1. 檢查工具名稱
        assert tool_obj.name == expected_name, f"Tool name mismatch: {tool_obj.name} != {expected_name}"
        
        # 2. 檢查內部原始函數是否可呼叫
        assert callable(tool_obj.fn), f"Underlying function for {expected_name} should be callable"
        
        # 3. 檢查說明文件
        assert tool_obj.description is not None, f"Description for {expected_name} is missing"

    # 4. 針對特定工具的參數結構檢查
    # 根據報錯，tool_obj.parameters 現在是一個 dict，直接從 dict 檢查 key
    save_params = save_knowledge_tool.parameters
    assert "project_name" in save_params.get("properties", {}), "Parameter 'project_name' missing in save_knowledge_tool"
    assert "content" in save_params.get("properties", {}), "Parameter 'content' missing in save_knowledge_tool"

@pytest.mark.asyncio
async def test_mcp_server_registry():
    """測試這些工具是否真的有註冊到 mcp server 實例中"""
    
    # 根據報錯修正方法名稱: list_tools -> get_tools
    # 取得 mcp server 內所有已註冊的工具
    # get_tools 是一個 async 函數，必須 await
    # 注意：FastMCP 的 get_tools 回傳的是 Dict[str, Tool]，key 為工具名稱
    registered_tools = await mcp._tool_manager.get_tools()
    
    # 由於 registered_tools 是 dict，直接取 keys 即可
    registered_tool_names = list(registered_tools.keys())
    
    expected_names = [
        "save_knowledge_tool",
        "read_knowledge_tool",
        "list_knowledge_tool",
        "search_knowledge_tool",
        "delete_knowledge_tool",
        "reindex_knowledge_tool",
        "get_vector_db_stats_tool",
        "list_projects_tool"
    ]
    
    for name in expected_names:
        assert name in registered_tool_names, f"Tool {name} was not registered in the MCP server instance"