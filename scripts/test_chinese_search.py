#!/usr/bin/env python3
"""
測試 VectorStore 的中文語意搜尋品質
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.services.vector import VectorStore
from src.types.vector import VectorDoc
from rich.console import Console
from rich.table import Table

console = Console()


async def test_chinese_semantic_search():
    """測試中文語意搜尋"""
    
    console.print("\n[bold green]🧪 測試中文語意搜尋品質[/bold green]\n")
    
    store = VectorStore.get_instance()
    await store.initialize()
    
    # 準備測試資料
    test_docs = [
        VectorDoc(
            id="doc_login",
            content="使用者登入系統時，需要驗證帳號密碼。驗證成功後會產生 JWT Token。",
            parent_id="test",
            project_name="test",
            tags=["auth"],
            code_type="logic"
        ),
        VectorDoc(
            id="doc_register",
            content="新使用者註冊時，系統會檢查電子郵件是否已被使用，並建立新的使用者帳號。",
            parent_id="test",
            project_name="test",
            tags=["auth"],
            code_type="logic"
        ),
        VectorDoc(
            id="doc_payment",
            content="付款流程包含信用卡驗證、金額扣款與交易記錄。",
            parent_id="test",
            project_name="test",
            tags=["payment"],
            code_type="logic"
        ),
        VectorDoc(
            id="doc_search",
            content="搜尋功能使用全文檢索技術，支援關鍵字與語意搜尋。",
            parent_id="test",
            project_name="test",
            tags=["search"],
            code_type="feature"
        ),
    ]
    
    # 插入測試資料
    console.print("[cyan]正在插入測試資料...[/cyan]")
    for doc in test_docs:
        await store.upsert(doc)
    
    await asyncio.sleep(1)  # 等待寫入完成
    
    # 測試查詢
    test_queries = [
        ("怎麼登入？", "doc_login"),
        ("如何註冊新帳號？", "doc_register"),
        ("付費方式", "doc_payment"),
        ("找東西", "doc_search"),
    ]
    
    console.print("\n[bold cyan]測試結果：[/bold cyan]\n")
    
    results_table = Table(title="語意搜尋測試")
    results_table.add_column("查詢", style="yellow")
    results_table.add_column("期望結果", style="cyan")
    results_table.add_column("實際結果", style="green")
    results_table.add_column("狀態", style="bold")
    
    total = len(test_queries)
    correct = 0
    
    for query, expected_id in test_queries:
        results = await store.search(query, limit=1)
        
        if results and results[0].id == expected_id:
            status = "✅ 正確"
            correct += 1
            actual = results[0].id
        elif results:
            status = "❌ 錯誤"
            actual = results[0].id
        else:
            status = "❌ 無結果"
            actual = "None"
        
        results_table.add_row(query, expected_id, actual, status)
    
    console.print(results_table)
    
    # 顯示準確率
    accuracy = (correct / total) * 100
    console.print(
        f"\n[bold]準確率: {correct}/{total} ({accuracy:.1f}%)[/bold]"
    )
    
    if accuracy >= 75:
        console.print("[bold green]✓ 中文語意搜尋品質良好！[/bold green]")
    else:
        console.print("[bold yellow]⚠ 中文語意搜尋品質需要改進[/bold yellow]")
    
    # 清理測試資料
    console.print("\n[dim]清理測試資料...[/dim]")
    await store.delete_by_parent_id("test")
    
    # 顯示快取統計
    cache_stats = store.get_cache_stats()
    console.print(f"\n[dim]快取統計: 命中率 {cache_stats.hit_rate:.1%}[/dim]")


if __name__ == "__main__":
    asyncio.run(test_chinese_semantic_search())
