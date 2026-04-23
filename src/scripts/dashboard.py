"""
York Knowledge Dashboard
暗色系、俐落介面

Tabs:
  📄 知識文件   — 瀏覽所有 .md 檔案
  🔷 向量索引   — 查看 LanceDB chunks
  🔍 語意搜尋   — 向量相似度搜尋
  ⚙️  管理       — 重建索引 / 備份 / 重置 / 品質測試
"""

import asyncio
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge.sync import reindex_all_projects, reindex_knowledge
from src.services.vector import VectorStore
from src.utils.project import list_projects

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="York",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d1117;
    color: #c9d1d9;
}
[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #c9d1d9; }

.york-title { font-size:1.4rem; font-weight:600; color:#58a6ff; letter-spacing:.05em; margin-bottom:0; }
.york-sub   { font-size:.75rem; color:#484f58; margin-top:0; }

[data-testid="metric-container"] {
    background:#161b22; border:1px solid #21262d;
    border-radius:6px; padding:.6rem 1rem;
}
[data-testid="stMetricValue"] { color:#58a6ff !important; font-size:1.4rem; }
[data-testid="stMetricLabel"] { color:#8b949e !important; font-size:.72rem; }

[data-testid="stTabs"] button { color:#8b949e; font-size:.82rem; padding:.35rem .9rem; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#58a6ff; border-bottom:2px solid #58a6ff; }

[data-testid="stDataFrame"] { border:1px solid #21262d; border-radius:6px; }

details { background:#161b22 !important; border:1px solid #21262d !important; border-radius:6px !important; }
details summary { color:#c9d1d9 !important; font-size:.85rem; }

pre, code { background:#161b22 !important; color:#79c0ff !important; font-size:.8rem; }

[data-testid="stTextInput"] input {
    background:#161b22; border:1px solid #30363d;
    color:#c9d1d9; border-radius:6px;
}
[data-testid="stSelectbox"] div, [data-testid="stMultiSelect"] div {
    background:#161b22; border-color:#30363d;
}

.danger-zone {
    border:1px solid #da3633; border-radius:6px;
    padding:1rem 1.2rem; margin-top:1rem;
}

hr { border-color:#21262d; }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:#0d1117; }
::-webkit-scrollbar-thumb { background:#30363d; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@st.cache_resource
def get_store() -> VectorStore:
    return VectorStore.get_instance()


@st.cache_data(ttl=30)
def load_chunks() -> list[dict]:
    async def _load():
        store = get_store()
        await store.initialize()
        table = await store.get_table()
        if not table:
            return []
        return table.search().limit(10000).to_list()
    return run_async(_load())


def load_md_files() -> dict[str, list[dict]]:
    knowledge_root = Path("/knowledge")
    if not knowledge_root.exists():
        return {}
    result: dict[str, list[dict]] = {}
    for project_dir in sorted(knowledge_root.iterdir()):
        if not project_dir.is_dir():
            continue
        files = []
        for md_file in sorted(project_dir.glob("*.md")):
            try:
                content = md_file.read_text("utf-8")
                files.append({
                    "name": md_file.name,
                    "path": str(md_file),
                    "size": len(content),
                    "content": content,
                })
            except Exception:
                pass
        if files:
            result[project_dir.name] = files
    return result


def semantic_search(query: str, limit: int = 10):
    async def _search():
        store = get_store()
        await store.initialize()
        return await store.search(query, limit=limit)
    return run_async(_search())


def get_all_projects() -> list[str]:
    async def _list():
        return await list_projects()
    try:
        return run_async(_list())
    except Exception:
        return []

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="york-title">⬡ York</p>', unsafe_allow_html=True)
    st.markdown('<p class="york-sub">Knowledge Dashboard</p>', unsafe_allow_html=True)
    st.markdown("---")

    chunks   = load_chunks()
    md_files = load_md_files()

    total_chunks   = len(chunks)
    total_docs     = sum(len(v) for v in md_files.values())
    total_projects = len(md_files)

    c1, c2 = st.columns(2)
    c1.metric("Projects", total_projects)
    c2.metric("Docs",     total_docs)
    st.metric("Vector Chunks", total_chunks)

    st.markdown("---")

    all_projects     = sorted(md_files.keys())
    selected_project = st.selectbox("Project", ["All"] + all_projects)

    if st.button("↺  Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_docs, tab_vectors, tab_search, tab_ops = st.tabs([
    "📄  知識文件",
    "🔷  向量索引",
    "🔍  語意搜尋",
    "⚙️  管理",
])

# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — 知識文件
# ─────────────────────────────────────────────────────────────────────────────

with tab_docs:
    display_projects = (
        {selected_project: md_files[selected_project]}
        if selected_project != "All" and selected_project in md_files
        else md_files
    )
    if not display_projects:
        st.info("尚無知識文件。")
    else:
        for project, files in display_projects.items():
            st.markdown(f"#### {project}　`{len(files)} docs`")
            for f in files:
                label    = f["name"].replace(".md", "")
                size_kb  = f["size"] / 1024
                with st.expander(f"**{label}**　·　{size_kb:.1f} KB"):
                    st.markdown(f["content"])
            st.markdown("")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — 向量索引
# ─────────────────────────────────────────────────────────────────────────────

with tab_vectors:
    if not chunks:
        st.info("向量資料庫為空。")
    else:
        df = pd.DataFrame(chunks)
        for alias, canon in [("parentId","parent_id"),("projectName","project_name")]:
            if alias in df.columns and canon not in df.columns:
                df[canon] = df[alias]

        if selected_project != "All" and "project_name" in df.columns:
            df = df[df["project_name"] == selected_project]

        show_cols = [c for c in ["project_name","parent_id","headerPath","preview","tags"] if c in df.columns]

        selection = st.dataframe(
            df[show_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "project_name": st.column_config.TextColumn("Project",  width="small"),
                "parent_id":    st.column_config.TextColumn("File",     width="small"),
                "headerPath":   st.column_config.TextColumn("Section",  width="medium"),
                "preview":      st.column_config.TextColumn("Preview",  width="large"),
                "tags":         st.column_config.ListColumn("Tags",     width="small"),
            },
            selection_mode="single-row",
            on_select="rerun",
        )

        if selection and selection.selection.rows:
            idx = selection.selection.rows[0]
            row = df.iloc[idx]
            st.markdown("---")
            col_content, col_meta = st.columns([3, 1])
            with col_content:
                st.markdown(f"**{row.get('parent_id','')}**　›　`{row.get('headerPath','')}`")
                st.markdown(row.get("content", ""))
            with col_meta:
                meta = {k: v for k, v in row.items() if k not in ("content","vector") and v is not None}
                st.json(meta)

# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — 語意搜尋
# ─────────────────────────────────────────────────────────────────────────────

with tab_search:
    col_input, col_limit = st.columns([4, 1])
    with col_input:
        query = st.text_input("", placeholder="搜尋任何知識...", key="search_query")
    with col_limit:
        limit = st.selectbox("Top", [5, 10, 20], index=1, label_visibility="hidden")

    if query:
        with st.spinner(""):
            results = semantic_search(query, limit=limit)

        if not results:
            st.warning("找不到相關結果。")
        else:
            st.caption(f"{len(results)} 個結果")
            for doc in results:
                header = doc.header_path or doc.parent_id
                with st.expander(f"`{doc.project_name}`　{header}"):
                    st.markdown(doc.content)
                    tag_str = "　".join(f"`{t}`" for t in (doc.tags or []))
                    st.caption(tag_str)

# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — 管理
# ─────────────────────────────────────────────────────────────────────────────

with tab_ops:

    # ── 1. 重建索引 ────────────────────────────────────────────────────────────
    st.markdown("#### 重建向量索引")
    st.caption("重新掃描 .md 檔案並同步至 LanceDB。不影響原始知識文件。")

    projects_available = get_all_projects()

    col_proj, col_btn = st.columns([2, 1])
    with col_proj:
        reindex_target = st.selectbox(
            "目標專案", ["全部"] + projects_available, label_visibility="collapsed"
        )
    with col_btn:
        do_reindex = st.button("↺  重建索引", use_container_width=True)

    if do_reindex:
        with st.status("重建索引中...", expanded=True) as status:
            try:
                if reindex_target == "全部":
                    async def _reindex_all():
                        return await reindex_all_projects()
                    results = run_async(_reindex_all())
                    for proj, stat in results.items():
                        icon = "✅" if stat["errors"] == 0 else "⚠️"
                        st.write(f"{icon} **{proj}** — {stat['count']} 篇, {stat['errors']} 錯誤")
                    total = sum(s["count"] for s in results.values())
                    status.update(label=f"完成 — 共 {total} 篇文件", state="complete")
                else:
                    async def _reindex_one():
                        return await reindex_knowledge(reindex_target)
                    result = run_async(_reindex_one())
                    icon = "✅" if result["errors"] == 0 else "⚠️"
                    st.write(f"{icon} **{reindex_target}** — {result['count']} 篇, {result['errors']} 錯誤")
                    status.update(label=f"完成 — {result['count']} 篇文件", state="complete")
                st.cache_data.clear()
            except Exception as e:
                status.update(label=f"失敗：{e}", state="error")

    st.markdown("---")

    # ── 2. 備份資料庫 ──────────────────────────────────────────────────────────
    st.markdown("#### 備份向量資料庫")
    st.caption("將 LanceDB 打包成 .tar.gz 存到 `/knowledge/backups/`。")

    if st.button("📦  立即備份", use_container_width=False):
        lancedb_path = Path("/lancedb")
        backup_dir   = Path("/knowledge/backups")

        if not lancedb_path.exists():
            st.error("LanceDB 路徑不存在：/lancedb")
        else:
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
                ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"lancedb_{ts}.tar.gz"

                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(lancedb_path, arcname="lancedb")

                size_mb = backup_file.stat().st_size / 1024 / 1024
                st.success(f"備份完成：`{backup_file.name}`　({size_mb:.2f} MB)")

                # 列出現有備份
                backups = sorted(backup_dir.glob("lancedb_*.tar.gz"), reverse=True)
                if backups:
                    st.caption(f"共 {len(backups)} 份備份，最新：{backups[0].name}")
            except Exception as e:
                st.error(f"備份失敗：{e}")

    st.markdown("---")

    # ── 3. 語意搜尋品質測試 ────────────────────────────────────────────────────
    st.markdown("#### 語意搜尋品質測試")
    st.caption("寫入少量測試文件，驗證中文向量搜尋準確率，完成後自動清除測試資料。")

    TEST_CASES = [
        ("doc_login",    "使用者登入系統需要驗證帳號密碼，成功後產生 JWT Token。",         "怎麼登入？"),
        ("doc_register", "新使用者註冊時系統會檢查電子郵件是否重複，並建立新帳號。",       "如何新增帳號？"),
        ("doc_payment",  "付款流程包含信用卡驗證、金額扣款與交易記錄。",                   "付費方式"),
        ("doc_search",   "搜尋功能使用全文檢索技術，支援關鍵字與語意搜尋。",               "如何查詢資料？"),
    ]

    if st.button("▶  執行測試", use_container_width=False):
        from src.models.vector import VectorDoc as VDoc

        async def _run_quality_test():
            store = get_store()
            await store.initialize()

            # 寫入
            docs = [
                VDoc(id=doc_id, content=content, parent_id="__quality_test__",
                     project_name="__quality_test__", tags=["test"])
                for doc_id, content, _ in TEST_CASES
            ]
            await store.upsert_batch(docs)
            await asyncio.sleep(0.5)

            # 搜尋
            rows = []
            correct = 0
            for doc_id, _, query in TEST_CASES:
                results = await store.search(
                    query, limit=1,
                    filter_expr="projectName = '__quality_test__'"
                )
                hit = results[0].id == doc_id if results else False
                if hit:
                    correct += 1
                rows.append({
                    "查詢": query,
                    "期望": doc_id,
                    "結果": results[0].id if results else "—",
                    "✓": "✅" if hit else "❌",
                })

            # 清除
            await store.delete_by_parent_id("__quality_test__")

            return rows, correct

        with st.spinner("測試中..."):
            rows, correct = run_async(_run_quality_test())

        accuracy = correct / len(TEST_CASES) * 100
        result_df = pd.DataFrame(rows)
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        if accuracy >= 75:
            st.success(f"準確率 {correct}/{len(TEST_CASES)} ({accuracy:.0f}%)　語意搜尋品質良好")
        else:
            st.warning(f"準確率 {correct}/{len(TEST_CASES)} ({accuracy:.0f}%)　建議檢查 Embedding 模型")

        st.cache_data.clear()

    st.markdown("---")

    # ── 4. 重置資料庫（危險操作）─────────────────────────────────────────────
    st.markdown("#### 重置向量資料庫")
    st.caption("刪除整個 LanceDB table。原始 .md 知識文件不受影響，可重建索引還原。")

    st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
    confirm_reset = st.checkbox("我知道這會清空所有向量資料，需重建索引才能恢復搜尋功能")
    if st.button("🗑  重置資料庫", disabled=not confirm_reset, type="primary"):
        async def _reset():
            store = get_store()
            await store.initialize()
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: store._db.drop_table("knowledge_vectors")
                )
            except Exception:
                pass
        run_async(_reset())
        st.success("資料庫已重置。請到「重建向量索引」重新建立。")
        st.cache_data.clear()
    st.markdown("</div>", unsafe_allow_html=True)
