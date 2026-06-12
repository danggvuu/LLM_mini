"""
Bước 3: Tokenize và lưu vào Inverted Index (BM25) trên RAM
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indexing import build_chunks
from src.bm25_index import BM25Document, BM25Index
from pathlib import Path
from src.config import settings

def run():
    print("=== BƯỚC 3: TOKENIZING VÀ BM25 (TRÊN RAM) ===")
    
    files = list(settings.data_dir.glob("*.*"))
    if not files: return
    sample_file = files[0]
    
    chunks = build_chunks([sample_file], notebook_id="demo_notebook")
    
    # Tạo thư mục lưu trữ riêng cho bài test này, tách biệt hoàn toàn với dự án chính
    isolated_bm25_dir = Path(__file__).parent / "isolated_storage" / "bm25"
    isolated_bm25_dir.mkdir(parents=True, exist_ok=True)
    bm25_index = BM25Index(persist_dir=isolated_bm25_dir)
    
    print("\n--- 1. CÁCH HỆ THỐNG TOKENIZE TỪNG CHUNK ---")
    sample_chunk = chunks[0]
    # bm25_index._tokenize dùng Regex để tách từ và đưa về chữ thường
    tokens = bm25_index._tokenize(sample_chunk.page_content)
    print(f"Nội dung gốc: {sample_chunk.page_content[:150]}...")
    print(f"Tokens tạo ra: {tokens[:25]}...")
    
    print("\n--- 2. ĐƯA VÀO CẤU TRÚC INVERTED INDEX ---")
    # Wrap chunk vào struct BM25Document
    bm25_docs = [
        BM25Document(chunk_id=c.metadata["chunk_id"], text=c.page_content, metadata=c.metadata)
        for c in chunks
    ]
    bm25_index.build(bm25_docs)
    
    print(f"Kích thước Index trên RAM: {bm25_index.size} documents.")
    
    # Kiểm tra cấu trúc RAM của BM25
    # rank_bm25 lưu trữ Document Frequencies (df) và Term Frequencies
    print("\n--- 3. KIỂM TRA TRỰC TIẾP TRONG RAM BM25 ---")
    target_word = tokens[0] if tokens else "the"
    
    # self._bm25.nd là dictionary đếm xem một token xuất hiện trong bao nhiêu documents
    doc_freq = bm25_index._bm25.nd.get(target_word, 0)
    print(f"Hệ thống ghi nhận từ khóa '{target_word}' xuất hiện trong {doc_freq} chunks.")
    
    print("\n--- 4. LƯU XUỐNG DISK ĐỂ TRUY XUẤT LẦN SAU ---")
    bm25_index.save()
    print(f"File JSON và Pickle của BM25 đã được lưu tại: {isolated_bm25_dir}")

if __name__ == "__main__":
    run()
