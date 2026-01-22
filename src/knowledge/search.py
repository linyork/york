"""
知識庫搜尋模組
實作 Hybrid Retrieval（關鍵字 + 語意搜尋）+ RRF
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.services.vector import VectorStore
from src.utils.logger import Logger
from src.utils.project import get_project_path
from src.knowledge.core import list_knowledge, read_knowledge


@dataclass
class SearchResult:
    """搜尋結果"""
    name: str
    preview: str
    tags: List[str]
    score: float
    verification_hints: List[str]
    context: Optional[Dict[str, Any]] = None


async def keyword_search(
    project_name: str,
    query: str
) -> List[SearchResult]:
    """
    關鍵字搜尋
    在檔案名稱與標籤中搜尋
    
    Args:
        project_name: 專案名稱
        query: 搜尋查詢
        
    Returns:
        搜尋結果列表
    """
    knowledge_list = await list_knowledge(project_name)
    
    results = []
    query_lower = query.lower()
    
    for item in knowledge_list:
        score = 0.0
        hints = []
        
        # 檢查檔案名稱
        if query_lower in item['name'].lower():
            score += 5.0
            hints.append(f"檔案名稱: {item['name']}")
        
        # 檢查標籤
        for tag in item.get('tags', []):
            if query_lower in tag.lower():
                score += 3.0
                hints.append(f"標籤: {tag}")
        
        # 檢查 code_type
        code_type = item.get('code_type')
        if code_type and query_lower in code_type.lower():
            score += 2.0
            hints.append(f"類型: {code_type}")
        
        if score > 0:
            # 讀取文件以取得預覽
            try:
                knowledge_file = await read_knowledge(project_name, item['name'])
                preview = knowledge_file.content[:200] + "..."
            except:
                preview = item['name']
            
            results.append(SearchResult(
                name=item['name'],
                preview=preview,
                tags=item.get('tags', []),
                score=score,
                verification_hints=hints
            ))
    
    # 按分數排序
    results.sort(key=lambda x: x.score, reverse=True)
    
    return results[:10]  # 返回前 10 個結果


async def vector_search(
    project_name: str,
    query: str,
    options: Optional[Dict[str, str]] = None
) -> List[SearchResult]:
    """
    向量語意搜尋
    
    Args:
        project_name: 專案名稱
        query: 搜尋查詢
        options: 結構化過濾選項
        
    Returns:
        搜尋結果列表
    """
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 建構過濾條件
    filter_expr = f"projectName = '{project_name}'"
    
    if options:
        if options.get('framework'):
            filter_expr += f" AND framework = '{options['framework']}'"
        if options.get('frameworkLayer'):
            filter_expr += f" AND frameworkLayer = '{options['frameworkLayer']}'"
        if options.get('codeType'):
            filter_expr += f" AND codeType = '{options['codeType']}'"
        if options.get('symbolName'):
            filter_expr += f" AND symbolName = '{options['symbolName']}'"
    
    # 執行向量搜尋
    docs = await store.search(
        query=query,
        limit=10,
        filter_expr=filter_expr
    )
    
    results = []
    
    for doc in docs:
        # 提取檔案名稱（從 parent_id）
        parent_id_parts = doc.parent_id.split(':')
        file_name = parent_id_parts[1] if len(parent_id_parts) > 1 else doc.parent_id
        
        results.append(SearchResult(
            name=file_name,
            preview=doc.preview or doc.content[:200],
            tags=doc.tags,
            score=0.5,  # 向量搜尋的預設分數
            verification_hints=[f"Header: {doc.header_path}"] if doc.header_path else [],
            context={
                "chunk_id": doc.id,
                "parent_id": doc.parent_id,
                "header_path": doc.header_path
            }
        ))
    
    return results


def reciprocal_rank_fusion(
    keyword_results: List[SearchResult],
    vector_results: List[SearchResult],
    k: int = 60
) -> List[SearchResult]:
    """
    Reciprocal Rank Fusion (RRF)
    合併關鍵字與向量搜尋結果
    
    Args:
        keyword_results: 關鍵字搜尋結果
        vector_results: 向量搜尋結果
        k: RRF 常數（預設 60）
        
    Returns:
        合併後的結果
    """
    # 使用字典追蹤每個文件的分數
    scores: Dict[str, float] = {}
    result_map: Dict[str, SearchResult] = {}
    
    # 處理關鍵字搜尋結果
    for rank, result in enumerate(keyword_results, 1):
        rrf_score = 1.0 / (k + rank)
        scores[result.name] = scores.get(result.name, 0) + rrf_score * 2  # 關鍵字權重 x2
        
        if result.name not in result_map:
            result_map[result.name] = result
        else:
            # 合併 hints
            result_map[result.name].verification_hints.extend(result.verification_hints)
    
    # 處理向量搜尋結果
    for rank, result in enumerate(vector_results, 1):
        rrf_score = 1.0 / (k + rank)
        scores[result.name] = scores.get(result.name, 0) + rrf_score
        
        if result.name not in result_map:
            result_map[result.name] = result
        else:
            # 合併 context
            if result.context:
                result_map[result.name].context = result.context
    
    # 建立最終結果列表
    final_results = []
    for name, score in scores.items():
        result = result_map[name]
        result.score = score
        final_results.append(result)
    
    # 按分數排序
    final_results.sort(key=lambda x: x.score, reverse=True)
    
    return final_results


async def search_knowledge(
    project_name: str,
    query: str,
    options: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    搜尋知識文件內容
    使用混合檢索 (Keyword + Vector Search + RRF)
    
    Args:
        project_name: 專案名稱
        query: 搜尋查詢
        options: 結構化過濾選項
        
    Returns:
        搜尋結果列表
    """
    Logger.info("Search", f"搜尋知識: {project_name} - {query}")
    
    # 並行執行兩種搜尋
    import asyncio
    keyword_task = keyword_search(project_name, query)
    vector_task = vector_search(project_name, query, options)
    
    keyword_results, vector_results = await asyncio.gather(keyword_task, vector_task)
    
    # RRF 合併結果
    merged_results = reciprocal_rank_fusion(keyword_results, vector_results)
    
    Logger.debug("Search", f"找到 {len(merged_results)} 個結果")
    
    # 轉換為字典格式
    return [
        {
            "name": r.name,
            "preview": r.preview,
            "tags": r.tags,
            "score": r.score,
            "verificationHints": r.verification_hints,
            "context": r.context
        }
        for r in merged_results[:10]  # 返回前 10 個結果
    ]


async def expand_context(
    chunk_id: str,
    parent_id: str
) -> Dict[str, Any]:
    """
    擴展 Chunk 上下文
    取得前一個與後一個 Chunk 的內容
    
    Args:
        chunk_id: Chunk ID
        parent_id: 父文件 ID
        
    Returns:
        包含前、當前、後 chunk 的字典
    """
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 取得所有該文件的 chunks
    chunks = await store.query(f"parent_id = '{parent_id}'", limit=100)
    
    if not chunks:
        return {"before": None, "current": None, "after": None}
    
    # 找到當前 chunk 的位置
    current_idx = None
    for i, chunk in enumerate(chunks):
        if chunk.id == chunk_id:
            current_idx = i
            break
    
    if current_idx is None:
        return {"before": None, "current": None, "after": None}
    
    # 取得前後 chunks
    before = chunks[current_idx - 1] if current_idx > 0 else None
    current = chunks[current_idx]
    after = chunks[current_idx + 1] if current_idx < len(chunks) - 1 else None
    
    return {
        "before": {
            "id": before.id,
            "header_path": before.header_path,
            "content": before.content,
            "preview": before.preview
        } if before else None,
        "current": {
            "id": current.id,
            "header_path": current.header_path,
            "content": current.content,
            "preview": current.preview
        },
        "after": {
            "id": after.id,
            "header_path": after.header_path,
            "content": after.content,
            "preview": after.preview
        } if after else None
    }
