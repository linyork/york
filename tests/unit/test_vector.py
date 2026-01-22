"""
測試向量資料庫服務
"""

import pytest
import asyncio
from src.services.vector import VectorStore
from src.models.vector import VectorDoc
from src.constants import VECTOR_DB_CONSTANTS


@pytest.mark.asyncio
async def test_singleton_pattern():
    """測試單例模式"""
    store1 = VectorStore.get_instance()
    store2 = VectorStore.get_instance()
    
    assert store1 is store2, "VectorStore 應該是單例模式"


@pytest.mark.asyncio
async def test_initialize():
    """測試初始化"""
    store = VectorStore.get_instance()
    await store.initialize()
    
    assert store._db is not None, "資料庫連線應該已建立"


@pytest.mark.asyncio
async def test_embedder_loading():
    """測試 Embedding 模型載入"""
    store = VectorStore.get_instance()
    
    embedder = await store.get_embedder()
    
    assert embedder is not None, "Embedder 應該已載入"
    assert store._embedder is embedder, "應該使用相同的 Embedder 實例"


@pytest.mark.asyncio
async def test_create_embedding():
    """測試向量嵌入生成"""
    store = VectorStore.get_instance()
    
    text = "測試文字"
    embedding = await store.create_embedding(text)
    
    assert len(embedding) == VECTOR_DB_CONSTANTS.VECTOR_DIMENSION, \
        f"向量維度應該是 {VECTOR_DB_CONSTANTS.VECTOR_DIMENSION}"
    assert all(isinstance(x, float) for x in embedding), \
        "向量元素應該都是 float"


@pytest.mark.asyncio
async def test_embedding_cache():
    """測試 Embedding 快取機制"""
    store = VectorStore.get_instance()
    store.clear_cache()  # 清空快取
    
    text = "測試快取"
    
    # 第一次呼叫（應該會 miss）
    embedding1 = await store.create_embedding(text)
    
    # 第二次呼叫（應該會 hit）
    embedding2 = await store.create_embedding(text)
    
    # 第三次呼叫不同文字（應該會 miss）
    embedding3 = await store.create_embedding("另一個測試")
    
    stats = store.get_cache_stats()
    
    # 驗證結果
    assert embedding1 == embedding2, "相同文字應該產生相同的向量"
    assert len(embedding3) == VECTOR_DB_CONSTANTS.VECTOR_DIMENSION, "向量維度正確"
    
    # 應該有 1 次命中（第二次呼叫）和 2 次未命中（第一次和第三次）
    assert stats.hits >= 1, "應該至少有 1 次快取命中"
    assert stats.misses >= 2, "應該至少有 2 次快取未命中"
    assert stats.size >= 2, "快取中應該有至少 2 個項目"
    assert 0 < stats.hit_rate < 1, "快取命中率應該在 0 和 1 之間"


@pytest.mark.xfail(reason="LanceDB/PyArrow compatibility issue: DataType.value_field missing")
@pytest.mark.asyncio
async def test_upsert_and_search():
    """測試文件插入與搜尋"""
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 建立測試文件
    doc = VectorDoc(
        id="test_doc_1",
        content="這是一個測試文件，用於驗證向量搜尋功能。",
        parent_id="test_parent",
        project_name="test_project",
        tags=["test", "vector"],
        framework="Python",
        code_type="test"
    )
    
    # 插入文件
    await store.upsert(doc)
    
    # 等待一下確保寫入完成
    await asyncio.sleep(0.5)
    
    # 搜尋文件
    results = await store.search("測試文件", limit=5)
    
    # 驗證結果
    assert len(results) > 0, "應該找到至少一個結果"
    
    # 清理
    await store.delete("test_doc_1")


@pytest.mark.xfail(reason="LanceDB/PyArrow compatibility issue: DataType.value_field missing")
@pytest.mark.asyncio
async def test_query_by_filter():
    """測試結構化查詢"""
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 建立測試文件
    doc = VectorDoc(
        id="test_doc_2",
        content="結構化查詢測試文件",
        parent_id="test_parent_2",
        project_name="test_project",
        tags=["test"],
        framework="TypeScript"
    )
    
    # 插入文件
    await store.upsert(doc)
    
    # 等待一下
    await asyncio.sleep(0.5)
    
    # 使用過濾條件查詢
    results = await store.query(
        filter_expr="parent_id = 'test_parent_2'",
        limit=10
    )
    
    # 驗證結果
    assert len(results) > 0, "應該找到結果"
    assert all(r.parent_id == "test_parent_2" for r in results), \
        "所有結果的 parent_id 應該相符"
    
    # 清理
    await store.delete_by_parent_id("test_parent_2")


@pytest.mark.xfail(reason="LanceDB/PyArrow compatibility issue: DataType.value_field missing")
@pytest.mark.asyncio
async def test_delete_by_parent_id():
    """測試批次刪除"""
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 建立多個測試文件
    parent_id = "test_parent_batch"
    
    for i in range(3):
        doc = VectorDoc(
            id=f"test_doc_batch_{i}",
            content=f"批次測試文件 {i}",
            parent_id=parent_id,
            project_name="test_project",
            tags=["batch"]
        )
        await store.upsert(doc)
    
    # 等待一下
    await asyncio.sleep(0.5)
    
    # 驗證文件存在
    results_before = await store.query(f"parent_id = '{parent_id}'", limit=10)
    assert len(results_before) == 3, "應該有 3 個文件"
    
    # 批次刪除
    await store.delete_by_parent_id(parent_id)
    
    # 等待一下
    await asyncio.sleep(0.5)
    
    # 驗證已刪除
    results_after = await store.query(f"parent_id = '{parent_id}'", limit=10)
    assert len(results_after) == 0, "所有文件應該已被刪除"


@pytest.mark.asyncio
async def test_get_stats():
    """測試統計資訊"""
    store = VectorStore.get_instance()
    await store.initialize()
    
    stats = await store.get_stats()
    
    assert stats.table_exists in [True, False], "table_exists 應該是布林值"
    assert stats.model_name == VECTOR_DB_CONSTANTS.MODEL_NAME, \
        "模型名稱應該相符"
    assert stats.vector_dim == VECTOR_DB_CONSTANTS.VECTOR_DIMENSION, \
        "向量維度應該相符"
    assert stats.total_count >= 0, "文件總數應該 >= 0"


@pytest.mark.asyncio
async def test_cache_stats():
    """測試快取統計"""
    store = VectorStore.get_instance()
    store.clear_cache()
    
    # 產生一些快取
    await store.create_embedding("測試 1")
    await store.create_embedding("測試 2")
    await store.create_embedding("測試 1")  # 快取命中
    
    stats = store.get_cache_stats()
    
    assert stats.hits > 0, "應該有快取命中"
    assert stats.misses > 0, "應該有快取未命中"
    assert stats.size > 0, "快取大小應該 > 0"
    assert stats.hit_rate > 0, "快取命中率應該 > 0"
