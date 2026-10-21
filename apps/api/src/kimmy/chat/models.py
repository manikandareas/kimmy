from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ChatBase(DeclarativeBase):
    pass


class Thread(ChatBase):
    __tablename__ = "chat_threads"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    last_seq: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint("last_seq >= 0", name="chat_threads_seq_check"),
        Index("chat_threads_user_updated_idx", "user_id", "updated_at", "id"),
    )


class Message(ChatBase):
    __tablename__ = "chat_messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("chat_threads.id"))
    seq: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        UniqueConstraint("thread_id", "seq", name="chat_messages_thread_seq_key"),
        CheckConstraint(
            "role IN ('user', 'assistant')", name="chat_messages_role_check"
        ),
        CheckConstraint("seq > 0", name="chat_messages_seq_check"),
    )


class Run(ChatBase):
    __tablename__ = "chat_runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("chat_threads.id"))
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id"), unique=True
    )
    request_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(80))
    memory_generation: Mapped[int | None] = mapped_column(BigInteger)
    reset_history: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    owner_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    provider: Mapped[str] = mapped_column(String(20), server_default="openai")
    model: Mapped[str | None] = mapped_column(String(200))
    resume_checkpoint_id: Mapped[str | None] = mapped_column(String(80))
    checkpoint_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("thread_id", "request_key", name="chat_runs_request_key"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="chat_runs_status_check",
        ),
        Index(
            "chat_runs_one_active_idx",
            "thread_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
        Index("chat_runs_thread_created_idx", "thread_id", "created_at", "id"),
    )


class Event(ChatBase):
    __tablename__ = "chat_events"
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_threads.id"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("chat_runs.id"))
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (CheckConstraint("seq > 0", name="chat_events_seq_check"),)


class RunCommand(ChatBase):
    __tablename__ = "chat_run_commands"
    run_id: Mapped[UUID] = mapped_column(ForeignKey("chat_runs.id"), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    expected_attempt: Mapped[int] = mapped_column(Integer)
