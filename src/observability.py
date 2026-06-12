"""
Observability — Tầng Giám sát
Prometheus metrics + optional LangSmith tracing.
"""
import time
import logging
import os
from typing import Optional, Callable, Any
from functools import wraps

from src.config import settings

metrics_dir = settings.storage_dir / "metrics_mmap"
metrics_dir.mkdir(parents=True, exist_ok=True)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(metrics_dir)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

try:
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, multiprocess
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "rag_requests_total",
        "Total number of RAG requests",
        ["endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "rag_request_duration_seconds",
        "Request latency in seconds",
        ["endpoint"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    )
    CACHE_HIT = Counter(
        "rag_cache_hits_total",
        "Number of cache hits",
    )
    CACHE_MISS = Counter(
        "rag_cache_misses_total",
        "Number of cache misses",
    )
    ACTIVE_TASKS = Gauge(
        "rag_active_background_tasks",
        "Number of active background ingestion tasks",
    )
    CHUNKS_INDEXED = Counter(
        "rag_chunks_indexed_total",
        "Total chunks indexed",
    )
    FEEDBACK_COUNT = Counter(
        "rag_feedback_total",
        "User feedback thumbs up/down",
        ["feedback_type"],
    )
    # APP_INFO = Info(
    #     "rag_app",
    #     "Application metadata",
    # )
    # APP_INFO.info({
    #     "app_name": "Simple NotebookLM",
    #     "version": "2.0.0",
    #     "architecture": "Flowchart TB",
    # })


def record_request(endpoint: str, status: str = "success"):
    """Increment request counter."""
    if PROMETHEUS_AVAILABLE:
        REQUEST_COUNT.labels(endpoint=endpoint, status=status).inc()


def record_latency(endpoint: str, duration: float):
    """Record request latency."""
    if PROMETHEUS_AVAILABLE:
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)


def record_cache_hit():
    if PROMETHEUS_AVAILABLE:
        CACHE_HIT.inc()


def record_cache_miss():
    if PROMETHEUS_AVAILABLE:
        CACHE_MISS.inc()


def record_task_start():
    if PROMETHEUS_AVAILABLE:
        ACTIVE_TASKS.inc()


def record_task_end():
    if PROMETHEUS_AVAILABLE:
        ACTIVE_TASKS.dec()


def record_chunks_indexed(count: int):
    if PROMETHEUS_AVAILABLE:
        CHUNKS_INDEXED.inc(count)


def record_feedback(feedback_type: str):
    """Record thumbs up/down feedback. feedback_type: 'up' or 'down'."""
    if PROMETHEUS_AVAILABLE:
        FEEDBACK_COUNT.labels(feedback_type=feedback_type).inc()


def get_metrics_response():
    """Generate Prometheus metrics response."""
    if PROMETHEUS_AVAILABLE:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return b"# Prometheus not available\n", "text/plain"


def track_latency(endpoint: str):
    """Decorator to track endpoint latency and request count."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                record_request(endpoint, "success")
                return result
            except Exception as exc:
                record_request(endpoint, "error")
                raise
            finally:
                record_latency(endpoint, time.time() - start)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                record_request(endpoint, "success")
                return result
            except Exception as exc:
                record_request(endpoint, "error")
                raise
            finally:
                record_latency(endpoint, time.time() - start)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# ---------------------------------------------------------------------------
# LangSmith Tracing (Optional)
# ---------------------------------------------------------------------------

_langsmith_initialized = False


def init_langsmith():
    """Initialize LangSmith tracing if configured."""
    global _langsmith_initialized
    if _langsmith_initialized:
        return

    from src.config import settings
    if not settings.enable_langsmith:
        return

    if not settings.langsmith_api_key:
        logger.warning("LangSmith enabled but no API key configured.")
        return

    try:
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        _langsmith_initialized = True
        logger.info("LangSmith tracing initialized for project: %s", settings.langsmith_project)
    except Exception as exc:
        logger.warning("Failed to initialize LangSmith: %s", exc)
