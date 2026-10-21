from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Cursors are decimal strings on the wire, just like other PostgreSQL bigints.
Cursor = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]
RunStatus = Literal["queued", "running", "completed", "failed"]


class CreateThread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="Percakapan baru", min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value


class SendMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must not be blank")
        return value


class ThreadView(BaseModel):
    id: UUID
    title: str
    through_seq: Cursor
    created_at: datetime
    updated_at: datetime


class ThreadPage(BaseModel):
    threads: list[ThreadView]
    next_offset: int | None


class MessageView(BaseModel):
    id: UUID
    thread_id: UUID
    seq: Cursor
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class RunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    thread_id: UUID
    message_id: UUID
    status: RunStatus
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class Admission(BaseModel):
    run: RunView
    replayed: bool


class Snapshot(BaseModel):
    thread: ThreadView
    messages: list[MessageView]
    active_run: RunView | None
    latest_run: RunView | None
    through_seq: Cursor
    before_seq: Cursor | None


class EventView(BaseModel):
    thread_id: UUID
    seq: Cursor
    run_id: UUID
    kind: str
    payload: dict[str, object]
    created_at: datetime


class EventPage(BaseModel):
    events: list[EventView]
    through_seq: Cursor
    next_after_seq: Cursor
    has_more: bool
