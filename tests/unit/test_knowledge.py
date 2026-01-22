"""
測試知識庫核心功能
"""

import pytest
import asyncio
from pathlib import Path

from src.knowledge.core import (
    save_knowledge,
    read_knowledge,
    list_knowledge,
    delete_knowledge
)
from src.knowledge.sync import sync_to_vector_store, reindex_knowledge
from src.knowledge.search import search_knowledge
from src.utils.splitter import split_markdown


@pytest.mark.asyncio
async def test_save_and_read_knowledge():
    """測試儲存與讀取知識文件"""
    
    # 儲存知識
    result = await save_knowledge(
        project_name="test_project",
        name="test_knowledge",
        content="# 測試知識\n\n這是一個測試文件。",
        tags=["test", "demo"]
    )
    
    assert result["name"] == "test_knowledge.md"
    assert result["project"] == "test_project"
    
    # 讀取知識
    knowledge_file = await read_knowledge("test_project", "test_knowledge")
    
    assert knowledge_file.name == "test_knowledge.md"
    assert "測試知識" in knowledge_file.content
    assert "test" in knowledge_file.metadata.tags
    
    # 清理
    await delete_knowledge("test_project", "test_knowledge")


@pytest.mark.asyncio
async def test_list_knowledge():
    """測試列出知識文件"""
    
    # 建立多個測試文件
    await save_knowledge(
        project_name="test_project",
        name="doc1",
        content="# 文件 1",
        tags=["tag1"]
    )
    
    await save_knowledge(
        project_name="test_project",
        name="doc2",
        content="# 文件 2",
        tags=["tag2"]
    )
    
    # 列出所有文件
    all_docs = await list_knowledge("test_project")
    assert len(all_docs) >= 2
    
    # 按標籤過濾
    tag1_docs = await list_knowledge("test_project", tag="tag1")
    assert len(tag1_docs) >= 1
    assert any(d["name"] == "doc1.md" for d in tag1_docs)
    
    # 清理
    await delete_knowledge("test_project", "doc1")
    await delete_knowledge("test_project", "doc2")


@pytest.mark.asyncio
async def test_markdown_splitter():
    """測試 Markdown 切分器"""
    
    content = """# 標題 1

這是第一段內容。
這是更多內容。

## 子標題 1.1

這是子段落的內容。
包含多行。

### 小標題 1.1.1

更深層的內容。

## 子標題 1.2

另一個段落。

# 標題 2

第二個主要段落。
"""
    
    chunks = split_markdown("test_parent", content)
    
    # 應該有多個 chunks
    assert len(chunks) > 0
    
    # 檢查 header_path
    for chunk in chunks:
        assert chunk.header_path is not None
        assert chunk.content is not None
        assert chunk.preview is not None
        assert len(chunk.preview) <= 203  # 200 字元 + "..."


@pytest.mark.asyncio
async def test_sync_to_vector_store():
    """測試同步到向量資料庫"""
    
    content = """# 登入功能

## 使用者驗證

使用 JWT Token 進行驗證。

## 密碼加密

使用 bcrypt 加密密碼。
"""
    
    # 先儲存知識
    await save_knowledge(
        project_name="test_project",
        name="login_feature",
        content=content,
        tags=["auth", "login"],
        metadata={"code_type": "feature"}
    )
    
    # 同步到向量資料庫
    await sync_to_vector_store(
        project_name="test_project",
        safe_name="login_feature.md",
        content=content,
        tags=["auth", "login"],
        metadata={"code_type": "feature"}
    )
    
    # 等待一下
    await asyncio.sleep(0.5)
    
    # 從向量資料庫搜尋
    from src.services.vector import VectorStore
    store = VectorStore.get_instance()
    results = await store.search("JWT 驗證", limit=5, filter_expr="projectName = 'test_project'")
    
    # 應該找到相關結果
    assert len(results) > 0
    
    # 清理
    await delete_knowledge("test_project", "login_feature")
    from src.knowledge.sync import delete_from_vector_store
    await delete_from_vector_store("test_project", "login_feature.md")


@pytest.mark.asyncio
async def test_search_knowledge():
    """測試知識搜尋"""
    
    # 建立測試文件
    await save_knowledge(
        project_name="test_project",
        name="payment_logic",
        content="""# 付款邏輯

## 信用卡驗證

驗證信用卡號碼的有效性。

## 扣款流程

呼叫第三方支付 API 進行扣款。
""",
        tags=["payment", "logic"],
        metadata={"code_type": "logic"}
    )
    
    # 同步到向量資料庫
    knowledge_file = await read_knowledge("test_project", "payment_logic")
    await sync_to_vector_store(
        project_name="test_project",
        safe_name=knowledge_file.safe_name,
        content=knowledge_file.content,
        tags=knowledge_file.metadata.tags,
        metadata={"code_type": "logic"}
    )
    
    await asyncio.sleep(0.5)
    
    # 搜尋
    results = await search_knowledge("test_project", "付款")
    
    # 應該找到結果
    assert len(results) > 0
    
    # 清理
    await delete_knowledge("test_project", "payment_logic")
    from src.knowledge.sync import delete_from_vector_store
    await delete_from_vector_store("test_project", "payment_logic.md")


@pytest.mark.asyncio
async def test_reindex_knowledge():
    """測試重建索引"""
    
    # 建立多個測試文件
    for i in range(3):
        await save_knowledge(
            project_name="test_project",
            name=f"reindex_test_{i}",
            content=f"# 測試文件 {i}\n\n內容 {i}",
            tags=["reindex"]
        )
    
    # 重建索引
    result = await reindex_knowledge("test_project")
    
    # 應該處理了至少 3 個文件
    assert result["count"] >= 3
    assert result["errors"] == 0
    
    # 清理
    for i in range(3):
        await delete_knowledge("test_project", f"reindex_test_{i}")
        from src.knowledge.sync import delete_from_vector_store
        await delete_from_vector_store("test_project", f"reindex_test_{i}.md")
