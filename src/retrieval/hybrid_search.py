"""
Hybrid Search — Tầng Truy xuất Lai
Runs Semantic (Qdrant) and Keyword (BM25) searches in parallel,
then combines results using Reciprocal Rank Fusion (RRF).
"""
import logging
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from src.config import settings
from src.schemas import ChunkMetadata, RetrievedChunk
from src.store import get_vector_store, get_client
from src.filters import filters_to_qdrant
from src.bm25_index import get_bm25_index

logger = logging.getLogger(__name__)

# RRF constant (standard value from literature)
RRF_K = 60


def _semantic_search(
    query: str,
    k: int,
    filters: Optional[dict],
    collection_name: Optional[str],
) -> List[RetrievedChunk]:
    """Semantic vector search via Qdrant."""
    name = collection_name or settings.qdrant_collection

    if not get_client().collection_exists(name):
        return []

    hits = get_vector_store(collection_name).similarity_search_with_score(
        query=query,
        k=k,
        filter=filters_to_qdrant(filters),
    )

    return [
        RetrievedChunk(
            text=doc.page_content,
            score=float(score),
            metadata=ChunkMetadata(**doc.metadata),
        )
        for doc, score in hits
    ]


def _bm25_search(query: str, k: int, notebook_id: str) -> List[RetrievedChunk]:
    """Keyword search via BM25 index."""
    bm25_index = get_bm25_index(notebook_id)

    if bm25_index.is_empty:
        logger.debug("BM25 index is empty, skipping keyword search.")
        return []

    results = bm25_index.search(query, top_k=k)

    return [
        RetrievedChunk(
            text=doc.text,
            score=float(score),
            metadata=ChunkMetadata(**doc.metadata),
        )
        for doc, score in results
    ]


def _reciprocal_rank_fusion(
    semantic_results: List[RetrievedChunk],
    bm25_results: List[RetrievedChunk],
    k: int = RRF_K,
) -> List[RetrievedChunk]:
    """
    Combine results using Reciprocal Rank Fusion (RRF).
    RRF_score(d) = Σ 1 / (k + rank_i(d))

    Uses chunk_id as the dedup key.
    """
    # Track RRF scores and keep best chunk object per chunk_id
    rrf_scores = {}
    chunk_map = {}

    for rank, chunk in enumerate(semantic_results, start=1):
        cid = chunk.metadata.chunk_id
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        if cid not in chunk_map:
            chunk_map[cid] = chunk

    for rank, chunk in enumerate(bm25_results, start=1):
        cid = chunk.metadata.chunk_id
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        if cid not in chunk_map:
            chunk_map[cid] = chunk

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    fused = []
    for cid in sorted_ids:
        chunk = chunk_map[cid]
        fused.append(chunk.model_copy(update={"score": rrf_scores[cid]}))

    return fused


class HybridSearcher:
    """
    Hybrid Search: chạy song song 2 luồng (Semantic + Keyword),
    kết hợp kết quả bằng RRF.
    """

    def search(
        self,
        query: str,
        k: int = None,
        filters: Optional[dict] = None,
        collection_name: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Execute hybrid search.

        Args:
            query: Search query
            k: Total number of candidates to retrieve per source before fusion
            filters: Metadata filters (applied to semantic search only)
            collection_name: Qdrant collection name

        Returns:
            Fused and ranked list of chunks
        """
        search_k = k or settings.hybrid_initial_k

        notebook_id = filters.get("notebook_id", "default") if filters else "default"

        # Run both searches in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            semantic_future = executor.submit(
                _semantic_search, query, search_k, filters, collection_name
            )
            bm25_future = executor.submit(
                _bm25_search, query, settings.bm25_top_k, notebook_id
            )

            semantic_results = semantic_future.result()
            bm25_results = bm25_future.result()

        logger.info(
            "Hybrid search: %d semantic + %d BM25 results for '%s'",
            len(semantic_results), len(bm25_results), query[:60],
        )

        # Combine using RRF
        fused = _reciprocal_rank_fusion(semantic_results, bm25_results)

        return fused


# Module-level singleton
_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    global _searcher
    if _searcher is None:
        _searcher = HybridSearcher()
    return _searcher
