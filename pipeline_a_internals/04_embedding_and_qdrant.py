"""
Bước 4: Embedding và lưu vector vào Qdrant Database
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.indexing import build_chunks
from src.config import settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_huggingface import HuggingFaceEmbeddings
import torch
from pathlib import Path
import uuid

def run():
    print("=== BƯỚC 4: EMBEDDING VÀ QDRANT VECTOR DB ===")
    files = list(settings.data_dir.glob("*.*"))
    if not files: return
    sample_file = files[0]
    
    chunks = build_chunks([sample_file], notebook_id="demo_notebook")
    
    print("\n--- 1. KHỞI TẠO MÔ HÌNH EMBEDDING (HUGGINGFACE) ---")
    
    # Ở bản gốc, hàm get_embeddings() giấu logic này.
    # Ở đây ta viết rõ ra để thấy Model nào đang được tải:
    model_name = settings.embedding_model
    if settings.low_vram_mode:
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
    print(f"Đang tải mô hình từ HuggingFace: {model_name}")
    print(f"Chạy trên thiết bị: {settings.hf_device}")
    
    embedder = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={
            "device": settings.hf_device,
            "model_kwargs": {"torch_dtype": torch.float16}  # Giảm VRAM
        },
        encode_kwargs={"normalize_embeddings": True},       # Dùng Cosine Similarity
    )
    
    print("\n--- 1.5. THỰC HIỆN EMBEDDING TỪNG CHUNK ---")
    
    sample_text = chunks[0].page_content
    # Thực hiện chuyển đổi chữ thành số (Vector)
    vector = embedder.embed_query(sample_text)
    print(f"=> Văn bản đã được mã hóa thành Vector có số chiều là: {len(vector)}")
    print(f"=> 5 con số đầu tiên của Vector: {vector[:5]}...")
    
    print("\n--- 2. CHUẨN BỊ LƯU VÀO QDRANT (TÁCH BIỆT HOÀN TOÀN) ---")
    isolated_qdrant_dir = Path(__file__).parent / "isolated_storage" / "qdrant"
    isolated_qdrant_dir.mkdir(parents=True, exist_ok=True)
    
    client = QdrantClient(path=str(isolated_qdrant_dir))
    collection_name = "demo_collection"
    
    if not client.collection_exists(collection_name):
        dim = len(vector)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )
    
    # Qdrant yêu cầu ID phải là UUID. Hệ thống băm chunk_id thành UUID.
    chunk_meta = chunks[0].metadata
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_meta["chunk_id"]))
    print(f"Chunk ID gốc: {chunk_meta['chunk_id']}")
    print(f"Hash thành UUID cho Qdrant DB: {point_id}")
    
    print("\n--- 3. NẠP VÀO DATABASE VÀ ĐỌC TRỰC TIẾP TỪ DB ---")
    # Nạp tay thẳng vào client thay vì dùng Langchain để tránh đụng chạm config gốc
    points = []
    for c in chunks[:2]:
        p_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, c.metadata["chunk_id"]))
        p_vec = embedder.embed_query(c.page_content)
        # Langchain qdrant mặc định lưu nội dung text vào trường page_content trong payload
        payload = {"page_content": c.page_content, "metadata": c.metadata}
        points.append(qmodels.PointStruct(id=p_id, vector=p_vec, payload=payload))
        
    client.upsert(collection_name=collection_name, points=points)
    point = client.retrieve(
        collection_name=collection_name,
        ids=[point_id],
        with_payload=True,
        with_vectors=True
    )
    
    if point:
        p = point[0]
        print(f"\n[DỮ LIỆU ĐANG NẰM TRONG Ổ CỨNG / QDRANT]")
        print(f"Vector DB Point ID: {p.id}")
        print("\nPayload (Nó lưu toàn bộ Metadata và text vào payload):")
        import json
        print(json.dumps(p.payload, indent=2, ensure_ascii=False))
        print(f"\nVector (Nó lưu dãy số embedding, trích 3 chiều đầu): {p.vector[:3]}...")

if __name__ == "__main__":
    run()
