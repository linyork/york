"""
York MCP Server
使用 FastMCP 框架實作 MCP 協定
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP

from src.config import config
from src.constants import MCP_CONSTANTS
from src.knowledge.core import (
    save_knowledge,
    read_knowledge,
    list_knowledge,
    delete_knowledge,
    get_project_knowledge
)
from src.knowledge.sync import (
    sync_to_vector_store,
    delete_from_vector_store,
    reindex_knowledge
)
from src.knowledge.search import search_knowledge
from src.services.vector import VectorStore
from src.utils.logger import Logger
from src.utils.project import list_projects
from src.structure import (
    get_project_structure, 
    save_project_structure, 
    detect_project_structure
)

# 建立 MCP Server 實例
mcp = FastMCP(MCP_CONSTANTS.SERVER_NAME)


# === 知識管理 Tools ===

@mcp.tool()
async def save_knowledge_tool(
    project_name: str,
    name: str,
    content: str,
    tags: Optional[List[str]] = None,
    framework: Optional[str] = None,
    framework_layer: Optional[str] = None,
    code_type: Optional[str] = None,
    symbol_name: Optional[str] = None,
    related_files: Optional[List[str]] = None,
    context_description: Optional[str] = None
) -> Dict[str, str]:
    """
    儲存知識文件到專案知識庫
    
    Args:
        project_name: 專案名稱
        name: 知識主題或檔案名稱
        content: 要儲存的內容（Markdown 格式）
        tags: 標籤列表（選填）
        framework: 所屬框架（選填，例如：Laravel, React）
        framework_layer: 框架層級（選填，例如：Controller, Service）
        code_type: 程式碼類型（選填，例如：logic, feature, guide）
        symbol_name: 主要符號名稱（選填，例如：UserController）
        related_files: 相關檔案列表（選填）
        context_description: 上下文描述（選填）
    
    Returns:
        包含檔案路徑的字典
    """
    Logger.info("MCP", f"save_knowledge: {project_name}/{name}")
    
    # 準備 metadata
    metadata = {}
    if framework:
        metadata['framework'] = framework
    if framework_layer:
        metadata['framework_layer'] = framework_layer
    if code_type:
        metadata['code_type'] = code_type
    if symbol_name:
        metadata['symbol_name'] = symbol_name
    if related_files:
        metadata['related_files'] = related_files
    if context_description:
        metadata['context_description'] = context_description
    
    # 儲存知識
    result = await save_knowledge(
        project_name=project_name,
        name=name,
        content=content,
        tags=tags or [],
        metadata=metadata
    )
    
    # 同步到向量資料庫
    await sync_to_vector_store(
        project_name=project_name,
        safe_name=result['name'],
        content=content,
        tags=tags or [],
        metadata=metadata
    )
    
    return result


@mcp.tool()
async def read_knowledge_tool(
    project_name: str,
    name: str
) -> Dict[str, Any]:
    """
    讀取知識文件
    
    Args:
        project_name: 專案名稱
        name: 檔案名稱
    
    Returns:
        知識文件內容與 metadata
    """
    Logger.info("MCP", f"read_knowledge: {project_name}/{name}")
    
    knowledge_file = await read_knowledge(project_name, name)
    
    return {
        "name": knowledge_file.name,
        "content": knowledge_file.content,
        "tags": knowledge_file.metadata.tags,
        "framework": knowledge_file.metadata.framework,
        "framework_layer": knowledge_file.metadata.framework_layer,
        "code_type": knowledge_file.metadata.code_type,
        "symbol_name": knowledge_file.metadata.symbol_name,
        "related_files": knowledge_file.metadata.related_files,
        "context_description": knowledge_file.metadata.context_description
    }


@mcp.tool()
async def list_knowledge_tool(
    project_name: str,
    tag: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    列出專案的所有知識文件
    
    Args:
        project_name: 專案名稱
        tag: 標籤過濾（選填）
    
    Returns:
        知識文件資訊列表
    """
    Logger.info("MCP", f"list_knowledge: {project_name}")
    
    return await list_knowledge(project_name, tag)


@mcp.tool()
async def delete_knowledge_tool(
    project_name: str,
    name: str
) -> Dict[str, str]:
    """
    刪除知識文件
    
    Args:
        project_name: 專案名稱
        name: 檔案名稱
    
    Returns:
        刪除結果
    """
    Logger.info("MCP", f"delete_knowledge: {project_name}/{name}")
    
    # 取得檔案的完整名稱
    if not name.endswith('.md'):
        name += '.md'
    
    # 從檔案系統刪除
    await delete_knowledge(project_name, name)
    
    # 從向量資料庫刪除
    await delete_from_vector_store(project_name, name)
    
    return {"status": "deleted", "name": name}


@mcp.tool()
async def search_knowledge_tool(
    project_name: str,
    query: str,
    framework: Optional[str] = None,
    framework_layer: Optional[str] = None,
    code_type: Optional[str] = None,
    symbol_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜尋知識文件內容（混合檢索：關鍵字 + 語意搜尋）
    
    Args:
        project_name: 專案名稱
        query: 搜尋查詢
        framework: 框架過濾（選填）
        framework_layer: 框架層級過濾（選填）
        code_type: 程式碼類型過濾（選填）
        symbol_name: 符號名稱過濾（選填）
    
    Returns:
        搜尋結果與使用指引
    """
    Logger.info("MCP", f"search_knowledge: {project_name} - {query}")
    
    # 準備過濾選項
    options = {}
    if framework:
        options['framework'] = framework
    if framework_layer:
        options['frameworkLayer'] = framework_layer
    if code_type:
        options['codeType'] = code_type
    if symbol_name:
        options['symbolName'] = symbol_name
    
    # 執行搜尋
    results = await search_knowledge(project_name, query, options if options else None)
    
    # 準備使用指引
    instructions = """【AI 知識處理守則】
1. **解讀分數 (Interpret Scores)**：Score > 0.03 代表 [關鍵字+向量] 雙重命中，可信度極高；Score < 0.02 代表僅單邊命中，需謹慎採用。
2. **視為線索 (Treat as Clues)**：搜尋結果僅代表「過去的紀錄」，非絕對真理。
3. **強制驗證 (Verify Implementation)**：判斷邏輯時，必須調閱實際程式碼 (`view_file`) 確認現況。
4. **衝突仲裁 (Conflict Resolution)**：當 [程式碼] 與 [知識庫] 衝突時，**絕對以程式碼為準**，並標記文件過時。
5. **深度合成 (Synthesize)**：禁止單純摘要內容。必須將知識邏輯「內化」後，結合當前 User Request 與程式碼狀態，推導出具體解決方案。
6. **知識閉環 (Close the Loop)**：若發現 [程式碼] 與 [知識庫] 不一致，請在回答最後**主動詢問**使用者：「偵測到知識庫文件與最新的程式碼邏輯不一致（或缺失），是否要我為您更新知識庫文件？」並準備好呼叫 `save_knowledge`。"""
    
    return {
        "instructions": instructions,
        "results": results
    }


@mcp.tool()
async def reindex_knowledge_tool(
    project_name: str
) -> Dict[str, int]:
    """
    重建專案的向量索引
    掃描知識庫中的所有 Markdown 檔案並重新同步
    
    Args:
        project_name: 專案名稱
    
    Returns:
        處理結果統計
    """
    Logger.info("MCP", f"reindex_knowledge: {project_name}")
    
    return await reindex_knowledge(project_name)


@mcp.tool()
async def get_project_knowledge_tool(
    project_name: str
) -> str:
    """
    取得專案的完整知識彙整 (friday-knowledge.md)
    
    Args:
        project_name: 專案名稱
    
    Returns:
        知識彙整內容（Markdown）
    """
    Logger.info("MCP", f"get_project_knowledge: {project_name}")
    
    return await get_project_knowledge(project_name)


# === 專案管理 Tools ===

# ... (Tools 定義保持不變) ...

# === Resources (被動讀取) ===

@mcp.resource("project://{project_name}/structure")
async def project_structure_resource(project_name: str) -> str:
    """
    [Resource] 專案結構配置檔 (project.structure.yml)
    提供專案的目錄結構與架構定義，適合放入 Context 以協助理解專案全貌。
    """
    Logger.info("MCP", f"Resource Access: Structure ({project_name})")
    try:
        return await get_project_structure(project_name)
    except FileNotFoundError:
        return f"# 專案 {project_name} 尚未建立結構配置檔。\n# 請使用 detect_project_structure 工具生成。"


@mcp.resource("project://{project_name}/knowledge/{file_name}")
async def project_knowledge_file_resource(project_name: str, file_name: str) -> str:
    """
    [Resource] 單一知識文件
    讀取特定的知識文件內容。
    用法：@project://my-project/knowledge/auth-flow.md
    """
    Logger.info("MCP", f"Resource Access: Knowledge ({project_name}/{file_name})")
    try:
        # 修正: 直接呼叫底層的 read_knowledge 函數 (回傳 KnowledgeFile 物件)
        knowledge_file = await read_knowledge(project_name, file_name)
        return knowledge_file.content
    except Exception as e:
        Logger.error("MCP", f"Resource Read Error: {e}")
        return f"錯誤：無法讀取知識文件 {file_name} (專案: {project_name})\n原因: {str(e)}"

# === 專案管理 Tools (接續) ===
@mcp.tool()
async def detect_project_structure_tool(
    project_path: str,
    project_name: str
) -> str:
    """
    掃描目前專案結構並產生建議的配置檔內容 (YAML)
    
    Args:
        project_path: 專案根目錄絕對路徑
        project_name: 專案名稱 (用於生成配置)
        
    Returns:
        YAML 配置建議內容
    """
    Logger.info("MCP", f"detect_project_structure: {project_path}")
    return await detect_project_structure(project_path, project_name)


@mcp.tool()
async def get_project_structure_tool(
    project_name: str
) -> str:
    """
    讀取專案目前的結構配置檔 (project.structure.yml)
    
    Args:
        project_name: 專案名稱
        
    Returns:
        YAML 配置內容
    """
    Logger.info("MCP", f"get_project_structure: {project_name}")
    try:
        return await get_project_structure(project_name)
    except FileNotFoundError:
        import traceback
        return f"找不到專案結構配置檔。建議使用 detect_project_structure 工具生成。"


@mcp.tool()
async def save_project_structure_tool(
    project_name: str,
    content: str
) -> str:
    """
    儲存或更新專案的結構配置檔 (project.structure.yml)
    
    Args:
        project_name: 專案名稱
        content: YAML 配置內容
        
    Returns:
        執行結果訊息
    """
    Logger.info("MCP", f"save_project_structure: {project_name}")
    try:
        return await save_project_structure(project_name, content)
    except Exception as e:
        Logger.error("MCP", f"儲存結構配置失敗: {e}")
        return f"錯誤: {str(e)}"


@mcp.tool()
async def list_projects_tool() -> List[str]:
    """
    列出所有可用的專案
    
    Returns:
        專案名稱列表
    """
    Logger.info("MCP", "list_projects")
    
    return await list_projects()


# === 向量資料庫 Tools ===

@mcp.tool()
async def get_vector_db_stats_tool() -> Dict[str, Any]:
    """
    取得向量資料庫的狀態統計資訊
    
    Returns:
        資料庫統計資訊
    """
    Logger.info("MCP", "get_vector_db_stats")
    
    store = VectorStore.get_instance()
    await store.initialize()
    
    db_stats = await store.get_stats()
    cache_stats = store.get_cache_stats()
    
    return {
        "database": {
            "table_exists": db_stats.table_exists,
            "total_count": db_stats.total_count,
            "vector_dim": db_stats.vector_dim,
            "model_name": db_stats.model_name
        },
        "cache": {
            "hits": cache_stats.hits,
            "misses": cache_stats.misses,
            "size": cache_stats.size,
            "max_size": cache_stats.max_size,
            "hit_rate": cache_stats.hit_rate
        }
    }


# === Resources (暫時不實作，未來可擴展) ===

# 啟動 Server
if __name__ == "__main__":
    Logger.info("MCP", f"啟動 York MCP Server v{MCP_CONSTANTS.SERVER_VERSION}")
    mcp.run()
