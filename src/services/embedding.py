"""
Embedding 服務模組
負責 SentenceTransformer 模型的載入、向量生成與 LRU 快取管理
"""

import asyncio
import threading
from functools import lru_cache
from typing import List, Optional, Union

from sentence_transformers import SentenceTransformer

from src.constants import VECTOR_DB_CONSTANTS
from src.models.vector import CacheStats
from src.utils.logger import Logger


class EmbeddingService:
    """
    向量 Embedding 服務（單例模式）

    職責：
    - SentenceTransformer 模型的延遲載入
    - 單一 / 批次向量生成
    - LRU 快取管理與統計
    """

    _instance: Optional['EmbeddingService'] = None
    _lock: threading.Lock = threading.Lock()
    _embedder: Optional[SentenceTransformer] = None
    _cache_stats: CacheStats = CacheStats()

    def __new__(cls) -> 'EmbeddingService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'EmbeddingService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_embedder(self) -> SentenceTransformer:
        """延遲載入 Embedding 模型，只在第一次需要時才載入"""
        if self._embedder is None:
            Logger.info("Embedding", f"載入 Embedding 模型: {VECTOR_DB_CONSTANTS.MODEL_NAME}")
            loop = asyncio.get_event_loop()
            self._embedder = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(VECTOR_DB_CONSTANTS.MODEL_NAME)
            )
            Logger.success("Embedding", "Embedding 模型載入完成")
        return self._embedder

    @lru_cache(maxsize=VECTOR_DB_CONSTANTS.CACHE_MAX_SIZE)
    def _embed_sync(self, text: str) -> tuple:
        """
        同步版本的單筆 Embedding（供 lru_cache 使用）

        Returns:
            向量的 tuple（hashable，可被 lru_cache 快取）
        """
        if self._embedder is None:
            raise RuntimeError("Embedder 尚未初始化，請先呼叫 get_embedder()")
        embedding = self._embedder.encode(text, convert_to_tensor=False)
        return tuple(embedding.tolist())

    async def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        建立向量嵌入，支援單筆或批次輸入。
        所有輸入皆經過 LRU 快取，避免重複計算。

        Args:
            text: 單一字串或字串列表

        Returns:
            單一向量 (List[float]) 或向量陣列 (List[List[float]])
        """
        await self.get_embedder()
        loop = asyncio.get_event_loop()

        if isinstance(text, str):
            return await self._embed_single(text, loop)
        else:
            return await self._embed_batch(text, loop)

    async def _embed_single(self, text: str, loop: asyncio.AbstractEventLoop) -> List[float]:
        """單筆 embedding，更新快取統計"""
        before = self._embed_sync.cache_info()
        result = await loop.run_in_executor(None, self._embed_sync, text)
        after = self._embed_sync.cache_info()

        if after.hits > before.hits:
            self._cache_stats.hits += 1
        else:
            self._cache_stats.misses += 1
        self._cache_stats.size = after.currsize
        self._cache_stats.max_size = after.maxsize

        return list(result)

    async def _embed_batch(self, texts: List[str], loop: asyncio.AbstractEventLoop) -> List[List[float]]:
        """批次 embedding：先查快取，未命中才送模型"""
        if not texts:
            return []

        results: List[List[float]] = []
        for t in texts:
            before = self._embed_sync.cache_info()
            embedding_tuple = await loop.run_in_executor(None, self._embed_sync, t)
            after = self._embed_sync.cache_info()

            if after.hits > before.hits:
                self._cache_stats.hits += 1
            else:
                self._cache_stats.misses += 1
            results.append(list(embedding_tuple))

        self._cache_stats.size = self._embed_sync.cache_info().currsize
        return results

    def get_cache_stats(self) -> CacheStats:
        """取得快取統計資訊"""
        return self._cache_stats

    def clear_cache(self) -> None:
        """清空 Embedding 快取"""
        self._embed_sync.cache_clear()
        self._cache_stats = CacheStats()
        Logger.info("Embedding", "Embedding 快取已清空")
