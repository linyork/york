"""
知識庫向量同步模組
負責知識文件與向量資料庫的同步操作
"""

from pathlib import Path
from typing import Dict, Any

from src.config import config
from src.constants import KNOWLEDGE_CONSTANTS
from src.services.vector import VectorStore
from src.models.vector import VectorDoc
from src.utils.logger import Logger
from src.utils.splitter import split_markdown
from src.utils.project import get_project_path, list_projects
from src.knowledge.core import read_knowledge, list_knowledge


async def sync_to_vector_store(
    project_name: str,
    safe_name: str,
    content: str,
    tags: list[str],
    metadata: Dict[str, Any] = None
) -> None:
    """
    同步知識文件至向量資料庫
    使用 Small-to-Big 切分策略
    
    Args:
        project_name: 專案名稱
        safe_name: 安全的檔案名稱（含 .md）
        content: 文件內容
        tags: 標籤列表
        metadata: Metadata 資訊
    """
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 使用檔案名稱作為 parent_id
    parent_id = f"{project_name}:{safe_name}"
    
    # 先刪除該檔案的舊 chunks
    await store.delete_by_parent_id(parent_id)
    
    # 切分 Markdown 文件
    chunks = split_markdown(parent_id, content)
    
    if not chunks:
        Logger.warning("Sync", f"文件無有效 chunks，跳過同步: {safe_name}")
        return
    
    Logger.info("Sync", f"正在同步 {len(chunks)} 個 chunks: {safe_name}")
    
    # 準備 metadata
    meta = metadata or {}
    framework = meta.get('framework')
    framework_layer = meta.get('framework_layer') or meta.get('frameworkLayer')
    code_type = meta.get('code_type') or meta.get('codeType')
    symbol_name = meta.get('symbol_name') or meta.get('symbolName')
    related_files = meta.get('related_files', []) or meta.get('relatedFiles', [])
    context_description = meta.get('context_description') or meta.get('contextDescription')
    
    # 批次準備所有 chunks 文件
    docs = []
    for chunk in chunks:
        doc = VectorDoc(
            id=chunk.id,
            content=chunk.content,
            parent_id=parent_id,
            project_name=project_name,
            tags=tags,
            framework=framework,
            framework_layer=framework_layer,
            code_type=code_type,
            symbol_name=symbol_name,
            header_path=chunk.header_path,
            preview=chunk.preview,
            related_files=related_files,
            context_description=context_description
        )
        docs.append(doc)

    # 批次插入
    await store.upsert_batch(docs)
    
    Logger.success("Sync", f"同步完成: {safe_name} ({len(chunks)} chunks)")


async def delete_from_vector_store(
    project_name: str,
    safe_name: str
) -> None:
    """
    從向量資料庫刪除知識文件
    
    Args:
        project_name: 專案名稱
        safe_name: 安全的檔案名稱（含 .md）
    """
    store = VectorStore.get_instance()
    await store.initialize()
    
    parent_id = f"{project_name}:{safe_name}"
    
    await store.delete_by_parent_id(parent_id)
    
    Logger.success("Sync", f"已從向量資料庫刪除: {safe_name}")


async def reindex_knowledge(
    project_name: str
) -> Dict[str, int]:
    """
    重建專案的向量索引
    掃描知識庫中的所有 Markdown 檔案並重新同步
    
    Args:
        project_name: 專案名稱
        
    Returns:
        處理結果統計 {"count": 成功數, "errors": 錯誤數}
    """
    Logger.info("Reindex", f"開始重建向量索引: {project_name}")
    
    project_path = get_project_path(project_name)
    
    if not project_path.exists():
        Logger.warning("Reindex", f"專案目錄不存在: {project_name}")
        return {"count": 0, "errors": 0}
    
    # 取得所有知識文件
    knowledge_list = await list_knowledge(project_name)
    
    count = 0
    errors = 0
    
    for item in knowledge_list:
        try:
            # 讀取文件
            knowledge_file = await read_knowledge(project_name, item['name'])
            
            # 同步到向量資料庫
            await sync_to_vector_store(
                project_name=project_name,
                safe_name=knowledge_file.safe_name,
                content=knowledge_file.content,
                tags=knowledge_file.metadata.tags,
                metadata={
                    'framework': knowledge_file.metadata.framework,
                    'framework_layer': knowledge_file.metadata.framework_layer,
                    'code_type': knowledge_file.metadata.code_type,
                    'symbol_name': knowledge_file.metadata.symbol_name,
                    'related_files': knowledge_file.metadata.related_files,
                    'context_description': knowledge_file.metadata.context_description
                }
            )
            
            count += 1
        
        except Exception as e:
            Logger.error("Reindex", f"處理文件失敗 {item['name']}: {e}")
            errors += 1
    
    Logger.success("Reindex", f"重建索引完成: {count} 個文件, {errors} 個錯誤")
    
    return {"count": count, "errors": errors}


async def reindex_all_projects() -> Dict[str, Dict[str, int]]:
    """
    重建所有專案的向量索引
    
    Returns:
        每個專案的處理結果
    """
    projects = await list_projects()
    
    results = {}
    
    for project_name in projects:
        try:
            result = await reindex_knowledge(project_name)
            results[project_name] = result
        except Exception as e:
            Logger.error("Reindex", f"重建專案索引失敗 {project_name}: {e}")
            results[project_name] = {"count": 0, "errors": 1}
    
    return results
