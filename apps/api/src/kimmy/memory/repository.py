from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.chat.models import Message, Run, Thread
from kimmy.memory.models import MemoryRevision, MemoryState


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock(self, user_id: str) -> MemoryState:
        await self.session.execute(
            insert(MemoryState).values(user_id=user_id).on_conflict_do_nothing()
        )
        state = await self.session.scalar(
            select(MemoryState).where(MemoryState.user_id == user_id).with_for_update()
        )
        assert state is not None
        return state

    async def active(self, user_id: str) -> list[MemoryRevision]:
        return list(
            await self.session.scalars(
                select(MemoryRevision)
                .where(MemoryRevision.user_id == user_id, MemoryRevision.active)
                .order_by(MemoryRevision.created_at, MemoryRevision.id)
                .limit(8)
            )
        )

    async def latest(self, user_id: str, memory_id: UUID) -> MemoryRevision | None:
        return await self.session.scalar(
            select(MemoryRevision)
            .where(MemoryRevision.user_id == user_id, MemoryRevision.id == memory_id)
            .order_by(MemoryRevision.revision.desc())
            .limit(1)
        )

    async def valid_source(
        self, user_id: str, thread_id: UUID, run_id: UUID, message_id: UUID
    ) -> bool:
        return (
            await self.session.scalar(
                select(Message.id)
                .join(Thread, Message.thread_id == Thread.id)
                .join(Run, Run.message_id == Message.id)
                .where(
                    Thread.user_id == user_id,
                    Thread.id == thread_id,
                    Message.id == message_id,
                    Message.role == "user",
                    Run.id == run_id,
                    Run.status == "running",
                )
            )
            is not None
        )

    async def add(self, revision: MemoryRevision) -> None:
        self.session.add(revision)
        await self.session.flush()
