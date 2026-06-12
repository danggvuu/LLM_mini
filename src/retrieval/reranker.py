"""
Cross-Encoder Reranker — Tầng Truy xuất
Uses BAAI/bge-reranker-v2-m3 to rerank retrieved chunks.
Lazy loads the model to avoid startup cost.
"""
import logging
from typing import List, Optional
from functools import lru_cache

from src.config import settings
from src.schemas import RetrievedChunk

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_cross_encoder():
    """Lazy-load the Cross-Encoder model."""
    from sentence_transformers import CrossEncoder
    import torch

    model_name = settings.reranker_model
    if settings.low_vram_mode:
        model_name = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        
    logger.info("Loading Cross-Encoder model: %s ...", model_name)
    try:
        model = CrossEncoder(
            model_name,
            device=settings.hf_device,
            model_kwargs={"torch_dtype": torch.float16}
        )
        logger.info("Cross-Encoder loaded successfully.")
        return model
    except Exception as exc:
        logger.error("Failed to load Cross-Encoder: %s", exc)
        return None


class CrossEncoderReranker:
    """
    Cross-Encoder Reranker.
    Nhận N chunks thô → tính điểm tương quan chéo → lọc sạch giữ lại top-K chunks.
    """

    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: int = None,
    ) -> List[RetrievedChunk]:
        """
        Rerank chunks using Cross-Encoder.

        Args:
            query: The user's question
            chunks: Raw retrieved chunks (typically 15)
            top_k: Number of top chunks to keep (typically 5)

        Returns:
            Reranked and filtered chunks
        """
        rerank_k = top_k or settings.hybrid_rerank_k

        if not chunks:
            return []

        # If fewer chunks than top_k, skip reranking
        if len(chunks) <= rerank_k:
            logger.debug("Fewer chunks (%d) than rerank_k (%d), skipping reranker.", len(chunks), rerank_k)
            return chunks

        model = _load_cross_encoder()
        if model is None:
            logger.warning("Cross-Encoder unavailable. Returning top chunks by original score.")
            return chunks[:rerank_k]

        # Compute cross-encoder scores
        pairs = [[query, chunk.text] for chunk in chunks]
        scores = model.predict(pairs)

        # Update scores and sort
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            scored_chunks.append(chunk.model_copy(update={"score": float(score)}))

        scored_chunks.sort(key=lambda c: c.score, reverse=True)

        reranked = scored_chunks[:rerank_k]
        logger.info(
            "Reranker: %d → %d chunks. Score range: [%.4f, %.4f]",
            len(chunks), len(reranked),
            reranked[-1].score if reranked else 0,
            reranked[0].score if reranked else 0,
        )

        return reranked


# Module-level singleton
_reranker: Optional[CrossEncoderReranker] = None


def get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker
