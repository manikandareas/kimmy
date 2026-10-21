from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import procrastinate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.agent.context import AgentContext
from kimmy.chat.models import Message, Thread
from kimmy.chat.repository import ChatRepository
from kimmy.chat.schemas import (
    Admission,
    EventPage,
    EventView,
    MessageView,
    RunView,
    SendMessage,
    Snapshot,
    ThreadPage,
    ThreadView,
)
from kimmy.errors import DomainError
from kimmy.jobs.queue import enqueue_run


def thread_view(thread: Thread) -> ThreadView:
    return ThreadView(
        id=thread.id,
        title=thread.title,
        through_seq=str(thread.last_seq),
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def message_view(message: Message) -> MessageView:
    return MessageView.model_validate(
        {
            "id": message.id,
            "thread_id": message.thread_id,
            "seq": str(message.seq),
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }
    )


class ChatService:
    def __init__(self, engine: AsyncEngine, queue: procrastinate.App):
        self.engine = engine
        self.queue = queue

    @asynccontextmanager
    async def repository(
        self, *, read_only: bool = False
    ) -> AsyncIterator[ChatRepository]:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                if read_only:
                    await session.execute(
                        text(
                            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                        )
                    )
                yield ChatRepository(session)

    async def require_thread(
        self, repo: ChatRepository, thread_id: UUID, user_id: str, *, lock: bool = False
    ) -> Thread:
        thread = await repo.thread(thread_id, user_id, lock=lock)
        if thread is None:
            raise DomainError(404, "THREAD_NOT_FOUND", "Thread not found")
        return thread

    async def create_thread(self, user_id: str, title: str) -> ThreadView:
        async with self.repository() as repo:
            return thread_view(await repo.create_thread(user_id, title))

    async def list_threads(self, user_id: str, limit: int, offset: int) -> ThreadPage:
        async with self.repository(read_only=True) as repo:
            threads = await repo.threads(user_id, limit + 1, offset)
            return ThreadPage(
                threads=[thread_view(t) for t in threads[:limit]],
                next_offset=offset + limit if len(threads) > limit else None,
            )

    async def admit(
        self, thread_id: UUID, user_id: str, request: SendMessage
    ) -> Admission:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            replay = await repo.replay(thread_id, request.request_key)
            if replay is not None:
                run, message = replay
                if message.content != request.content:
                    raise DomainError(
                        409,
                        "REQUEST_KEY_CONFLICT",
                        "Request key was already used with a different payload",
                    )
                return Admission(run=RunView.model_validate(run), replayed=True)
            if await repo.active_run(thread_id) is not None:
                raise DomainError(
                    409,
                    "THREAD_BUSY",
                    "Wait for the active run before sending another message",
                )
            run, message = await repo.create_run(
                thread, request.request_key, request.content
            )
            await repo.append_event(
                thread,
                run,
                "message.created",
                {"message": message_view(message).model_dump(mode="json")},
            )
            await repo.append_event(
                thread,
                run,
                "run.queued",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )
            await enqueue_run(self.queue, repo.session, run.id, thread_id, user_id)
            return Admission(run=RunView.model_validate(run), replayed=False)

    async def snapshot(
        self,
        thread_id: UUID,
        user_id: str,
        limit: int = 100,
        before_seq: int | None = None,
    ) -> Snapshot:
        async with self.repository(read_only=True) as repo:
            thread = await self.require_thread(repo, thread_id, user_id)
            messages = await repo.messages(
                thread_id,
                before_seq if before_seq is not None else thread.last_seq + 1,
                limit + 1,
            )
            page = messages[:limit]
            active = await repo.active_run(thread_id)
            latest = await repo.latest_run(thread_id)
            return Snapshot(
                thread=thread_view(thread),
                messages=[message_view(m) for m in reversed(page)],
                active_run=RunView.model_validate(active) if active else None,
                latest_run=RunView.model_validate(latest) if latest else None,
                through_seq=str(thread.last_seq),
                before_seq=str(page[-1].seq) if len(messages) > limit else None,
            )

    async def get_run(self, thread_id: UUID, user_id: str, run_id: UUID) -> RunView:
        async with self.repository(read_only=True) as repo:
            await self.require_thread(repo, thread_id, user_id)
            run = await repo.run(run_id, thread_id)
            if run is None:
                raise DomainError(404, "RUN_NOT_FOUND", "Run not found")
            return RunView.model_validate(run)

    async def events(
        self, thread_id: UUID, user_id: str, after_seq: int, limit: int = 100
    ) -> EventPage:
        async with self.repository(read_only=True) as repo:
            thread = await self.require_thread(repo, thread_id, user_id)
            if after_seq > thread.last_seq:
                raise DomainError(
                    409,
                    "CURSOR_AHEAD",
                    "Cursor is ahead of this thread; reload its snapshot",
                )
            events = await repo.events(thread_id, after_seq, thread.last_seq, limit + 1)
            page = events[:limit]
            return EventPage(
                events=[
                    EventView(
                        thread_id=e.thread_id,
                        seq=str(e.seq),
                        run_id=e.run_id,
                        kind=e.kind,
                        payload=e.payload,
                        created_at=e.created_at,
                    )
                    for e in page
                ],
                through_seq=str(thread.last_seq),
                next_after_seq=str(page[-1].seq if page else after_seq),
                has_more=len(events) > limit,
            )

    async def claim(self, thread_id: UUID, user_id: str, run_id: UUID) -> bool:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            if run is None or run.status != "queued":
                return False
            run.status = "running"
            run.started_at = datetime.now(UTC)
            await repo.append_event(
                thread,
                run,
                "run.running",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )
            return True

    async def fail(
        self, thread_id: UUID, user_id: str, run_id: UUID, code: str
    ) -> None:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            if run is None or run.status != "running":
                return
            run.status = "failed"
            run.error_code = code
            run.finished_at = datetime.now(UTC)
            await repo.append_event(
                thread,
                run,
                "run.failed",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )

    async def execution_input(
        self, thread_id: UUID, user_id: str, run_id: UUID
    ) -> tuple[AgentContext, str, str | None]:
        async with self.repository(read_only=True) as repo:
            thread = await self.require_thread(repo, thread_id, user_id)
            run = await repo.run(run_id, thread_id)
            if run is None or run.status != "running":
                raise DomainError(409, "RUN_NOT_RUNNING", "Run is not running")
            message = await repo.input_message(run)
            return (
                AgentContext(thread.user_id, thread.id, run.id, message.id),
                message.content,
                await repo.completed_checkpoint(thread_id),
            )

    async def progress(
        self, context: AgentContext, kind: str, payload: dict[str, object]
    ) -> None:
        async with self.repository() as repo:
            thread = await self.require_thread(
                repo, context.thread_id, context.user_id, lock=True
            )
            run = await repo.run(context.run_id, context.thread_id)
            if run is None or run.status != "running":
                raise DomainError(409, "RUN_NOT_RUNNING", "Run is not running")
            await repo.append_event(thread, run, kind, payload)

    async def complete(
        self, context: AgentContext, content: str, checkpoint_id: str
    ) -> None:
        async with self.repository() as repo:
            thread = await self.require_thread(
                repo, context.thread_id, context.user_id, lock=True
            )
            run = await repo.run(context.run_id, context.thread_id)
            if run is None or run.status != "running":
                raise DomainError(409, "RUN_NOT_RUNNING", "Run is not running")
            answer = await repo.create_answer(thread, content)
            await repo.append_event(
                thread,
                run,
                "message.created",
                {"message": message_view(answer).model_dump(mode="json")},
            )
            run.checkpoint_id = checkpoint_id
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            await repo.append_event(
                thread,
                run,
                "run.completed",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )
