"""
Notebook Store — Quản lý siêu dữ liệu (metadata) của các thẻ (Notebooks)
Lưu trữ phân mảnh theo từng tệp JSON để chống quá tải RAM và dùng FileLock chống Race Condition.
"""
import json
import time
import uuid
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from filelock import FileLock

from src.config import settings

logger = logging.getLogger(__name__)

class NotebookDocument(BaseModel):
    filename: str
    uploaded_at: float = Field(default_factory=time.time)
    chunks_indexed: int = 0
    privacy: Literal["public", "private"] = "public"

class Notebook(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    llm_provider: Literal["gemini", "hf_local", "vllm"] = "gemini"
    created_at: float = Field(default_factory=time.time)
    documents: List[NotebookDocument] = Field(default_factory=list)
    messages: List[dict] = Field(default_factory=list)
    learning_data: Dict[str, Dict[str, dict]] = Field(
        default_factory=lambda: {"quiz": {}, "flashcards": {}, "summary": {}}
    )

class NotebookStore:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (settings.storage_dir.parent / "notebooks")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy()

    def _migrate_legacy(self):
        """Chuyển đổi từ file notebooks.json cũ sang cấu trúc thư mục phân mảnh."""
        legacy_file = settings.storage_dir.parent / "notebooks.json"
        if legacy_file.exists():
            try:
                data = json.loads(legacy_file.read_text(encoding="utf-8"))
                for nb_data in data:
                    nb = Notebook(**nb_data)
                    self._save_notebook(nb)
                # Backup file cũ để an toàn
                legacy_file.rename(legacy_file.with_suffix(".json.bak"))
                logger.info("Migrated legacy notebooks.json successfully.")
            except Exception as e:
                logger.error("Failed to migrate legacy notebooks: %s", e)

    def _get_path(self, notebook_id: str) -> Path:
        return self.storage_dir / f"{notebook_id}.json"

    def _save_notebook(self, nb: Notebook):
        path = self._get_path(nb.id)
        lock_path = path.with_suffix(".lock")
        try:
            with FileLock(lock_path, timeout=5):
                path.write_text(json.dumps(nb.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save notebook %s: %s", nb.id, e)

    def list_notebooks(self) -> List[Notebook]:
        """Tải metadata (danh sách) các notebook. (Không dùng cache để đảm bảo dữ liệu mới nhất khi có nhiều worker)"""
        notebooks = []
        for path in self.storage_dir.glob("*.json"):
            lock_path = path.with_suffix(".lock")
            try:
                with FileLock(lock_path, timeout=5):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    notebooks.append(Notebook(**data))
            except Exception as e:
                logger.error("Failed to load notebook %s: %s", path, e)
        return sorted(notebooks, key=lambda x: x.created_at, reverse=True)

    def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        path = self._get_path(notebook_id)
        if not path.exists():
            return None
        lock_path = path.with_suffix(".lock")
        try:
            with FileLock(lock_path, timeout=5):
                data = json.loads(path.read_text(encoding="utf-8"))
                return Notebook(**data)
        except Exception as e:
            logger.error("Failed to get notebook %s: %s", notebook_id, e)
            return None

    def create_notebook(self, name: str, llm_provider: str = "gemini") -> Notebook:
        nb = Notebook(name=name, llm_provider=llm_provider)
        self._save_notebook(nb)
        logger.info("Created notebook: %s (%s) with provider=%s", name, nb.id, llm_provider)
        return nb

    def delete_notebook(self, notebook_id: str) -> bool:
        path = self._get_path(notebook_id)
        lock_path = path.with_suffix(".lock")
        if path.exists():
            try:
                with FileLock(lock_path, timeout=5):
                    path.unlink()
                # Thử xóa file lock
                if lock_path.exists():
                    lock_path.unlink()
                logger.info("Deleted notebook: %s", notebook_id)
                return True
            except Exception as e:
                logger.error("Failed to delete notebook %s: %s", notebook_id, e)
        return False

    def add_message(self, notebook_id: str, message: dict) -> bool:
        nb = self.get_notebook(notebook_id)
        if nb:
            nb.messages.append(message)
            self._save_notebook(nb)
            return True
        return False

    def clear_messages(self, notebook_id: str) -> bool:
        nb = self.get_notebook(notebook_id)
        if nb:
            nb.messages = []
            self._save_notebook(nb)
            return True
        return False

    def delete_document(self, notebook_id: str, filename: str) -> bool:
        nb = self.get_notebook(notebook_id)
        if nb:
            original_len = len(nb.documents)
            nb.documents = [doc for doc in nb.documents if doc.filename != filename]
            if len(nb.documents) < original_len:
                self._save_notebook(nb)
                return True
        return False

    def add_document(self, notebook_id: str, filename: str, chunks: int, privacy: str = "public"):
        nb = self.get_notebook(notebook_id)
        if nb:
            # Check if exists
            for doc in nb.documents:
                if doc.filename == filename:
                    doc.chunks_indexed += chunks
                    doc.uploaded_at = time.time()
                    doc.privacy = privacy
                    self._save_notebook(nb)
                    return
            nb.documents.append(NotebookDocument(filename=filename, chunks_indexed=chunks, privacy=privacy))
            self._save_notebook(nb)

    def update_provider(self, notebook_id: str, llm_provider: str) -> Optional["Notebook"]:
        nb = self.get_notebook(notebook_id)
        if nb:
            nb.llm_provider = llm_provider
            self._save_notebook(nb)
            logger.info("Updated notebook %s provider to %s", notebook_id, llm_provider)
            return nb
        return None

# Module-level singleton
_store: Optional[NotebookStore] = None

def get_notebook_store() -> NotebookStore:
    global _store
    if _store is None:
        _store = NotebookStore()
    return _store
