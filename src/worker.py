"""
Background Worker — Tầng Xử lý Dữ liệu Bất đồng bộ
Uses FastAPI BackgroundTasks for async file processing.
Tracks task status for client polling.
"""
import time
import uuid
import logging
from typing import Dict, Optional, Literal
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

TaskStatus = Literal["pending", "processing", "done", "error"]


@dataclass
class TaskInfo:
    """Track the status of a background ingestion task."""
    task_id: str
    filename: str
    status: TaskStatus = "pending"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    chunks_indexed: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "chunks_indexed": self.chunks_indexed,
            "error_message": self.error_message,
        }


class TaskTracker:
    """In-memory tracker for background ingestion tasks."""

    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._last_cleanup = time.time()

    def create(self, filename: str) -> TaskInfo:
        # Passive Garbage Collection (mỗi tiếng 1 lần)
        if time.time() - self._last_cleanup > 3600:
            self.cleanup_old()
            self._last_cleanup = time.time()
            
        task_id = str(uuid.uuid4())[:8]
        task = TaskInfo(task_id=task_id, filename=filename)
        self._tasks[task_id] = task
        logger.info("Task created: %s for file %s", task_id, filename)
        return task

    def get(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)

    def list_all(self):
        return list(self._tasks.values())

    def cleanup_old(self, max_age_seconds: int = 3600) -> int:
        cutoff = time.time() - max_age_seconds
        old = [tid for tid, t in self._tasks.items()
               if t.completed_at and t.completed_at < cutoff]
        for tid in old:
            del self._tasks[tid]
        return len(old)


# Module-level singleton
_tracker: Optional[TaskTracker] = None


def get_task_tracker() -> TaskTracker:
    global _tracker
    if _tracker is None:
        _tracker = TaskTracker()
    return _tracker


def process_file_background(file_bytes: bytes, filename: str, notebook_id: str, task: TaskInfo, privacy: str = "public") -> None:
    """
    Background task function to process and ingest a file.
    Called by FastAPI BackgroundTasks.
    """
    from src.indexing import save_and_ingest_file
    from src.observability import record_task_start, record_task_end

    record_task_start()
    task.status = "processing"
    logger.info("Background processing started: %s (task %s)", filename, task.task_id)

    try:
        result = save_and_ingest_file(file_bytes, filename, notebook_id)
        
        from src.notebook_store import get_notebook_store
        get_notebook_store().add_document(notebook_id, result["filename"], result["chunks_indexed"], privacy=privacy)

        task.status = "done"
        task.filename = result["filename"]
        task.chunks_indexed = result["chunks_indexed"]
        task.completed_at = time.time()
        logger.info(
            "Background processing complete: %s — %d chunks (task %s)",
            filename, task.chunks_indexed, task.task_id,
        )
    except Exception as exc:
        task.status = "error"
        task.error_message = str(exc)
        task.completed_at = time.time()
        logger.error("Background processing failed: %s — %s (task %s)", filename, exc, task.task_id)
    finally:
        record_task_end()
