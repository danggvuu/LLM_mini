"""
Bước 2: Cắt nhỏ (Chunking) và gắn Metadata chi tiết cho từng Chunk
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indexing import build_chunks
from src.config import settings
import json

def run():
    print("=== BƯỚC 2: CHUNKING VÀ GẮN METADATA CHO TỪNG CHUNK ===")
    
    files = list(settings.data_dir.glob("*.*"))
    if not files:
        print("Không có file nào trong thư mục data!")
        return
    sample_file = files[2]
    
    # Gọi build_chunks (Nó sẽ dùng RecursiveCharacterTextSplitter)
    # Sau khi cắt, hàm này tạo một struct `ChunkMetadata` để định dạng metadata chuẩn cho từng chunk
    # Cụ thể: nó tạo `chunk_id` theo định dạng `doc_id:page:index`
    chunks = build_chunks([sample_file], notebook_id="demo_notebook")
    
    print(f"=> Từ file gốc đã chia thành {len(chunks)} chunks.")
    
    for i in range(min(5, len(chunks))):
        print(f"\n--- CHUNK THỨ {i+1} ---")
        print("Nội dung Toàn bộ Chunk:")
        print(chunks[i].page_content + "\n")
        print("Metadata chi tiết (chú ý chunk_id):")
        print(json.dumps(chunks[i].metadata, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run()
