import streamlit as st
import pandas as pd
import asyncio
import sys
from pathlib import Path

# 將專案根目錄加入路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.vector import VectorStore
from src.models.vector import VectorDoc

st.set_page_config(
    page_title="York Knowledge Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS Styling ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main-header {
        font-size: 2.5rem;
        color: #4B4B4B;
    }
    div.stButton > button:first-child {
        background-color: #0083B8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Cache & Utils ---

@st.cache_resource
def get_store():
    """取得 VectorStore 單例 (Cached)"""
    return VectorStore.get_instance()

def run_async(coro):
    """執行非同步函數"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def load_data():
    """載入所有資料"""
    store = VectorStore.get_instance()
    await store.initialize()
    table = await store.get_table()
    if not table:
        return []
    
    # 取出所有資料 (假設資料量還能接受，若太大需分頁)
    # Streamlit 的 dataframe 處理幾萬筆沒問題
    return table.search().limit(10000).to_list()

async def semantic_search_query(query, limit=10):
    store = VectorStore.get_instance()
    await store.initialize()
    return await store.search(query, limit=limit)

# --- Main App ---

st.title("🤖 York Knowledge Brain")
st.caption("AI Project Knowledge Manager - Visualization Dashboard")

# 1. 載入資料
with st.spinner("Loading Knowledge Base..."):
    raw_data = run_async(load_data())

if not raw_data:
    st.warning("Knowledge base is empty or database not initialized.")
    st.info("Try running `save_knowledge` tool first.")
    st.stop()

# 轉換為 DataFrame
df = pd.DataFrame(raw_data)

# 處理欄位別名 (相容舊資料)
if 'parentId' in df.columns:
    df['parent_id'] = df['parentId'].fillna(df.get('parent_id', ''))
if 'projectName' in df.columns:
    df['project_name'] = df['projectName'].fillna(df.get('project_name', ''))

# 確保必要欄位存在
required_cols = ['id', 'project_name', 'parent_id', 'content', 'tags']
for col in required_cols:
    if col not in df.columns:
        df[col] = ''

# --- Sidebar Filters ---

st.sidebar.header("🔍 Filters")

# Project Filter
projects = sorted(list(set(df['project_name'].dropna().astype(str))))
selected_project = st.sidebar.selectbox("Project", ["All"] + projects)

# Tag Filter (Global or Filtered)
if selected_project != "All":
    filtered_df = df[df['project_name'] == selected_project]
else:
    filtered_df = df

all_tags = set()
for tags_list in filtered_df['tags']:
    if isinstance(tags_list, list):
        all_tags.update(tags_list)
    elif isinstance(tags_list, str):
        # 處理可能的字串格式
        pass

selected_tags = st.sidebar.multiselect("Tags", sorted(list(all_tags)))

# Apply Filters
if selected_project != "All":
    df_display = df[df['project_name'] == selected_project]
else:
    df_display = df

if selected_tags:
    # 簡單的 tag 過濾：只要包含任一選定 tag 就顯示
    df_display = df_display[df_display['tags'].apply(lambda x: any(tag in x for tag in selected_tags) if isinstance(x, list) else False)]

st.sidebar.markdown("---")
st.sidebar.metric("Total Docs", len(df))
st.sidebar.metric("Filtered Docs", len(df_display))

# --- Tabs Interface ---

tab1, tab2 = st.tabs(["📚 Knowledge Explorer", "🧠 Semantic Search"])

with tab1:
    st.subheader(f"Knowledge Chunks ({len(df_display)})")
    
    # 顯示欄位選擇
    cols = ['project_name', 'parent_id', 'content', 'tags']
    
    # 使用 st.dataframe 的選取功能 (Streamlit 1.35+)
    selection = st.dataframe(
        df_display[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "content": st.column_config.TextColumn("Content Preview", width="medium"),
            "parent_id": st.column_config.TextColumn("File", width="small"),
            "tags": st.column_config.ListColumn("Tags"),
        },
        selection_mode="single-row",
        on_select="rerun" 
    )
    
    # 詳細視圖 (Selection Detail)
    # Streamlit 的 selection 回傳的是 rows index
    if selection and selection.selection.rows:
        selected_index = selection.selection.rows[0]
        # 注意：这里的 index 是 df_display 的 index，需要對應回去
        selected_row = df_display.iloc[selected_index]
        
        st.markdown("---")
        st.subheader(f"📄 Detail: {selected_row['parent_id']}")
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown("### Content")
            st.markdown(selected_row['content'])
            
        with c2:
            st.markdown("### Metadata")
            st.json(selected_row.to_dict())
            
            st.info(f"ID: {selected_row['id']}")

with tab2:
    st.subheader("Semantic Similarity Search")
    
    query = st.text_input("Ask York a question...", placeholder="e.g., How does the auth system work?")
    
    if query:
        with st.spinner("Searching vector space..."):
            results = run_async(semantic_search_query(query))
            
        st.success(f"Found {len(results)} relevant chunks.")
        
        for i, doc in enumerate(results):
            with st.expander(f"#{i+1} {doc.project_name} - {doc.parent_id} ({doc.score if hasattr(doc, 'score') else 'N/A'})"):
                st.markdown(f"**Path:** `{doc.header_path}`")
                st.markdown(doc.content)
                st.caption(f"Tags: {', '.join(doc.tags)}")

