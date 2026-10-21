from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MemoryContent = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: MemoryContent


class MemoryUpdate(MemoryCreate):
    expected_revision: int = Field(ge=1)


class MemoryForget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


class MemoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision: int
    content: str
    active: bool
    source_message_id: UUID | None
    created_at: datetime


class MemoryProfile(BaseModel):
    generation: int
    memories: list[MemoryView]


class MemoryReceipt(BaseModel):
    changed: bool
    generation: int
    memory: MemoryView
