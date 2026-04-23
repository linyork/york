"""
向量資料庫服務模組
使用 LanceDB 提供向量儲存與語意搜尋功能

Embedding 生成與快取由 EmbeddingService 負責。
"""

import asyncio
import threading
from pathlib import Path
from typing import List, Optional, Union

import lancedb

from src.config import config
from src.constants import VECTOR_DB_CONSTANTS
from src.models.vector import VectorDoc, CacheStats, DatabaseStats
from src.services.embedding import EmbeddingService
from src.utils.logger import Logger
from src.utils.security import escape_sql_string, escape_sql_like


class VectorStore:
    """
    向量資料庫服務（單例模式）

    職責：DB 連線管理、CRUD、向量搜尋。
    Embedding 生成與快取委派給 EmbeddingService。
    """

    _instance: Optional['VectorStore'] = None
    _db: Optional[lancedb.DBConnection] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'VectorStore':
        """單例模式實作（thread-safe double-checked locking）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'VectorStore':
        """取得 VectorStore 單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def _embedder_service(self) -> EmbeddingService:
        """取得 EmbeddingService 單例（委派）"""
        return EmbeddingService.get_instance()
    
    async def initialize(self) -> None:
        """
        初始化資料庫連線
        確保資料庫目錄存在並建立連線
        """
        if self._db is not None:
            return  # 已初始化
        
        # 建立資料庫目錄（使用獨立本機路徑，不放在 Google Drive 上，避免 FUSE mmap deadlock）
        db_path = Path(config.vector_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        Logger.info("VectorStore", f"連接向量資料庫 (本機): {db_path}")
        
        # 建立 LanceDB 連線
        self._db = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: lancedb.connect(str(db_path))
        )
        
        Logger.success("VectorStore", "向量資料庫連線成功")
    
    async def get_table(self) -> Optional[lancedb.table.Table]:
        """
        取得資料表實例
        如果資料表不存在，返回 null
        
        Returns:
            資料表實例或 None
        """
        await self.initialize()
        
        try:
            table = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._db.open_table(VECTOR_DB_CONSTANTS.TABLE_NAME)
            )
            return table
        except Exception:
            # 資料表不存在
            return None
    
    async def create_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """委派至 EmbeddingService（向後相容介面）"""
        return await self._embedder_service.embed(text)

    def get_cache_stats(self) -> CacheStats:
        """取得快取統計資訊（委派至 EmbeddingService）"""
        return self._embedder_service.get_cache_stats()

    def clear_cache(self) -> None:
        """清空 Embedding 快取（委派至 EmbeddingService）"""
        self._embedder_service.clear_cache()

    async def upsert(self, doc: VectorDoc, retry_count: int = 0) -> None:
        """
        插入或更新向量文件
        
        Args:
            doc: 要插入的文件
            retry_count: 遞迴重試計數器（內部使用）
        """
        await self.upsert_batch([doc], retry_count)

    async def upsert_batch(self, docs: List[VectorDoc], retry_count: int = 0) -> None:
        """
        批次插入或更新向量文件

        Args:
            docs: 要插入的文件列表
            retry_count: 遞迴重試計數器（內部使用）
        """
        if not docs:
            return

        await self.initialize()
        
        # 找出需要建立向量嵌入的文件
        docs_to_embed = [doc for doc in docs if doc.vector is None]
        if docs_to_embed:
            contents = [doc.content for doc in docs_to_embed]
            embeddings = await self.create_embedding(contents)
            for doc, embedding in zip(docs_to_embed, embeddings):
                doc.vector = embedding
        
        # 準備資料
        # 使用 by_alias=True 確保輸出 camelCase 欄位名稱，與資料庫相容
        data_list = [doc.model_dump(by_alias=True) for doc in docs]

        # LanceDB 不接受 list 欄位為 None（PyArrow 無法推斷型別）→ 統一轉為空列表
        _LIST_FIELDS = ("tags", "relatedFiles")
        for item in data_list:
            for field in _LIST_FIELDS:
                if item.get(field) is None:
                    item[field] = []

        try:
            table = await self.get_table()

            if table is None:
                # 資料表不存在，建立新表
                Logger.info("VectorStore", f"建立新資料表: {VECTOR_DB_CONSTANTS.TABLE_NAME}")

                import pyarrow as pa

                schema = pa.schema([
                    pa.field("id",                 pa.string()),
                    pa.field("content",            pa.string()),
                    pa.field("parentId",           pa.string()),
                    pa.field("projectName",        pa.string()),
                    pa.field("tags",               pa.list_(pa.string())),
                    pa.field("vector",             pa.list_(pa.float32(), VECTOR_DB_CONSTANTS.VECTOR_DIMENSION)),
                    # Optional (nullable)
                    pa.field("framework",          pa.string()),
                    pa.field("frameworkLayer",     pa.string()),
                    pa.field("codeType",           pa.string()),
                    pa.field("symbolName",         pa.string()),
                    pa.field("headerPath",         pa.string()),
                    pa.field("preview",            pa.string()),
                    pa.field("relatedFiles",       pa.list_(pa.string())),
                    pa.field("contextDescription", pa.string()),
                    pa.field("contentHash",        pa.string()),
                ])

                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._db.create_table(
                        VECTOR_DB_CONSTANTS.TABLE_NAME,
                        data=data_list,
                        schema=schema
                    )
                )

                Logger.success("VectorStore", "資料表建立成功")
            else:
                # 資料表存在，新增資料
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: table.add(data_list)
                    )
                    Logger.debug("VectorStore", f"已批次插入 {len(docs)} 個文件")
                except Exception as schema_err:
                    err_msg = str(schema_err)
                    # 僅在確定是 schema 結構不符（欄位缺失/型別變更）時才 drop & recreate
                    # 避免因資料問題誤刪整個 table
                    is_schema_mismatch = any(kw in err_msg for kw in (
                        "not found in target schema",
                        "value_field",
                        "Schema mismatch",
                        "field does not exist",
                    ))
                    if is_schema_mismatch and retry_count == 0:
                        Logger.warning("VectorStore", f"Schema 結構不符，自動重建資料表: {schema_err}")
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self._db.drop_table(VECTOR_DB_CONSTANTS.TABLE_NAME)
                        )
                        await self.upsert_batch(docs, retry_count + 1)
                        return
                    raise  # 其他錯誤直接往上拋

        except Exception as e:
            if retry_count < VECTOR_DB_CONSTANTS.MAX_SCHEMA_RETRIES:
                Logger.warning("VectorStore", f"批次插入失敗，重試中... ({retry_count + 1}/{VECTOR_DB_CONSTANTS.MAX_SCHEMA_RETRIES})")
                await self.upsert_batch(docs, retry_count + 1)
            else:
                Logger.error("VectorStore", f"批次插入文件失敗: {e}")
                raise
    
    async def delete_by_parent_id(self, parent_id: str) -> None:
        """
        根據父文件 ID 刪除所有相關的向量文件
        用於清理整個檔案的所有 chunks
        
        Args:
            parent_id: 父文件 ID
        """
        table = await self.get_table()
        
        if table is None:
            Logger.warning("VectorStore", "資料表不存在，無法刪除")
            return
        
        safe_parent_id = escape_sql_string(parent_id)

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.delete(f"parentId = '{safe_parent_id}'")
        )
        
        Logger.debug("VectorStore", f"已刪除 parent_id={parent_id} 的所有文件")
    
    async def delete(self, doc_id: str) -> None:
        """
        根據 ID 刪除向量文件
        
        Args:
            doc_id: 文件 ID
        """
        table = await self.get_table()
        
        if table is None:
            Logger.warning("VectorStore", "資料表不存在，無法刪除")
            return
        
        safe_id = escape_sql_string(doc_id)

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.delete(f"id = '{safe_id}'")
        )
        
        Logger.debug("VectorStore", f"已刪除文件: {doc_id}")
    
    async def search(
        self,
        query: str,
        limit: int = VECTOR_DB_CONSTANTS.DEFAULT_SEARCH_LIMIT,
        filter_expr: Optional[str] = None
    ) -> List[VectorDoc]:
        """
        語意搜尋
        使用向量相似度找出最相關的文件
        
        Args:
            query: 搜尋查詢
            limit: 返回結果數量限制
            filter_expr: SQL 過濾條件（選填）
            
        Returns:
            搜尋結果列表
        """
        table = await self.get_table()
        
        if table is None:
            Logger.warning("VectorStore", "資料表不存在，返回空結果")
            return []
        
        # 建立查詢向量
        query_vector = await self.create_embedding(query)
        
        # 執行向量搜尋
        search_builder = table.search(query_vector).limit(limit)
        
        if filter_expr:
            search_builder = search_builder.where(filter_expr)
        
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: search_builder.to_list()
        )
        
        # 轉換為 VectorDoc（Table 欄位為 camelCase，Pydantic alias 自動對應）
        docs = []
        for row in results:
            docs.append(VectorDoc(**row))
        
        Logger.debug("VectorStore", f"向量搜尋找到 {len(docs)} 個結果")
        return docs
    
    async def query(
        self,
        filter_expr: str,
        limit: int = 100
    ) -> List[VectorDoc]:
        """
        結構化查詢（不使用向量）
        用於根據 Metadata（如 parentId）精確檢索
        
        Args:
            filter_expr: SQL 過濾條件（必填）
            limit: 返回結果數量限制
            
        Returns:
            查詢結果列表
        """
        table = await self.get_table()
        
        if table is None:
            Logger.warning("VectorStore", "資料表不存在，返回空結果")
            return []
        
        # 執行查詢
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.search().where(filter_expr).limit(limit).to_list()
        )
        
        # 轉換為 VectorDoc
        docs = []
        for row in results:
            docs.append(VectorDoc(**row))
        
        Logger.debug("VectorStore", f"結構化查詢找到 {len(docs)} 個結果")
        return docs
    
    async def full_text_search(
        self,
        queries: List[str],
        project_name: str,
        extra_filter: Optional[str] = None,
        limit: int = 10,
    ) -> List['VectorDoc']:
        """
        全文內容搜尋（LIKE 比對）

        在 chunk content 欄位中，對 queries 的任一項做 LIKE 比對。
        不依賴向量相似度，純字串命中，補足跨語言關鍵字落地。

        Args:
            queries:      搜尋關鍵字列表（任一命中即回傳）
            project_name: 專案名稱
            extra_filter: 額外的 SQL 過濾條件（如 framework filter）
            limit:        回傳上限

        Returns:
            命中的 VectorDoc 列表
        """
        table = await self.get_table()
        if table is None:
            Logger.warning("VectorStore", "資料表不存在，全文搜尋返回空結果")
            return []

        # 過濾掉空字串或過短的 query（< 2 字元），避免 LIKE '%a%' 命中過多
        valid_queries = [q.strip() for q in queries if len(q.strip()) >= 2]
        if not valid_queries:
            return []

        safe_project = escape_sql_string(project_name)

        # 建立 OR 條件：任一 query LIKE 命中即算
        like_conditions = [
            f"content LIKE '%{escape_sql_like(q)}%' ESCAPE '\\\\'"
            for q in valid_queries
        ]
        content_expr = " OR ".join(like_conditions)
        filter_expr = f"projectName = '{safe_project}' AND ({content_expr})"

        if extra_filter:
            filter_expr += f" AND ({extra_filter})"

        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: table.search().where(filter_expr).limit(limit).to_list()
            )
            docs = [VectorDoc(**row) for row in results]
            Logger.debug("VectorStore", f"全文搜尋找到 {len(docs)} 個結果")
            return docs
        except Exception as e:
            Logger.warning("VectorStore", f"全文搜尋失敗，略過: {e}")
            return []

    async def get_stats(self) -> DatabaseStats:
        """
        取得資料庫統計資訊
        
        Returns:
            資料庫統計資訊
        """
        table = await self.get_table()
        
        if table is None:
            return DatabaseStats(
                total_count=0,
                vector_dim=VECTOR_DB_CONSTANTS.VECTOR_DIMENSION,
                model_name=VECTOR_DB_CONSTANTS.MODEL_NAME,
                table_exists=False
            )
        
        # 取得總數
        count = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.count_rows()
        )
        
        return DatabaseStats(
            total_count=count,
            vector_dim=VECTOR_DB_CONSTANTS.VECTOR_DIMENSION,
            model_name=VECTOR_DB_CONSTANTS.MODEL_NAME,
            table_exists=True
        )
