from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from kimmy.chat.models import ChatBase


class MemoryState(ChatBase):
    __tablename__ = "memory_states"
    user_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    generation: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))


class MemoryRevision(ChatBase):
    __tablename__ = "memory_revisions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("memory_states.user_id"))
    content: Mapped[str] = mapped_column(Text)
    active: Mapped[bool]
    source_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_messages.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        Index(
            "memory_one_active_idx", "id", unique=True, postgresql_where=text("active")
        ),
        Index("memory_user_active_idx", "user_id", "active"),
    )
