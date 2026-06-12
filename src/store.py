from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from src.config import settings

@lru_cache(maxsize=1)
def get_embeddings():
    import torch
    model_name = settings.embedding_model
    if settings.low_vram_mode:
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={
            "device": settings.hf_device,
            "model_kwargs": {"torch_dtype": torch.float16}
        },
        encode_kwargs={"normalize_embeddings": True},
    )

@lru_cache(maxsize=1)
def get_client():
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.storage_dir))

def get_vector_store(collection_name=None):
    name = collection_name or settings.qdrant_collection
    ensure_collection(collection_name=name)
    return QdrantVectorStore(
        client=get_client(),
        collection_name=name,
        embedding=get_embeddings(),
    )

INDEXED_PAYLOAD_FIELDS = {
    "metadata.notebook_id": qmodels.PayloadSchemaType.KEYWORD,
    "metadata.document_id": qmodels.PayloadSchemaType.KEYWORD,
    "metadata.filename": qmodels.PayloadSchemaType.KEYWORD,
    "metadata.page": qmodels.PayloadSchemaType.INTEGER,
}

def ensure_collection(recreate=False, collection_name=None):
    client = get_client()
    name = collection_name or settings.qdrant_collection
    exists = client.collection_exists(name)
    
    if exists and recreate:
        client.delete_collection(name)
        exists = False
        
    if not exists:
        dim = len(get_embeddings().embed_query("dimension probe"))
        client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )
        
    payload_schema = client.get_collection(name).payload_schema or {}
    for field, schema in INDEXED_PAYLOAD_FIELDS.items():
        if payload_schema.get(field) is None:
            client.create_payload_index(name, field_name=field, field_schema=schema)

def delete_notebook_vectors(notebook_id: str, collection_name=None):
    """Delete all vectors belonging to a specific notebook."""
    client = get_client()
    name = collection_name or settings.qdrant_collection
    if client.collection_exists(name):
        from qdrant_client.http import models
        client.delete(
            collection_name=name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.notebook_id",
                            match=models.MatchValue(value=notebook_id),
                        )
                    ]
                )
            ),
        )
