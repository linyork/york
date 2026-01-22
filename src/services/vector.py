"""
向量資料庫服務模組
使用 LanceDB 與 SentenceTransformers 提供語意搜尋功能

功能特色：
- 多語言語意理解（支援中文）
- LRU 快取機制（減少重複計算）
- Small-to-Big 檢索策略
- 單例模式（Singleton Pattern）
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

import lancedb
from sentence_transformers import SentenceTransformer

from src.config import config
from src.constants import VECTOR_DB_CONSTANTS
from src.models.vector import VectorDoc, CacheStats, DatabaseStats
from src.utils.logger import Logger


class VectorStore:
    """
    向量資料庫服務（單例模式）
    
    技術堆疊：
    - LanceDB: 高效能向量資料庫
    - SentenceTransformers: 多語言 Embedding 模型
    - LRU 快取: 減少重複計算
    
    功能特色：
    - 支援多語言語意理解（中文優化）
    - Small-to-Big 檢索策略
    - 自動 Schema 管理
    - 智能快取機制
    """
    
    _instance: Optional['VectorStore'] = None
    _embedder: Optional[SentenceTransformer] = None
    _db: Optional[lancedb.DBConnection] = None
    _cache_stats: CacheStats = CacheStats()
    
    def __new__(cls):
        """單例模式實作"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'VectorStore':
        """取得 VectorStore 單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def get_embedder(self) -> SentenceTransformer:
        """
        延遲載入 Embedding 模型
        只在第一次需要時才載入，減少啟動時間
        
        Returns:
            Embedding 模型實例
        """
        if self._embedder is None:
            Logger.info("VectorStore", f"載入 Embedding 模型: {VECTOR_DB_CONSTANTS.MODEL_NAME}")
            
            # 使用 asyncio 執行緒池執行同步的模型載入
            loop = asyncio.get_event_loop()
            self._embedder = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(VECTOR_DB_CONSTANTS.MODEL_NAME)
            )
            
            Logger.success("VectorStore", "Embedding 模型載入完成")
        
        return self._embedder
    
    async def initialize(self) -> None:
        """
        初始化資料庫連線
        確保資料庫目錄存在並建立連線
        """
        if self._db is not None:
            return  # 已初始化
        
        # 建立資料庫目錄
        db_path = Path(config.knowledge_root) / VECTOR_DB_CONSTANTS.DB_DIR_NAME
        db_path.mkdir(parents=True, exist_ok=True)
        
        Logger.info("VectorStore", f"連接向量資料庫: {db_path}")
        
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
    
    @lru_cache(maxsize=VECTOR_DB_CONSTANTS.CACHE_MAX_SIZE)
    def _create_embedding_sync(self, text: str) -> tuple:
        """
        同步版本的 Embedding 生成（供 lru_cache 使用）
        
        Args:
            text: 要嵌入的文字
            
        Returns:
            向量嵌入的 tuple（可 hashable）
        """
        if self._embedder is None:
            raise RuntimeError("Embedder 尚未初始化，請先呼叫 get_embedder()")
        
        embedding = self._embedder.encode(text, convert_to_tensor=False)
        return tuple(embedding.tolist())
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        建立文字的向量嵌入
        使用 LRU 快取減少重複計算
        
        Args:
            text: 要嵌入的文字
            
        Returns:
            向量嵌入陣列
        """
        # 確保 Embedder 已載入
        await self.get_embedder()
        
        # 檢查快取（在呼叫前）
        cache_info_before = self._create_embedding_sync.cache_info()
        
        # 執行嵌入（會自動使用快取）
        loop = asyncio.get_event_loop()
        embedding_tuple = await loop.run_in_executor(
            None,
            self._create_embedding_sync,
            text
        )
        
        # 更新快取統計（檢查呼叫後的快取情況）
        cache_info_after = self._create_embedding_sync.cache_info()
        
        # 如果 hits 增加，代表這次呼叫命中快取
        if cache_info_after.hits > cache_info_before.hits:
            self._cache_stats.hits += 1
        else:
            self._cache_stats.misses += 1
        
        self._cache_stats.size = cache_info_after.currsize
        self._cache_stats.max_size = cache_info_after.maxsize
        
        return list(embedding_tuple)
    
    async def upsert(self, doc: VectorDoc, retry_count: int = 0) -> None:
        """
        插入或更新向量文件
        
        Args:
            doc: 要插入的文件
            retry_count: 遞迴重試計數器（內部使用）
        """
        await self.initialize()
        
        # 建立向量嵌入
        if doc.vector is None:
            doc.vector = await self.create_embedding(doc.content)
        
        # 準備資料
        # 使用 by_alias=True 確保輸出 camelCase 欄位名稱 (如 parentId)，與資料庫相容
        data = doc.model_dump(by_alias=True)
        
        try:
            table = await self.get_table()
            
            if table is None:
                # 資料表不存在，建立新表
                Logger.info("VectorStore", f"建立新資料表: {VECTOR_DB_CONSTANTS.TABLE_NAME}")
                
                # 定義 Schema 以避免自動推斷導致的 PyArrow/LanceDB 相容性問題
                import pyarrow as pa
                
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("parentId", pa.string()),
                    pa.field("projectName", pa.string()),
                    pa.field("tags", pa.list_(pa.string())),
                    pa.field("vector", pa.list_(pa.float32(), VECTOR_DB_CONSTANTS.VECTOR_DIMENSION)),
                    
                    # Optional fields (nullable)
                    pa.field("framework", pa.string()),
                    pa.field("frameworkLayer", pa.string()),
                    pa.field("codeType", pa.string()),
                    pa.field("symbolName", pa.string()),
                    pa.field("headerPath", pa.string()),
                    pa.field("preview", pa.string()),
                    pa.field("relatedFiles", pa.list_(pa.string())),
                    pa.field("contextDescription", pa.string()),
                ])

                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._db.create_table(
                        VECTOR_DB_CONSTANTS.TABLE_NAME,
                        data=[data],
                        schema=schema
                    )
                )
                
                Logger.success("VectorStore", "資料表建立成功")
            else:
                # 資料表存在，新增資料
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: table.add([data])
                )
                
                Logger.debug("VectorStore", f"文件已插入: {doc.id}")
        
        except Exception as e:
            if retry_count < VECTOR_DB_CONSTANTS.MAX_SCHEMA_RETRIES:
                Logger.warning("VectorStore", f"插入失敗，重試中... ({retry_count + 1}/{VECTOR_DB_CONSTANTS.MAX_SCHEMA_RETRIES})")
                await self.upsert(doc, retry_count + 1)
            else:
                Logger.error("VectorStore", f"插入文件失敗: {e}")
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
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.delete(f"parentId = '{parent_id}'")
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
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: table.delete(f"id = '{doc_id}'")
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
        
        # 轉換為 VectorDoc
        # 轉換為 VectorDoc
        docs = []
        for row in results:
            # 由於我們在 model 中設定了 alias 和 populate_by_name=True
            # 且 Table 中的欄位是 camelCase (如 parentId)
            # Pydantic 會自動將 parentId 對應到 parent_id
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
        # 轉換為 VectorDoc
        docs = []
        for row in results:
            docs.append(VectorDoc(**row))
        
        Logger.debug("VectorStore", f"結構化查詢找到 {len(docs)} 個結果")
        return docs
    
    def get_cache_stats(self) -> CacheStats:
        """
        取得快取統計資訊
        用於監控快取效能
        
        Returns:
            快取統計資訊
        """
        return self._cache_stats
    
    def clear_cache(self) -> None:
        """清空 Embedding 快取"""
        self._create_embedding_sync.cache_clear()
        self._cache_stats = CacheStats()
        Logger.info("VectorStore", "Embedding 快取已清空")
    
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
