from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Section(BaseModel):
    title: str
    content: str


class Document(BaseModel):
    slug: str
    title: str
    version: str
    effective_date: date
    content_hash: str
    sections: list[Section]


class EmbeddingIdentity(BaseModel):
    model: str
    dimensions: int


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    source: str
    title: str
    section: str
    version: str
    effective_date: date
    quote: str


class Citation(SourceChunk):
    score: float


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=3, ge=1, le=5)


class SearchResult(BaseModel):
    method: str = "cosine_similarity_active_sop"
    citations: list[Citation]


class IndexReceipt(BaseModel):
    documents: int
    chunks: int
    changed: bool
    generation: int
    identity: EmbeddingIdentity
