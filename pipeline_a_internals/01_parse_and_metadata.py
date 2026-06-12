"""
Bước 1: Nạp file và trích xuất nội dung (Parse) + Gắn Metadata ban đầu
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indexing import _load_with_markitdown
from src.config import settings
import json

def run():
    print("=== BƯỚC 1: PARSE VÀ GẮN METADATA BƯỚC ĐẦU ===")
    
    sample_file = settings.data_dir / "first_page_only.pdf"
    print(f"Đang xử lý file: {sample_file.name} (Chỉ gồm 1 trang đầu tiên của PDF gốc)")
    
    # MarkItDown đọc file và trả về danh sách Document
    # Mỗi Document đại diện cho 1 trang hoặc 1 phần, kèm metadata cơ bản (document_id, filename, page)
    documents = _load_with_markitdown(sample_file)
    
    print(f"\n=> Đã trích xuất được {len(documents)} trang/phần.")
    
    print("\n--- CHI TIẾT TRANG ĐẦU TIÊN VÀ METADATA ---")
    for idx, doc in enumerate(documents):
        print(f"\n[Slide/Page {idx + 1}]")
        print(f"Nội dung thô:\n{doc.page_content.strip()}")
        print("\nMetadata gắn kèm:")
        print(json.dumps(doc.metadata, indent=2, ensure_ascii=False))
        print("-" * 50)

if __name__ == "__main__":
    run()
