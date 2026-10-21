from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.chat.models import Event, Message, Run, RunCommand, Thread


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def thread(
        self, thread_id: UUID, user_id: str, *, lock: bool = False
    ) -> Thread | None:
        query = select(Thread).where(Thread.id == thread_id, Thread.user_id == user_id)
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def threads(self, user_id: str, limit: int, offset: int) -> list[Thread]:
        return list(
            await self.session.scalars(
                select(Thread)
                .where(Thread.user_id == user_id)
                .order_by(Thread.updated_at.desc(), Thread.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    async def create_thread(self, user_id: str, title: str) -> Thread:
        thread = Thread(user_id=user_id, title=title)
        self.session.add(thread)
        await self.session.flush()
        return thread

    async def replay(
        self, thread_id: UUID, request_key: str
    ) -> tuple[Run, Message] | None:
        row = (
            await self.session.execute(
                select(Run, Message)
                .join(Message, Run.message_id == Message.id)
                .where(Run.thread_id == thread_id, Run.request_key == request_key)
            )
        ).one_or_none()
        return (row.Run, row.Message) if row else None

    async def active_run(self, thread_id: UUID) -> Run | None:
        return await self.session.scalar(
            select(Run).where(
                Run.thread_id == thread_id, Run.status.in_(("queued", "running"))
            )
        )

    async def latest_run(self, thread_id: UUID) -> Run | None:
        return await self.session.scalar(
            select(Run)
            .join(Message, Run.message_id == Message.id)
            .where(Run.thread_id == thread_id)
            .order_by(Message.seq.desc())
            .limit(1)
        )

    async def run(self, run_id: UUID, thread_id: UUID) -> Run | None:
        return await self.session.scalar(
            select(Run).where(Run.id == run_id, Run.thread_id == thread_id)
        )

    async def input_message(self, run: Run) -> Message:
        message = await self.session.get(Message, run.message_id)
        if message is None or message.thread_id != run.thread_id:
            raise RuntimeError("Run input message is missing")
        return message

    async def completed_checkpoint(
        self, thread_id: UUID, generation: int
    ) -> str | None:
        return await self.session.scalar(
            select(Run.checkpoint_id)
            .join(Message, Run.message_id == Message.id)
            .where(
                Run.thread_id == thread_id,
                Run.status == "completed",
                Run.memory_generation == generation,
            )
            .order_by(Message.seq.desc())
            .limit(1)
        )

    async def create_answer(
        self, thread: Thread, content: str, citations: list[dict[str, object]]
    ) -> Message:
        message = Message(
            thread_id=thread.id,
            seq=thread.last_seq + 1,
            role="assistant",
            content=content,
            citations=citations,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def messages(
        self, thread_id: UUID, before_seq: int, limit: int
    ) -> list[Message]:
        return list(
            await self.session.scalars(
                select(Message)
                .where(Message.thread_id == thread_id, Message.seq < before_seq)
                .order_by(Message.seq.desc())
                .limit(limit)
            )
        )

    async def events(
        self, thread_id: UUID, after_seq: int, through_seq: int, limit: int
    ) -> list[Event]:
        return list(
            await self.session.scalars(
                select(Event)
                .where(
                    Event.thread_id == thread_id,
                    Event.seq > after_seq,
                    Event.seq <= through_seq,
                )
                .order_by(Event.seq)
                .limit(limit)
            )
        )

    async def activity(
        self, thread_id: UUID, message_ids: list[UUID], through_seq: int
    ) -> tuple[list[Run], list[Event]]:
        runs = list(
            await self.session.scalars(
                select(Run).where(
                    Run.thread_id == thread_id, Run.message_id.in_(message_ids)
                )
            )
        )
        events = list(
            await self.session.scalars(
                select(Event)
                .where(
                    Event.thread_id == thread_id,
                    Event.run_id.in_([run.id for run in runs]),
                    Event.seq <= through_seq,
                    Event.kind.in_(
                        (
                            "run.queued",
                            "agent.text_delta",
                            "tool.requested",
                            "tool.completed",
                        )
                    ),
                )
                .order_by(Event.seq)
            )
        )
        return runs, events

    async def create_run(
        self, thread: Thread, request_key: str, content: str, provider: str, model: str
    ) -> tuple[Run, Message]:
        message = Message(
            thread_id=thread.id, seq=thread.last_seq + 1, role="user", content=content
        )
        self.session.add(message)
        await self.session.flush()
        run = Run(
            thread_id=thread.id,
            message_id=message.id,
            request_key=request_key,
            status="queued",
            provider=provider,
            model=model,
        )
        self.session.add(run)
        await self.session.flush()
        return run, message

    async def append_event(
        self, thread: Thread, run: Run, kind: str, payload: dict[str, object]
    ) -> None:
        # Every writer holds the thread row lock until commit. Sequence order is
        # therefore commit order; a later transaction cannot expose a cursor gap.
        thread.last_seq += 1
        thread.updated_at = datetime.now(UTC)
        self.session.add(
            Event(
                thread_id=thread.id,
                seq=thread.last_seq,
                run_id=run.id,
                kind=kind,
                payload=payload,
            )
        )
        await self.session.flush()

    async def stale_runs(self) -> list[tuple[UUID, UUID, str]]:
        rows = await self.session.execute(
            select(Run.id, Run.thread_id, Thread.user_id)
            .join(Thread)
            .where(
                Run.status == "running",
                or_(Run.lease_until.is_(None), Run.lease_until < func.now()),
            )
            .limit(100)
        )
        return [(r.id, r.thread_id, r.user_id) for r in rows]

    async def command(self, run_id: UUID, request_key: str) -> RunCommand | None:
        return await self.session.get(RunCommand, (run_id, request_key))
