"""
知識庫搜尋模組
實作三路混合檢索 (Keyword + Vector Multi-Query + Full-Text Content) + RRF

搜尋架構：
┌─────────────────────────────────────────────────────────────────┐
│  query + query_variants (多語言版本)                             │
├──────────────┬──────────────────────────┬───────────────────────┤
│  A. 關鍵字   │  B. 向量語意 (multi-query) │  C. 全文內容搜尋      │
│  (檔案層級)  │  (chunk 層級，逐 variant)  │  (chunk 層級，LIKE)   │
│  filename,   │  多個 embedding 並發，      │  所有 variant 對       │
│  tags 比對   │  dedup 後彙整              │  content LIKE 比對    │
└──────┬───────┴────────────┬─────────────┴──────────┬────────────┘
       │                    └──── chunk-level 合併 ────┘
       │                                 │
       └──────────── RRF ────────────────┘
                         │
                    Stale 偵測
                         │
                    最終結果 (Top 10)
"""

import asyncio
import hashlib
from typing import List, Dict, Any, Optional

from src.services.vector import VectorStore
from src.utils.logger import Logger
from src.knowledge.core import list_knowledge, read_knowledge
from src.utils.security import escape_sql_string


# ── 資料類型 ─────────────────────────────────────────────────────────────────

class SearchResult:
    """搜尋結果"""
    __slots__ = ('name', 'preview', 'tags', 'score', 'verification_hints',
                 'content', 'context', 'stale')

    def __init__(
        self,
        name: str,
        preview: str,
        tags: List[str],
        score: float,
        verification_hints: List[str],
        content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stale: bool = False,
    ):
        self.name               = name
        self.preview            = preview
        self.tags               = tags
        self.score              = score
        self.verification_hints = verification_hints
        self.content            = content
        self.context            = context
        self.stale              = stale


# ── A. 關鍵字搜尋（檔案層級）────────────────────────────────────────────────

async def keyword_search(
    project_name: str,
    query: str,
    query_variants: Optional[List[str]] = None,
) -> List[SearchResult]:
    """
    關鍵字搜尋（強化多語版）

    在 filename、tags、code_type 比對 query + 所有 query_variants。
    任一 variant 命中即算，不重複計分。

    Returns:
        搜尋結果列表（檔案層級命中，content=None）
    """
    knowledge_list = await list_knowledge(project_name)

    all_queries = [query] + (query_variants or [])
    query_lowers = [q.lower() for q in all_queries if q.strip()]

    results = []

    for item in knowledge_list:
        score  = 0.0
        hints: List[str] = []

        item_name_lower = item['name'].lower()
        if any(ql in item_name_lower for ql in query_lowers):
            score += 5.0
            hints.append(f"檔案名稱: {item['name']}")

        for tag in item.get('tags', []):
            tag_lower = tag.lower()
            if any(ql in tag_lower for ql in query_lowers):
                score += 3.0
                hints.append(f"標籤: {tag}")

        code_type = item.get('code_type')
        if code_type:
            ct_lower = code_type.lower()
            if any(ql in ct_lower for ql in query_lowers):
                score += 2.0
                hints.append(f"類型: {code_type}")

        if score > 0:
            try:
                knowledge_file = await read_knowledge(project_name, item['name'])
                preview = knowledge_file.content[:200] + "..."
            except Exception as e:
                Logger.warning("Search", f"無法讀取預覽 {item['name']}: {e}")
                preview = item['name']

            results.append(SearchResult(
                name=item['name'],
                preview=preview,
                tags=item.get('tags', []),
                score=score,
                verification_hints=hints,
                content=None,   # 檔案層級，不帶 chunk
            ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:10]


# ── B. 向量語意搜尋（multi-query）──────────────────────────────────────────

async def vector_search(
    project_name: str,
    queries: List[str],
    options: Optional[Dict[str, str]] = None,
) -> List[SearchResult]:
    """
    向量語意搜尋（支援多語 query variants）

    對每個 query 獨立跑 embedding + 向量搜尋，
    以 chunk_id dedup 合併，保留首次出現的結果（最高相似度）。

    Returns:
        搜尋結果列表（chunk 層級，content = 完整 chunk 內容）
    """
    store = VectorStore.get_instance()
    await store.initialize()

    safe_project_name = escape_sql_string(project_name)
    filter_expr = f"projectName = '{safe_project_name}'"

    if options:
        if options.get('framework'):
            filter_expr += f" AND framework = '{escape_sql_string(options['framework'])}'"
        if options.get('frameworkLayer'):
            filter_expr += f" AND frameworkLayer = '{escape_sql_string(options['frameworkLayer'])}'"
        if options.get('codeType'):
            filter_expr += f" AND codeType = '{escape_sql_string(options['codeType'])}'"
        if options.get('symbolName'):
            filter_expr += f" AND symbolName = '{escape_sql_string(options['symbolName'])}'"

    # 每個 query variant 並發搜尋
    tasks = [
        store.search(query=q, limit=10, filter_expr=filter_expr)
        for q in queries
        if q.strip()
    ]
    all_doc_lists = await asyncio.gather(*tasks, return_exceptions=True)

    # Dedup：同一 chunk_id 只保留首次出現（相似度最高的那次）
    seen_ids: set = set()
    merged_docs = []
    for doc_list in all_doc_lists:
        if isinstance(doc_list, Exception):
            Logger.warning("Search", f"某 query variant 向量搜尋失敗: {doc_list}")
            continue
        for doc in doc_list:
            if doc.id not in seen_ids:
                seen_ids.add(doc.id)
                merged_docs.append(doc)

    results = []
    for doc in merged_docs:
        parent_id_parts = doc.parent_id.split(':')
        file_name = parent_id_parts[1] if len(parent_id_parts) > 1 else doc.parent_id

        results.append(SearchResult(
            name=file_name,
            preview=doc.preview or doc.content[:200],
            tags=doc.tags,
            score=0.5,
            verification_hints=[f"語意命中: {doc.header_path}"] if doc.header_path else [],
            content=doc.content,
            context={
                "chunk_id":     doc.id,
                "parent_id":    doc.parent_id,
                "header_path":  doc.header_path,
                "content_hash": doc.content_hash,
            },
        ))

    return results


# ── C. 全文內容搜尋（chunk 層級 LIKE）──────────────────────────────────────

async def fulltext_content_search(
    project_name: str,
    queries: List[str],
    options: Optional[Dict[str, str]] = None,
) -> List[SearchResult]:
    """
    全文內容搜尋（補足跨語言關鍵字命中）

    對 chunk content 做 LIKE '%keyword%' 比對，不依賴向量相似度。
    多語言 variant 任一命中即回傳，命中越多語言版本的 chunk 分數越高。

    Returns:
        搜尋結果列表（chunk 層級）
    """
    store = VectorStore.get_instance()
    await store.initialize()

    # 建立 metadata 過濾（與 vector_search 一致）
    extra_parts: List[str] = []
    if options:
        if options.get('framework'):
            extra_parts.append(
                f"framework = '{escape_sql_string(options['framework'])}'"
            )
        if options.get('frameworkLayer'):
            extra_parts.append(
                f"frameworkLayer = '{escape_sql_string(options['frameworkLayer'])}'"
            )
        if options.get('codeType'):
            extra_parts.append(
                f"codeType = '{escape_sql_string(options['codeType'])}'"
            )
    extra_filter = " AND ".join(extra_parts) if extra_parts else None

    valid_queries = [q.strip() for q in queries if len(q.strip()) >= 2]
    if not valid_queries:
        return []

    docs = await store.full_text_search(
        queries=valid_queries,
        project_name=project_name,
        extra_filter=extra_filter,
        limit=10,
    )

    results = []
    for doc in docs:
        parent_id_parts = doc.parent_id.split(':')
        file_name = parent_id_parts[1] if len(parent_id_parts) > 1 else doc.parent_id

        # 統計哪些 variants 命中
        hit_queries = [q for q in valid_queries if q.lower() in doc.content.lower()]
        if not hit_queries:
            continue

        lang_hint = f"全文命中 ({len(hit_queries)}/{len(valid_queries)} 語言變體): {', '.join(hit_queries[:2])}"
        hints = [lang_hint]
        if doc.header_path:
            hints.append(f"Section: {doc.header_path}")

        results.append(SearchResult(
            name=file_name,
            preview=doc.preview or doc.content[:200],
            tags=doc.tags,
            score=0.5,
            verification_hints=hints,
            content=doc.content,
            context={
                "chunk_id":      doc.id,
                "parent_id":     doc.parent_id,
                "header_path":   doc.header_path,
                "content_hash":  doc.content_hash,
                "fulltext_hits": len(hit_queries),
            },
        ))

    return results


# ── RRF 合併 ─────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    keyword_results: List[SearchResult],
    chunk_results: List[SearchResult],
    k: int = 60,
) -> List[SearchResult]:
    """
    Reciprocal Rank Fusion (RRF) — 三路合併版本

    chunk_results 為 vector_search + fulltext_content_search 的合併列表。
    同一 chunk_id 重複出現（語意 + 全文都命中）時，分數自然累加，排名提升。

    Key 設計：
    - chunk_results：key = "chunk:{chunk_id}"，chunk 獨立計分
    - keyword_results：key = "file:{file_name}"，檔案層級

    Bonus 規則：
    - chunk 所屬檔案也被 keyword 命中 → keyword RRF 分數 × 0.5 加到 chunk
    - 若某檔案只有 keyword 命中，保留檔案層級結果
    - 若某檔案有 chunk 結果，移除重複的檔案層級結果
    """
    scores:     Dict[str, float]      = {}
    result_map: Dict[str, SearchResult] = {}

    # Step 1：keyword 檔案層級分數（供 bonus 使用）
    kw_file_scores: Dict[str, float]      = {}
    kw_file_hints:  Dict[str, List[str]]  = {}

    for rank, result in enumerate(keyword_results, 1):
        rrf = 1.0 / (k + rank) * 2   # keyword 權重 x2
        kw_file_scores[result.name] = kw_file_scores.get(result.name, 0) + rrf
        kw_file_hints.setdefault(result.name, []).extend(result.verification_hints)

        key = f"file:{result.name}"
        scores[key]     = scores.get(key, 0) + rrf
        result_map[key] = result

    # Step 2：chunk 層級結果（來自向量 + 全文，均以 chunk_id 為 key）
    chunk_file_names: set = set()

    for rank, result in enumerate(chunk_results, 1):
        chunk_id = result.context.get("chunk_id") if result.context else None
        key      = f"chunk:{chunk_id}" if chunk_id else f"file:{result.name}"

        rrf      = 1.0 / (k + rank)
        kw_bonus = kw_file_scores.get(result.name, 0) * 0.5

        scores[key] = scores.get(key, 0) + rrf + kw_bonus
        chunk_file_names.add(result.name)

        if key not in result_map:
            result_map[key] = result
        else:
            # 同 chunk 被多路搜尋命中 → 累加分數，合併 hints
            result_map[key].verification_hints.extend(result.verification_hints)

        # 把 keyword hints 補進 chunk（讓 AI 知道也有關鍵字命中）
        if result.name in kw_file_hints:
            existing = set(result_map[key].verification_hints)
            for h in kw_file_hints[result.name]:
                if h not in existing:
                    result_map[key].verification_hints.append(h)

    # Step 3：移除已被 chunk 覆蓋的檔案層級 keyword 結果
    final_results = []
    for key, score in scores.items():
        result = result_map[key]
        if key.startswith("file:") and result.name in chunk_file_names:
            continue
        result.score = score
        final_results.append(result)

    final_results.sort(key=lambda x: x.score, reverse=True)
    return final_results


# ── 主搜尋入口 ────────────────────────────────────────────────────────────────

async def search_knowledge(
    project_name: str,
    query: str,
    options: Optional[Dict[str, str]] = None,
    query_variants: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    搜尋知識文件內容
    使用三路混合檢索 (Keyword + Vector Multi-Query + Full-Text Content) + RRF

    Args:
        project_name:    專案名稱
        query:           主要查詢（任何語言）
        options:         metadata 過濾（framework / frameworkLayer / codeType / symbolName）
        query_variants:  同義查詢的其他語言版本（由 AI 呼叫端提供）

    Returns:
        搜尋結果列表，每筆包含：
        - name / content / preview / tags / score / verificationHints / context / stale
    """
    all_queries = [query] + (query_variants or [])
    Logger.info("Search", f"搜尋知識: {project_name} - {query} (variants: {len(all_queries)-1})")

    # 三路並發
    keyword_task  = keyword_search(project_name, query, query_variants)
    vector_task   = vector_search(project_name, all_queries, options)
    fulltext_task = fulltext_content_search(project_name, all_queries, options)

    results = await asyncio.gather(keyword_task, vector_task, fulltext_task, return_exceptions=True)

    keyword_results:  List[SearchResult] = results[0] if not isinstance(results[0], Exception) else []
    vector_results:   List[SearchResult] = results[1] if not isinstance(results[1], Exception) else []
    fulltext_results: List[SearchResult] = results[2] if not isinstance(results[2], Exception) else []

    if isinstance(results[0], Exception):
        Logger.warning("Search", f"關鍵字搜尋失敗: {results[0]}")
    if isinstance(results[1], Exception):
        Logger.warning("Search", f"向量搜尋失敗: {results[1]}")
    if isinstance(results[2], Exception):
        Logger.warning("Search", f"全文搜尋失敗: {results[2]}")

    # chunk_results = 向量 + 全文合併（RRF 內部以 chunk_id dedup）
    chunk_results = vector_results + fulltext_results
    merged_results = reciprocal_rank_fusion(keyword_results, chunk_results)

    # ── Stale 偵測 ────────────────────────────────────────────────────────────
    stale_files:    set         = set()
    current_hashes: Dict[str, str] = {}

    for r in merged_results:
        if r.context and r.context.get("content_hash") and r.name not in current_hashes:
            try:
                kf = await read_knowledge(project_name, r.name)
                current_hashes[r.name] = hashlib.md5(kf.content.encode()).hexdigest()[:16]
            except Exception:
                current_hashes[r.name] = ""

    for r in merged_results:
        stored_hash = r.context.get("content_hash") if r.context else None
        if stored_hash and r.name in current_hashes:
            if stored_hash != current_hashes[r.name]:
                r.stale = True
                stale_files.add(r.name)

    if stale_files:
        Logger.warning("Search", f"偵測到 {len(stale_files)} 個 stale 文件: {', '.join(stale_files)}")

    Logger.debug(
        "Search",
        f"結果: keyword={len(keyword_results)} vector={len(vector_results)} "
        f"fulltext={len(fulltext_results)} → merged={len(merged_results)}"
    )

    return [
        {
            "name":              r.name,
            "content":           r.content,
            "preview":           r.preview,
            "tags":              r.tags,
            "score":             r.score,
            "verificationHints": r.verification_hints,
            "context":           r.context,
            "stale":             r.stale,
        }
        for r in merged_results[:10]
    ]


# ── Small-to-Big Retrieval ────────────────────────────────────────────────────

async def expand_context(
    chunk_id: str,
    parent_id: str,
) -> Dict[str, Any]:
    """
    擴展 Chunk 上下文
    取得前一個與後一個 Chunk 的內容
    """
    store = VectorStore.get_instance()
    await store.initialize()

    safe_parent_id = escape_sql_string(parent_id)
    chunks = await store.query(f"parentId = '{safe_parent_id}'", limit=100)

    if not chunks:
        return {"before": None, "current": None, "after": None}

    current_idx = next(
        (i for i, c in enumerate(chunks) if c.id == chunk_id), None
    )

    if current_idx is None:
        return {"before": None, "current": None, "after": None}

    def _fmt(c):
        return {
            "id":          c.id,
            "header_path": c.header_path,
            "content":     c.content,
            "preview":     c.preview,
        }

    before  = chunks[current_idx - 1] if current_idx > 0 else None
    current = chunks[current_idx]
    after   = chunks[current_idx + 1] if current_idx < len(chunks) - 1 else None

    return {
        "before":  _fmt(before)  if before  else None,
        "current": _fmt(current),
        "after":   _fmt(after)   if after   else None,
    }
