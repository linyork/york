#!/usr/bin/env python3
"""
向量資料庫檢測與管理工具 (Interactive CLI)
對齊 Friday inspect_db.ts 的功能與體驗
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional

# 將專案根目錄加入路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from src.services.vector import VectorStore
from src.models.vector import VectorDoc
from src.knowledge.sync import reindex_knowledge
from src.utils.project import list_projects
from src.constants import VECTOR_DB_CONSTANTS

console = Console()

async def get_store():
    store = VectorStore.get_instance()
    await store.initialize()
    return store

async def show_stats():
    store = await get_store()
    stats = await store.get_stats()
    
    console.print(Panel(f"""
    [bold cyan]📊 Database Statistics[/bold cyan]
    
    📁 Location:   [yellow]{store._db.uri if store._db else 'Unknown'}[/yellow]
    📄 Table:      [yellow]{VECTOR_DB_CONSTANTS.TABLE_NAME}[/yellow]
    🔢 Total Rows: [green]{stats.total_count}[/green]
    🧠 Model:      [blue]{stats.model_name}[/blue]
    📏 Dim:        [blue]{stats.vector_dim}[/blue]
    """, title="資料庫狀態"))

async def preview_data(limit: int = 10):
    store = await get_store()
    console.print(f"\n[bold]👀 前 {limit} 筆資料預覽[/bold]")
    
    tbl = await store.get_table()
    if not tbl:
        console.print("[red]資料表不存在[/red]")
        return

    # 改用 to_list 避免 pandas 依賴
    results = tbl.search().limit(limit).to_list()
    
    if not results:
        console.print("[yellow](資料表為空)[/yellow]")
        return

    for i, row in enumerate(results):
        doc = VectorDoc(**row)
        content_preview = doc.content[:80].replace('\n', ' ') + "..."
        console.print(f"\n[{i+1}] ID: [cyan]{doc.id}[/cyan]")
        console.print(f"    Parent: [yellow]{doc.parent_id}[/yellow]")
        console.print(f"    Path:   [blue]{doc.header_path or 'Root'}[/blue]")
        console.print(f"    Tags:   [magenta]{', '.join(doc.tags)}[/magenta]")
        console.print(f"    Content: {content_preview}")
    
    console.print("-" * 30)

async def find_by_filename():
    filename = Prompt.ask("\n🔍 輸入要搜尋的檔名 (例如 'auth.md')")
    if not filename: return
    
    store = await get_store()
    tbl = await store.get_table()
    if not tbl: return

    # 使用 LanceDB 的 SQL where 類似語法，或取出後過濾
    # 這裡取出較多資料後在 Python 過濾比較靈活
    results = tbl.search().limit(5000).to_list()
    
    matches = [r for r in results if filename.lower() in (r.get('parentId') or r.get('parent_id') or '').lower()]
    
    console.print(f"\nFound {len(matches)} chunks matching '{filename}':")
    for r in matches:
        doc = VectorDoc(**r)
        content_preview = doc.content[:50].replace('\n', ' ') + "..."
        console.print(f"  - [[blue]{doc.header_path or 'Root'}[/blue]] {content_preview}")

async def simulate_search():
    query = Prompt.ask("\n🧠 輸入搜尋查詢")
    if not query: return
    
    console.print(f"\n🔄 正在生成 embedding 並搜尋 '{query}'...")
    store = await get_store()
    
    start = time.time()
    docs = await store.search(query, limit=5)
    duration = (time.time() - start) * 1000
    
    console.print(f"\n✅ Found {len(docs)} matches in {duration:.2f}ms:\n")
    
    for i, doc in enumerate(docs):
        # 這裡的 score 沒有直接暴露在 VectorDoc 中，視實作而定
        # 我們只顯示內容
        console.print(f"[{i+1}] ID: [cyan]{doc.id}[/cyan]")
        console.print(f"    Path: [blue]{doc.header_path or 'Root'}[/blue]")
        console.print(f"    Content: {doc.content[:150].replace('\n', ' ')}...")
        console.print("")

async def perform_reindex():
    project_name = Prompt.ask("\n🏗️  輸入要重新索引的專案名稱 (例如 'repository_name')")
    if not project_name: return
    
    console.print(f"\n⏳ Starting re-index for '{project_name}'...")
    start = time.time()
    result = await reindex_knowledge(project_name)
    duration = time.time() - start
    
    if result['count'] > 0 or result['errors'] > 0:
        console.print(f"\n✅ Re-index Complete in {duration:.2f}s")
        console.print(f"   - Processed: {result['count']} files")
        console.print(f"   - Errors: {result['errors']}")
    else:
        console.print("\n[yellow]無處理項目或專案不存在[/yellow]")

async def rebuild_all_projects():
    confirm = Prompt.ask("\n⚠️  WARNING: 這將刪除所有向量資料並重建所有專案！\n    輸入 'YES' 確認")
    if confirm != 'YES':
        console.print("[red]操作已取消[/red]")
        return
        
    console.print("\n🗑️  刪除現有向量庫...")
    store = await get_store()
    
    # 強制刪除 Table (透過刪檔或 Drop)
    # 簡單起見，我們用 delete_by_parent_id 模擬清空，或者 drop table
    # 如果 VectorStore 有提供 drop table 最好，沒有的話我們需要實作
    # 目前僅能透過 delete_by_parent_id 刪除，比較慢。
    # 更好的方式是直接刪除目錄，但在 Docker 內且 process 正佔用可能會有問題。
    # 我們嘗試 drop table
    try:
        if store._db:
            await asyncio.to_thread(store._db.drop_table, VECTOR_DB_CONSTANTS.TABLE_NAME)
            console.print("✅ Table dropped.")
    except Exception as e:
        console.print(f"[yellow]Table drop failed (maybe not exist): {e}[/yellow]")

    console.print("\n📂 Scanning projects...")
    projects = await list_projects()
    
    # 過濾 ALLOWED_PROJECTS (這裡簡化，假設 list_projects 已經正確)
    # 若要過濾 process.env 需要從 os.environ 讀取
    import os
    allowed_env = os.environ.get("ALLOWED_PROJECTS", "")
    if allowed_env:
        allowed_list = [p.strip() for p in allowed_env.split(',') if p.strip()]
        projects = [p for p in projects if p in allowed_list]
        console.print(f"ℹ️  Filtering by ALLOWED_PROJECTS: {allowed_list}")

    console.print(f"Found {len(projects)} projects to re-index: {', '.join(projects)}\n")
    
    total_files = 0
    total_errors = 0
    start_time = time.time()
    
    for i, project in enumerate(projects):
        console.print(f"\n[{i+1}/{len(projects)}] 🏗️  Re-indexing: [cyan]{project}[/cyan]")
        try:
            result = await reindex_knowledge(project)
            console.print(f"   ✅ Processed: {result['count']} files, Errors: {result['errors']}")
            total_files += result['count']
            total_errors += result['errors']
        except Exception as e:
            console.print(f"   ❌ Failed: {e}")
            total_errors += 1
            
    duration = time.time() - start_time
    
    console.print("\n" + "="*50)
    console.print("🎉 Rebuild Complete!")
    console.print("="*50)
    console.print(f"⏱️  Total Time: {duration:.2f}s")
    console.print(f"📊 Projects: {len(projects)}")
    console.print(f"📄 Files: {total_files}")
    console.print(f"❌ Errors: {total_errors}")
    console.print("="*50)

def print_menu():
    print("\n🤖 York Vector DB Inspector")
    print("1. 📊 Show Stats")
    print("2. 👀 Preview Top 10 Rows")
    print("3. 🔍 Find Chunks by Filename")
    print("4. 🧠 Simulate Semantic Search")
    print("5. 🏗️  Re-index Single Project")
    print("6. 🔥 DELETE ALL & Rebuild All Projects")
    print("7. 🚪 Exit")

async def main():
    while True:
        print_menu()
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6", "7"])
        
        try:
            if choice == '1':
                await show_stats()
            elif choice == '2':
                await preview_data()
            elif choice == '3':
                await find_by_filename()
            elif choice == '4':
                await simulate_search()
            elif choice == '5':
                await perform_reindex()
            elif choice == '6':
                await rebuild_all_projects()
            elif choice == '7':
                console.print("再見！ 👋")
                break
        except Exception as e:
            console.print(f"[bold red]Error executing command:[/bold red] {e}")
            import traceback
            traceback.print_exc()
            
        # 暫停一下讓使用者看到結果
        if choice != '7':
            Prompt.ask("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n再見！")
