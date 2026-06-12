from typing import Literal, List, Optional
from pydantic import BaseModel, Field, model_validator

class ChunkMetadata(BaseModel):
    document_id: str
    notebook_id: Optional[str] = None
    filename: str
    source: str
    page: int
    chunk_id: str
    section: Optional[str] = None

class RetrievedChunk(BaseModel):
    text: str
    score: float
    metadata: ChunkMetadata

class Citation(BaseModel):
    source_index: int
    source_marker: str
    filename: str
    page: int
    section: Optional[str] = None
    chunk_id: Optional[str] = None

class RagAnswer(BaseModel):
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    chunks: List[RetrievedChunk] = Field(default_factory=list)

class Summary(BaseModel):
    scope: Literal["query", "document", "filter", "corpus"]
    target: Optional[str] = None
    summary: str
    key_points: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    chunks: List[RetrievedChunk] = Field(default_factory=list)

class QuizItem(BaseModel):
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    correct_index: int
    explanation: str
    source_markers: List[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    topic: Optional[str] = None

    @model_validator(mode="after")
    def _validate_correct_index(self) -> "QuizItem":
        if not 0 <= self.correct_index < len(self.options):
            raise ValueError("correct_index out of range")
        return self

class QuizSet(BaseModel):
    scope: Literal["query", "document", "filter", "corpus"]
    target: Optional[str] = None
    items: List[QuizItem] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    chunks: List[RetrievedChunk] = Field(default_factory=list)

class Flashcard(BaseModel):
    front: str
    back: str
    hint: Optional[str] = None
    topic: Optional[str] = None
    source_markers: List[str] = Field(default_factory=list)

class FlashcardSet(BaseModel):
    scope: Literal["query", "document", "filter", "corpus"]
    target: Optional[str] = None
    cards: List[Flashcard] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    chunks: List[RetrievedChunk] = Field(default_factory=list)
