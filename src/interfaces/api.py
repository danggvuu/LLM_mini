"""
FastAPI Backend — Tầng Giao diện & Định tuyến API
Hỗ trợ Server-Sent Events (SSE), async upload, session management,
feedback, và Prometheus metrics.
"""
import json
import logging

from fastapi import FastAPI, File, UploadFile, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import List, Optional

from src.config import settings
from src.schemas import RagAnswer, Summary, QuizSet, FlashcardSet
from src.filters import MetadataFilter, filters_to_dict
from src.indexing import save_and_ingest_file
from src.rag import answer, answer_stream
from src.learning import summarize as summarize_learning, generate_quiz, generate_flashcards
from src.store import get_client
from src.worker import get_task_tracker, process_file_background, TaskInfo
from src.session import get_session_store
from src.notebook_store import get_notebook_store
from src.observability import (
    track_latency, record_feedback, get_metrics_response, init_langsmith,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Learning API",
    description="Grounded Q&A, summaries, quizzes, and flashcards over indexed documents. "
                "Supports SSE streaming, async upload, session management, and observability.",
    version="2.0.0",
)


@app.on_event("startup")
async def startup():
    """Initialize observability and preload models on startup."""
    init_langsmith()
    logger.info("Preloading models into memory (Eager Loading)...")
    try:
        from src.store import get_embeddings
        from src.llm import get_llm
        from src.retrieval.reranker import _load_cross_encoder
        get_embeddings()
        get_llm()
        _load_cross_encoder()
        logger.info("Models preloaded successfully.")
    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
    logger.info("RAG API v2.0.0 started.")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: Optional[int] = Field(default=None, ge=1, le=64)
    filters: Optional[MetadataFilter] = None
    session_id: Optional[str] = None

class SummarizeRequest(BaseModel):
    document: Optional[str] = None
    query: Optional[str] = None
    filters: Optional[MetadataFilter] = None
    k: Optional[int] = Field(default=None, ge=1, le=64)

class QuizRequest(BaseModel):
    document: Optional[str] = None
    query: Optional[str] = None
    filters: Optional[MetadataFilter] = None
    count: Optional[int] = Field(default=None, ge=1, le=50)
    k: Optional[int] = Field(default=None, ge=1, le=64)

class FlashcardsRequest(QuizRequest):
    pass

class UploadResponse(BaseModel):
    task_id: str
    filename: str
    status: str

class TaskStatusResponse(BaseModel):
    task_id: str
    filename: str
    status: str
    chunks_indexed: int = 0
    error_message: Optional[str] = None

class FeedbackRequest(BaseModel):
    question: str
    feedback_type: str = Field(pattern="^(up|down)$")
    session_id: Optional[str] = None

class DocumentInfo(BaseModel):
    filename: str
    document_id: str
    num_pages: int
    num_chunks: int

class NotebookCreateRequest(BaseModel):
    name: str
    llm_provider: str = "gemini"

class AddNotebookMessageRequest(BaseModel):
    role: str
    content: str
    citations: Optional[List[dict]] = None


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def list_documents() -> List[DocumentInfo]:
    client = get_client()
    collection_name = settings.qdrant_collection
    if not client.collection_exists(collection_name):
        return []

    offset = None
    docs = {}
    while True:
        res, next_offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        for point in res:
            meta = point.payload.get("metadata") or {}
            doc_id = meta.get("document_id")
            filename = meta.get("filename")
            page = meta.get("page")

            if doc_id and filename:
                if doc_id not in docs:
                    docs[doc_id] = {
                        "filename": filename,
                        "document_id": doc_id,
                        "pages": set(),
                        "chunks_count": 0
                    }
                docs[doc_id]["pages"].add(page)
                docs[doc_id]["chunks_count"] += 1

        if next_offset is None or not res:
            break
        offset = next_offset

    return [
        DocumentInfo(
            filename=info["filename"],
            document_id=doc_id,
            num_pages=len(info["pages"]),
            num_chunks=info["chunks_count"]
        )
        for doc_id, info in docs.items()
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/notebooks")
def list_notebooks():
    return get_notebook_store().list_notebooks()

@app.get("/notebooks/{notebook_id}")
def get_notebook(notebook_id: str):
    nb = get_notebook_store().get_notebook(notebook_id)
    if not nb:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
    return nb

@app.post("/notebooks")
def create_notebook(req: NotebookCreateRequest):
    return get_notebook_store().create_notebook(req.name, llm_provider=req.llm_provider)

@app.delete("/notebooks/{notebook_id}")
def delete_notebook(notebook_id: str):
    success = get_notebook_store().delete_notebook(notebook_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
        
    # Xóa sạch vector rác trong Qdrant
    from src.store import delete_notebook_vectors
    try:
        delete_notebook_vectors(notebook_id)
    except Exception as e:
        logger.error(f"Error deleting vectors for {notebook_id}: {e}")
        
    # Xóa sạch thư mục BM25
    from src.bm25_index import delete_bm25_folder
    try:
        delete_bm25_folder(notebook_id)
    except Exception as e:
        logger.error(f"Error deleting bm25 for {notebook_id}: {e}")
        
    return {"status": "deleted"}

class UpdateProviderRequest(BaseModel):
    llm_provider: str

@app.post("/notebooks/{notebook_id}/provider")
def update_notebook_provider(notebook_id: str, req: UpdateProviderRequest):
    """Switch the LLM backend for an existing notebook."""
    nb = get_notebook_store().update_provider(notebook_id, req.llm_provider)
    if not nb:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
    return {"id": nb.id, "llm_provider": nb.llm_provider}

@app.get("/notebooks/{notebook_id}/documents")
@track_latency("documents")
def get_notebook_documents(notebook_id: str):
    nb = get_notebook_store().get_notebook(notebook_id)
    if not nb:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
    return nb.documents

@app.delete("/notebooks/{notebook_id}/documents/{filename}")
def delete_notebook_document(notebook_id: str, filename: str):
    """Xóa một tài liệu cụ thể khỏi notebook (cả metadata và qdrant vector)"""
    success = get_notebook_store().delete_document(notebook_id, filename)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
        
    # Xóa vector rác khỏi Qdrant nếu có
    from src.store import get_client
    from src.config import settings
    from qdrant_client.http import models
    client = get_client()
    try:
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename",
                        match=models.MatchValue(value=filename)
                    ),
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=notebook_id)
                    )
                ]
            )
        )
    except Exception as e:
        logger.error(f"Error deleting vectors for doc {filename} in {notebook_id}: {e}")
        
    # Ghi chú: Xóa khỏi BM25 hơi phức tạp vì nó dính vào file pickle,
    # tạm thời chỉ gỡ khỏi RAM và NotebookStore là đủ cho cá nhân (khi load lại BM25 sẽ bỏ qua doc này nếu muốn code kỹ hơn, 
    # nhưng hiện tại BM25 sẽ được build lại nếu ta làm thêm chức năng đó).
    return {"status": "deleted"}

@app.post("/notebooks/{notebook_id}/messages")
def add_notebook_message(notebook_id: str, req: AddNotebookMessageRequest):
    success = get_notebook_store().add_message(notebook_id, req.model_dump())
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
    return {"status": "ok"}

@app.delete("/notebooks/{notebook_id}/messages")
def clear_notebook_messages(notebook_id: str):
    success = get_notebook_store().clear_messages(notebook_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Notebook not found"})
    return {"status": "cleared"}

# --- Upload (Async with Background Worker) ---

@app.post("/upload/{notebook_id}", response_model=UploadResponse)
async def upload(notebook_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), privacy: str = "public"):
    """
    Upload a file and process it asynchronously.
    Returns immediately with a task_id for status polling.
    privacy: 'public' or 'private' — used to warn user if notebook uses cloud LLM.
    """
    # Warn if private data is being sent to a cloud LLM
    nb = get_notebook_store().get_notebook(notebook_id)
    if nb and nb.llm_provider == "gemini" and privacy == "private":
        logger.warning(
            "PRIVACY WARNING: Private document '%s' uploaded to notebook using Gemini API (cloud). "
            "Data will be sent to Google servers.", file.filename
        )

    content = await file.read()
    filename = file.filename or "unknown"

    tracker = get_task_tracker()
    task = tracker.create(filename)

    # Schedule background processing
    background_tasks.add_task(process_file_background, content, filename, notebook_id, task, privacy)

    return UploadResponse(
        task_id=task.task_id,
        filename=filename,
        status="pending",
    )


@app.get("/upload/status/{task_id}", response_model=TaskStatusResponse)
def upload_status(task_id: str):
    """Check the status of a background upload task."""
    tracker = get_task_tracker()
    task = tracker.get(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"detail": f"Task {task_id} not found."})
    return TaskStatusResponse(
        task_id=task.task_id,
        filename=task.filename,
        status=task.status,
        chunks_indexed=task.chunks_indexed,
        error_message=task.error_message,
    )


# --- Q&A ---

@app.post("/ask", response_model=RagAnswer)
@track_latency("ask")
def ask(req: AskRequest):
    """Synchronous Q&A with full response."""
    # Determine llm_provider from notebook settings
    llm_provider = None
    if req.filters and getattr(req.filters, "notebook_id", None):
        nb = get_notebook_store().get_notebook(req.filters.notebook_id)
        if nb:
            llm_provider = nb.llm_provider

    # Save to session if session_id provided
    if req.session_id:
        store = get_session_store()
        session = store.get_or_create(req.session_id)
        session.add_message("user", req.question)

    result = answer(
        req.question,
        k=req.k,
        filters=filters_to_dict(req.filters),
        session_id=req.session_id,
        llm_provider=llm_provider,
    )

    # Save assistant response to session
    if req.session_id:
        session.add_message("assistant", result.answer)

    return result


@app.post("/ask/stream")
@track_latency("ask_stream")
def ask_stream(req: AskRequest):
    """
    Streaming Q&A via Server-Sent Events (SSE).
    Yields text chunks as SSE data events.
    """
    from src.stream_batching import get_stream_batcher

    # Determine llm_provider from notebook settings
    llm_provider = None
    if req.filters and getattr(req.filters, "notebook_id", None):
        nb = get_notebook_store().get_notebook(req.filters.notebook_id)
        if nb:
            llm_provider = nb.llm_provider

    def generate():
        try:
            batcher = get_stream_batcher()
            token_stream = answer_stream(
                req.question,
                k=req.k,
                filters=filters_to_dict(req.filters),
                llm_provider=llm_provider,
            )
            yield from batcher.batch_as_sse(token_stream)
        except Exception as e:
            logger.exception("Error during SSE streaming")
            error_data = json.dumps({"text": "\n\n⚠️ Xin lỗi, hệ thống AI đang quá tải hoặc gặp sự cố mạng. Vui lòng thử lại sau ít phút!", "done": True}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Summarize ---

def _save_learning_data(req, res, material_type: str):
    filters_dict = filters_to_dict(req.filters)
    nb_id = filters_dict.get("notebook_id")
    if nb_id:
        from src.notebook_store import get_notebook_store
        store = get_notebook_store()
        nb = store.get_notebook(nb_id)
        if nb:
            doc_key = req.document or "all"
            if material_type not in nb.learning_data:
                nb.learning_data[material_type] = {}
            # Dump the pydantic model to dict
            nb.learning_data[material_type][doc_key] = res.model_dump()
            store._save_notebook(nb)

@app.post("/summarize", response_model=Summary)
@track_latency("summarize")
def summarize_endpoint(req: SummarizeRequest):
    try:
        res = summarize_learning(
            document=req.document,
            query=req.query,
            filters=filters_to_dict(req.filters),
            k=req.k,
        )
        _save_learning_data(req, res, "summary")
        return res
    except Exception as e:
        logger.exception("LLM Error in summarize")
        raise HTTPException(status_code=503, detail="Hệ thống AI đang quá tải hoặc gặp sự cố. Vui lòng thử lại sau!")


# --- Quiz ---

@app.post("/quiz", response_model=QuizSet)
@track_latency("quiz")
def quiz_endpoint(req: QuizRequest):
    try:
        res = generate_quiz(
            document=req.document,
            query=req.query,
            filters=filters_to_dict(req.filters),
            count=req.count,
            k=req.k,
        )
        _save_learning_data(req, res, "quiz")
        return res
    except Exception as e:
        logger.exception("LLM Error in quiz")
        raise HTTPException(status_code=503, detail="Hệ thống AI đang quá tải hoặc gặp sự cố. Vui lòng thử lại sau!")


# --- Flashcards ---

@app.post("/flashcards", response_model=FlashcardSet)
@track_latency("flashcards")
def flashcards_endpoint(req: FlashcardsRequest):
    try:
        res = generate_flashcards(
            document=req.document,
            query=req.query,
            filters=filters_to_dict(req.filters),
            count=req.count,
            k=req.k,
        )
        _save_learning_data(req, res, "flashcards")
        return res
    except Exception as e:
        logger.exception("LLM Error in flashcards")
        raise HTTPException(status_code=503, detail="Hệ thống AI đang quá tải hoặc gặp sự cố. Vui lòng thử lại sau!")

@app.delete("/notebooks/{notebook_id}/learning/{material_type}")
def delete_learning_data(notebook_id: str, material_type: str, document: str = "all"):
    """Delete a specific learning material (quiz, flashcards, summary) for a document."""
    from src.notebook_store import get_notebook_store
    store = get_notebook_store()
    nb = store.get_notebook(notebook_id)
    if nb and material_type in nb.learning_data:
        if document in nb.learning_data[material_type]:
            del nb.learning_data[material_type][document]
            store._save_notebook(nb)
            return {"status": "deleted"}
    return {"status": "not_found"}


# --- Session Management ---

@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Get conversation history for a session."""
    store = get_session_store()
    session = store.get(session_id)
    if session is None:
        return {"session_id": session_id, "messages": []}
    return {"session_id": session_id, "messages": session.get_history()}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Clear a session's conversation history."""
    store = get_session_store()
    deleted = store.delete(session_id)
    return {"session_id": session_id, "deleted": deleted}


# --- Feedback ---

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Record thumbs up/down feedback."""
    record_feedback(req.feedback_type)
    return {"status": "recorded", "feedback_type": req.feedback_type}


# --- Observability ---

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    body, content_type = get_metrics_response()
    return Response(content=body, media_type=content_type)
