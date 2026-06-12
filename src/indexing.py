"""
Data Ingestion Pipeline — Tầng Xử lý Dữ liệu
MarkItDown Parser → Recursive Chunker → Embedder → Qdrant + BM25
"""
import hashlib
import uuid
import logging
from collections import defaultdict
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config import settings
from src.schemas import ChunkMetadata
from src.store import get_vector_store, ensure_collection
from src.bm25_index import BM25Document, get_bm25_index

logger = logging.getLogger(__name__)


def _document_id(path: Path) -> str:
    raw = f"{path.name}:{path.stat().st_size}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _chunk_id(doc_id: str, page: int, index: int) -> str:
    return f"{doc_id}:{page}:{index}"


def _load_with_markitdown(path: Path):
    """
    Use MarkItDown to parse multimodal documents (PDF, DOCX, PPTX, Images, etc.)
    into Markdown text. Falls back to PyPDFLoader for plain PDFs if MarkItDown fails.
    """
    doc_id = _document_id(path)

    try:
        from markitdown import MarkItDown
        from openai import Client as OpenAIClient
        import re
        from langchain_text_splitters import MarkdownHeaderTextSplitter

        # Configure OCR client
        llm_client = None
        llm_model = None
        if settings.llm_provider == "gemini" and settings.google_api_key:
            llm_client = OpenAIClient(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=settings.google_api_key,
            )
            llm_model = settings.gemini_model
        elif settings.llm_provider == "vllm" and settings.vllm_api_base:
            llm_client = OpenAIClient(
                base_url=settings.vllm_api_base,
                api_key=settings.vllm_api_key,
            )
            llm_model = settings.hf_model

        if llm_client and llm_model:
            md = MarkItDown(llm_client=llm_client, llm_model=llm_model)
        else:
            md = MarkItDown()

        result = md.convert(str(path))
        markdown_text = result.text_content

        if not markdown_text or not markdown_text.strip():
            logger.warning("MarkItDown produced empty output for %s, falling back to PyPDF.", path.name)
            return _load_pdf_fallback(path, doc_id)

        # Pre-process DOCX bold pseudo-headings: lines with just **text** -> # text
        markdown_text = re.sub(r'^\s*\*\*(.+?)\*\*\s*$', r'# \1', markdown_text, flags=re.MULTILINE)

        # MarkItDown returns single text block — split into pages by page breaks or sections
        # For PDFs, we try to detect page boundaries
        pages = _split_into_pages(markdown_text, path.name)

        documents = []
        
        # Setup Markdown header splitter
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )

        for page_num, page_text in enumerate(pages, start=1):
            if page_text.strip():
                try:
                    sub_docs = markdown_splitter.split_text(page_text)
                    if not sub_docs:
                        raise ValueError("Empty split")
                    for sub_doc in sub_docs:
                        # Extract the most specific header as the section
                        section_name = sub_doc.metadata.get("Header 4") or sub_doc.metadata.get("Header 3") or sub_doc.metadata.get("Header 2") or sub_doc.metadata.get("Header 1")
                        
                        documents.append(Document(
                            page_content=sub_doc.page_content,
                            metadata={
                                "document_id": doc_id,
                                "filename": path.name,
                                "source": str(path.resolve()),
                                "page": page_num,
                                "section": section_name,
                            },
                        ))
                except Exception as ex:
                    # Fallback to entire page if splitter fails
                    logger.warning(f"MarkdownHeaderTextSplitter failed on page {page_num}: {ex}")
                    documents.append(Document(
                        page_content=page_text,
                        metadata={
                            "document_id": doc_id,
                            "filename": path.name,
                            "source": str(path.resolve()),
                            "page": page_num,
                            "section": None,
                        },
                    ))

        logger.info("MarkItDown parsed %s: %d pages/sections.", path.name, len(documents))
        return documents

    except Exception as exc:
        logger.warning("MarkItDown failed for %s (%s), falling back to PyPDF.", path.name, exc)
        return _load_pdf_fallback(path, doc_id)


def _split_into_pages(text: str, filename: str):
    """
    Split MarkItDown output into logical pages.
    Tries page break markers first, then falls back to section headers.
    """
    import re

    # Check for PowerPoint slide markers from MarkItDown
    slide_break_pattern = r'\n*(?=<!-- Slide number: \d+ -->)\n*'
    parts = re.split(slide_break_pattern, text, flags=re.IGNORECASE)
    if len(parts) > 1:
        return [p for p in parts if p.strip()]

    # Check for page break markers (common in PDF conversions)
    page_break_pattern = r'\n-{3,}\s*(?:page\s*\d+|trang\s*\d+)?\s*-{3,}\n'
    parts = re.split(page_break_pattern, text, flags=re.IGNORECASE)

    if len(parts) > 1:
        return [p for p in parts if p.strip()]

    # Fallback: split by major headings (# or ##)
    heading_pattern = r'\n(?=# )'
    parts = re.split(heading_pattern, text)

    if len(parts) > 1:
        return [p for p in parts if p.strip()]

    # Last resort: return as single page
    return [text] if text.strip() else []


def _load_pdf_fallback(path: Path, doc_id: str):
    """Fallback to PyPDFLoader for standard PDF loading."""
    from langchain_community.document_loaders import PyPDFLoader

    pages = PyPDFLoader(str(path)).load()

    for doc in pages:
        page_number = int(doc.metadata.get("page", 0)) + 1
        doc.metadata = {
            "document_id": doc_id,
            "filename": path.name,
            "source": str(path.resolve()),
            "page": page_number,
            "section": doc.metadata.get("section"),
        }
    return pages


def _splitter(chunk_size=None, chunk_overlap=None):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=False,
    )


def build_chunks(file_paths, notebook_id=None, chunk_size=None, chunk_overlap=None, chunker=None):
    """Parse files and split into chunks."""
    page_docs = []
    for path in file_paths:
        p = Path(path)
        page_docs.extend(_load_with_markitdown(p))

    splitter = chunker or _splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(page_docs)
    per_doc_counter = defaultdict(int)

    for chunk in chunks:
        doc_id = chunk.metadata["document_id"]
        idx = per_doc_counter[doc_id]
        per_doc_counter[doc_id] += 1

        meta = ChunkMetadata(
            document_id=doc_id,
            notebook_id=notebook_id,
            filename=chunk.metadata["filename"],
            source=chunk.metadata["source"],
            page=chunk.metadata["page"],
            chunk_id=_chunk_id(doc_id, chunk.metadata["page"], idx),
            section=chunk.metadata.get("section"),
        )
        chunk.metadata = meta.model_dump()

    return chunks


def _build_bm25_from_chunks(chunks, notebook_id):
    """Build BM25 index from LangChain Document chunks."""
    bm25_docs = [
        BM25Document(
            chunk_id=c.metadata["chunk_id"],
            text=c.page_content,
            metadata=c.metadata,
        )
        for c in chunks
    ]
    bm25_index = get_bm25_index(notebook_id)
    bm25_index.build(bm25_docs)
    bm25_index.save()
    logger.info("BM25 index built and persisted: %d documents.", len(bm25_docs))


def index_chunks(chunks, collection_name=None):
    """Index chunks into Qdrant vector store."""
    if not chunks:
        return 0
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c.metadata["chunk_id"])) for c in chunks]
    get_vector_store(collection_name=collection_name).add_documents(chunks, ids=ids)
    return len(chunks)


def discover_files():
    """Discover all supported files in the data directory."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    supported_exts = ["*.pdf", "*.docx", "*.pptx", "*.xlsx", "*.html", "*.md", "*.txt"]
    files = []
    for ext in supported_exts:
        files.extend(settings.data_dir.glob(ext))
    return files


def discover_pdfs():
    """Legacy function: discover only PDFs."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return list(settings.data_dir.glob("*.pdf"))


def ingest(recreate=False, collection_name=None, chunker=None, chunk_size=None, chunk_overlap=None):
    """
    Full ingestion pipeline: discover files → parse → chunk → embed → index (Qdrant + BM25).
    """
    files = discover_files()
    if not files:
        logger.warning("No files found in %s.", settings.data_dir)
        return 0

    ensure_collection(recreate=recreate, collection_name=collection_name)
    chunks = build_chunks(files, chunker=chunker, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Index into Qdrant
    count = index_chunks(chunks, collection_name=collection_name)

    # Build BM25 index
    _build_bm25_from_chunks(chunks, "default")

    # Record metrics
    from src.observability import record_chunks_indexed
    record_chunks_indexed(count)

    logger.info("Ingestion complete: %d chunks indexed.", count)
    return count


def save_and_ingest_file(file_bytes, filename, notebook_id):
    """Save an uploaded file and ingest it."""
    import re
    import time
    
    safe_name = Path(filename).name
    
    # Đổi tên tự động nếu file có tên chung chung do copy-paste (image.png, image.jpg)
    if re.match(r'^image\.(png|jpg|jpeg)$', safe_name, re.IGNORECASE):
        p = Path(safe_name)
        safe_name = f"clipboard_{int(time.time())}{p.suffix}"
        
    dest = settings.data_dir / safe_name
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)

    ensure_collection(recreate=False)
    chunks = build_chunks([dest], notebook_id=notebook_id)

    # Chặn Race Condition: Kiểm tra xem Notebook có bị user xóa trong lúc đang xử lý không
    from src.notebook_store import get_notebook_store
    nb = get_notebook_store().get_notebook(notebook_id)
    if not nb:
        logger.warning("Notebook %s bị xóa trong quá trình xử lý file %s. Tự hủy tiến trình.", notebook_id, filename)
        return {"filename": safe_name, "chunks_indexed": 0}

    # Dọn dẹp dữ liệu cũ nếu re-upload trùng tên file (Tránh lỗi nhân bản rác Qdrant & BM25)
    for doc in nb.documents:
        if doc.filename == safe_name:
            logger.info("Phát hiện nạp lại file trùng tên %s, dọn dẹp bản cũ...", safe_name)
            # Dọn Qdrant
            from src.store import get_client
            from qdrant_client.http import models
            try:
                get_client().delete(
                    collection_name=settings.qdrant_collection,
                    points_selector=models.Filter(
                        must=[
                            models.FieldCondition(key="filename", match=models.MatchValue(value=safe_name)),
                            models.FieldCondition(key="document_id", match=models.MatchValue(value=notebook_id))
                        ]
                    )
                )
            except Exception as e:
                logger.error("Lỗi xóa Qdrant cũ: %s", e)
            
            # Dọn BM25
            try:
                idx = get_bm25_index(notebook_id)
                idx.remove_document(safe_name)
            except Exception as e:
                logger.error("Lỗi xóa BM25 cũ: %s", e)
            break

    # Index into Qdrant
    indexed = index_chunks(chunks)

    # Add to BM25 index
    bm25_docs = [
        BM25Document(chunk_id=c.metadata["chunk_id"], text=c.page_content, metadata=c.metadata)
        for c in chunks
    ]
    bm25_index = get_bm25_index(notebook_id)
    bm25_index.add_documents(bm25_docs)
    bm25_index.save()

    # Record metrics
    from src.observability import record_chunks_indexed
    record_chunks_indexed(indexed)

    return {"filename": safe_name, "chunks_indexed": indexed}


# Legacy alias
save_and_ingest_pdf = save_and_ingest_file
