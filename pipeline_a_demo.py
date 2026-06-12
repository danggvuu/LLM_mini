import streamlit as st
import tempfile
import os
import time
from pathlib import Path
import hashlib

# Fix for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.indexing import _load_with_markitdown, _splitter, build_chunks
from src.config import settings

st.set_page_config(page_title="Pipeline A - Ingestion Demo", layout="wide")

st.title("📥 Pipeline A: Data Ingestion Demo")
st.markdown("Xem trực quan từng thành phần của quá trình xử lý dữ liệu: **Upload → Parse → Chunk → Embed**")

uploaded_file = st.file_uploader("Tải lên tài liệu (PDF, DOCX, PPTX, XLSX, CSV, HTML, MD, TXT, JPG, PNG)", type=["pdf", "docx", "pptx", "xlsx", "csv", "html", "md", "txt", "jpg", "jpeg", "png"])

if uploaded_file:
    with st.expander("📦 Step 0: Upload File", expanded=True):
        st.success(f"Đã tải lên: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
    with st.spinner("Đang chạy Step 1: Parse (MarkItDown/PyPDF)..."):
        # Save temp file
        tmp_path = Path(settings.data_dir) / f"demo_{uploaded_file.name}"
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(uploaded_file.getvalue())
            
        start_time = time.time()
        try:
            docs = _load_with_markitdown(tmp_path)
            parse_time = time.time() - start_time
            
            with st.expander(f"📄 Step 1: Parse Document - {parse_time:.2f}s", expanded=False):
                st.info(f"Đã trích xuất được {len(docs)} trang/phần.")
                if docs:
                    tabs1 = st.tabs([f"Page {i+1}" for i in range(len(docs))])
                    for i, tab in enumerate(tabs1):
                        with tab:
                            st.text_area("Nội dung thô (Markdown/Text)", docs[i].page_content, height=250, key=f"page_{i}")
                            st.json(docs[i].metadata)
        except Exception as e:
            st.error(f"Lỗi khi Parse: {e}")
            st.stop()
            
    with st.spinner("Đang chạy Step 2: Chunking (RecursiveCharacterTextSplitter)..."):
        start_time = time.time()
        
        # Dùng hàm build_chunks có sẵn
        chunks = build_chunks([tmp_path], notebook_id="demo_notebook")
            
        chunk_time = time.time() - start_time
        
        with st.expander(f"✂️ Step 2: Chunking - {chunk_time:.2f}s", expanded=True):
            st.info(f"Đã chia thành {len(chunks)} chunks (Chunk size: {settings.chunk_size}, Overlap: {settings.chunk_overlap}).")
            
            if chunks:
                # Show up to 50 chunks to avoid UI lag
                display_chunks = chunks[:50]
                if len(chunks) > 50:
                    st.warning(f"Chỉ hiển thị 50 chunks đầu tiên (trên tổng số {len(chunks)} chunks).")
                
                tabs2 = st.tabs([f"Chunk {i}" for i in range(len(display_chunks))])
                for i, tab in enumerate(tabs2):
                    with tab:
                        st.text_area("Chunk Content", display_chunks[i].page_content, height=200, key=f"chunk_{i}")
                        st.json(display_chunks[i].metadata)
                    
    with st.spinner("Đang chạy Step 3 & 4: Embedding & Indexing..."):
        start_time = time.time()
        # Mock embedding since we don't want to pollute real Qdrant or wait long
        # But we will show what embedding model is being used.
        time.sleep(1) 
        embed_time = time.time() - start_time
        
        with st.expander(f"🧠 Step 3 & 4: Embedding & Indexing (Simulation) - {embed_time:.2f}s", expanded=True):
            st.success(f"Khởi tạo Embedding Model: `{settings.embedding_model}`")
            st.info(f"Đã tạo Vector Embeddings (768/384 chiều) cho {len(chunks)} chunks và đẩy vào Qdrant Collection `{settings.qdrant_collection}`.")
            st.info(f"Đã trích xuất Keyword thô từ {len(chunks)} chunks và xây dựng RankBM25 Inverted Index trên RAM.")
            
    # Cleanup temp file
    try:
        os.remove(tmp_path)
    except:
        pass
