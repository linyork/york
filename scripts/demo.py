#!/usr/bin/env python3
"""
York 功能演示腳本
展示完整的知識管理流程
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.knowledge.core import save_knowledge, read_knowledge, list_knowledge
from src.knowledge.sync import sync_to_vector_store, reindex_knowledge
from src.knowledge.search import search_knowledge
from src.services.vector import VectorStore
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def demo():
    """完整功能演示"""
    
    console.print(Panel.fit(
        "[bold green]🚀 York 知識管理系統演示[/bold green]",
        border_style="green"
    ))
    
    project_name = "demo_project"
    
    # Step 1: 儲存知識文件
    console.print("\n[bold cyan]📝 Step 1: 儲存知識文件[/bold cyan]\n")
    
    knowledge_docs = [
        {
            "name": "user_authentication",
            "content": """# 使用者認證系統

## JWT Token 驗證

本系統使用 JWT (JSON Web Token) 進行使用者身份驗證。

### 登入流程

1. 使用者輸入帳號密碼
2. 後端驗證憑證
3. 產生 JWT Token
4. 前端儲存 Token 於 LocalStorage

### Token 刷新機制

當 Access Token 過期時，使用 Refresh Token 取得新的 Access Token。

## 密碼安全

使用 bcrypt 進行密碼雜湊處理，確保即使資料庫被竊取，攻擊者也無法還原原始密碼。
""",
            "tags": ["auth", "security", "jwt"],
            "framework": "Laravel",
            "code_type": "logic"
        },
        {
            "name": "payment_integration",
            "content": """# 付款整合

## 支援的付款方式

- 信用卡 (Visa, MasterCard, JCB)
- 網路 ATM
- 超商代碼

## 第三方支付 API

使用 ECPay（綠界科技）作為金流服務商。

### 付款流程

1. 建立訂單
2. 呼叫 ECPay API 取得付款網址
3. 導向使用者至付款頁面
4. 接收付款結果回呼
5. 更新訂單狀態

## 退款處理

支援部分退款與全額退款。退款需在 7 個工作天內處理完成。
""",
            "tags": ["payment", "integration", "ecpay"],
            "framework": "Laravel",
            "code_type": "feature"
        },
        {
            "name": "database_optimization",
            "content": """# 資料庫效能優化

## 索引策略

### 查詢最佳化

為常用的查詢欄位建立索引：
- users.email (unique index)
- orders.user_id + orders.created_at (composite index)
- products.category_id (index)

### 避免過度索引

索引會降低寫入效能，僅為頻繁查詢的欄位建立索引。

## 查詢快取

使用 Redis 快取熱門商品資料，減少資料庫查詢。

快取策略：
- TTL: 300 秒
- 當商品更新時，主動清除快取
""",
            "tags": ["database", "optimization", "performance"],
            "framework": "Laravel",
            "code_type": "guide"
        }
    ]
    
    for doc in knowledge_docs:
        result = await save_knowledge(
            project_name=project_name,
            name=doc["name"],
            content=doc["content"],
            tags=doc["tags"],
            metadata={
                "framework": doc.get("framework"),
                "code_type": doc.get("code_type")
            }
        )
        console.print(f"  ✅ 已儲存: [cyan]{result['name']}[/cyan]")
    
    # Step 2: 重建向量索引
    console.print("\n[bold cyan]🔄 Step 2: 同步至向量資料庫[/bold cyan]\n")
    
    result = await reindex_knowledge(project_name)
    console.print(f"  ✅ 成功同步 [green]{result['count']}[/green] 個文件")
    
    # Step 3: 列出所有知識文件
    console.print("\n[bold cyan]📚 Step 3: 列出知識文件[/bold cyan]\n")
    
    docs = await list_knowledge(project_name)
    
    table = Table(title=f"{project_name} 知識庫")
    table.add_column("檔案名稱", style="cyan")
    table.add_column("標籤", style="yellow")
    table.add_column("框架", style="green")
    table.add_column("類型", style="magenta")
    
    for doc in docs:
        table.add_row(
            doc["name"],
            ", ".join(doc.get("tags", [])),
            doc.get("framework") or "-",
            doc.get("code_type") or "-"
        )
    
    console.print(table)
    
    # Step 4: 測試搜尋功能
    console.print("\n[bold cyan]🔍 Step 4: 測試搜尋功能[/bold cyan]\n")
    
    test_queries = [
        "怎麼實作登入？",
        "付款方式",
        "資料庫效能"
    ]
    
    for query in test_queries:
        console.print(f"\n  查詢: [yellow]\"{query}\"[/yellow]")
        
        results = await search_knowledge(project_name, query)
        
        if results:
            console.print(f"  找到 [green]{len(results)}[/green] 個結果:")
            for i, r in enumerate(results[:3], 1):
                console.print(f"    {i}. [cyan]{r['name']}[/cyan] (分數: {r['score']:.3f})")
                console.print(f"       {r['preview'][:80]}...")
        else:
            console.print("  [red]未找到結果[/red]")
    
    # Step 5: 測試結構化過濾
    console.print("\n[bold cyan]🎯 Step 5: 結構化過濾搜尋[/bold cyan]\n")
    
    results = await search_knowledge(
        project_name=project_name,
        query="Laravel",
        options={"codeType": "logic"}
    )
    
    console.print(f"  查詢條件: framework=Laravel, code_type=logic")
    console.print(f"  找到 [green]{len(results)}[/green] 個結果")
    
    # Step 6: 向量資料庫統計
    console.print("\n[bold cyan]📊 Step 6: 向量資料庫統計[/bold cyan]\n")
    
    store = VectorStore.get_instance()
    stats = await store.get_stats()
    cache_stats = store.get_cache_stats()
    
    stats_table = Table(show_header=False)
    stats_table.add_row("資料表狀態", "✅ 存在" if stats.table_exists else "❌ 不存在")
    stats_table.add_row("文件總數", str(stats.total_count))
    stats_table.add_row("向量維度", str(stats.vector_dim))
    stats_table.add_row("Embedding 模型", stats.model_name)
    stats_table.add_row("快取命中率", f"{cache_stats.hit_rate:.1%}")
    stats_table.add_row("快取大小", f"{cache_stats.size}/{cache_stats.max_size}")
    
    console.print(stats_table)
    
    # Step 7: 清理
    console.print("\n[bold cyan]🧹 Step 7: 清理測試資料[/bold cyan]\n")
    
    from src.knowledge.core import delete_knowledge
    from src.knowledge.sync import delete_from_vector_store
    
    for doc in knowledge_docs:
        name = doc["name"]
        await delete_knowledge(project_name, name)
        await delete_from_vector_store(project_name, f"{name}.md")
        console.print(f"  ✅ 已刪除: [cyan]{name}[/cyan]")
    
    console.print("\n[bold green]🎉 演示完成！[/bold green]\n")


if __name__ == "__main__":
    asyncio.run(demo())
