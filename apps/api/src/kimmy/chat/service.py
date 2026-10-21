from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import procrastinate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.agent.context import AgentContext
from kimmy.chat.activity import project_activity
from kimmy.chat.models import Message, Run, RunCommand, Thread
from kimmy.chat.ownership import require_owner
from kimmy.chat.repository import ChatRepository
from kimmy.chat.schemas import (
    Admission,
    EventPage,
    EventView,
    MessageView,
    RunCommandRequest,
    RunView,
    SendMessage,
    Snapshot,
    ThreadPage,
    ThreadView,
)
from kimmy.config import get_settings
from kimmy.errors import DomainError
from kimmy.jobs.queue import enqueue_run
from kimmy.knowledge.schemas import Citation
from kimmy.memory.repository import MemoryRepository
from kimmy.memory.service import require_generation


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
            "citations": message.citations,
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
                if message.content != request.content or (
                    request.provider is not None and run.provider != request.provider
                ):
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
            settings = get_settings()
            provider = request.provider or settings.chat_provider
            model = (
                settings.openai_chat_model
                if provider == "openai"
                else settings.openrouter_chat_model
            )
            run, message = await repo.create_run(
                thread, request.request_key, request.content, provider, model
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
            runs, activity_events = await repo.activity(
                thread_id, [m.id for m in page if m.role == "user"], thread.last_seq
            )
            return Snapshot(
                thread=thread_view(thread),
                messages=[message_view(m) for m in reversed(page)],
                active_run=RunView.model_validate(active) if active else None,
                latest_run=RunView.model_validate(latest) if latest else None,
                through_seq=str(thread.last_seq),
                before_seq=str(page[-1].seq) if len(messages) > limit else None,
                activities=project_activity(runs, activity_events),
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

    async def claim(self, thread_id: UUID, user_id: str, run_id: UUID) -> UUID | None:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            if run is None or run.status != "queued":
                return None
            if run.attempts >= 3:
                return None
            run.attempts += 1
            run.owner_token = uuid4()
            run.lease_until = datetime.now(UTC) + timedelta(seconds=30)
            run.status = "running"
            run.started_at = datetime.now(UTC)
            await repo.append_event(
                thread,
                run,
                "run.running",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )
            return run.owner_token

    async def fail(
        self, thread_id: UUID, user_id: str, run_id: UUID, code: str, token: UUID
    ) -> None:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            if run is None or run.status != "running":
                return
            if (
                run.owner_token != token
                or run.lease_until is None
                or run.lease_until <= datetime.now(UTC)
            ):
                return
            run.owner_token = None
            run.lease_until = None
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
        self, thread_id: UUID, user_id: str, run_id: UUID, token: UUID
    ) -> tuple[AgentContext, str, str | None]:
        async with self.repository() as repo:
            state = await MemoryRepository(repo.session).lock(user_id)
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            require_owner(run, token)
            assert run is not None
            resume = bool(
                run.resume_checkpoint_id and run.memory_generation == state.generation
            )
            if not resume:
                run.resume_checkpoint_id = None
            run.memory_generation = state.generation
            message = await repo.input_message(run)
            return (
                AgentContext(
                    thread.user_id,
                    thread.id,
                    run.id,
                    message.id,
                    state.generation,
                    reset_history=run.reset_history,
                    owner_token=token,
                    resume=resume,
                    provider=run.provider,
                    model=run.model,
                ),
                message.content,
                run.resume_checkpoint_id
                if resume
                else await repo.completed_checkpoint(thread_id, state.generation),
            )

    async def progress(
        self, context: AgentContext, kind: str, payload: dict[str, object]
    ) -> None:
        async with self.repository() as repo:
            state = await MemoryRepository(repo.session).lock(context.user_id)
            require_generation(state.generation, context.memory_generation)
            thread = await self.require_thread(
                repo, context.thread_id, context.user_id, lock=True
            )
            run = await repo.run(context.run_id, context.thread_id)
            require_owner(run, context.owner_token)
            assert run is not None
            await repo.append_event(thread, run, kind, payload)

    async def complete(
        self,
        context: AgentContext,
        content: str,
        checkpoint_id: str,
        citations: list[Citation],
    ) -> None:
        async with self.repository() as repo:
            state = await MemoryRepository(repo.session).lock(context.user_id)
            require_generation(state.generation, context.memory_generation)
            thread = await self.require_thread(
                repo, context.thread_id, context.user_id, lock=True
            )
            run = await repo.run(context.run_id, context.thread_id)
            require_owner(run, context.owner_token)
            assert run is not None
            answer = await repo.create_answer(
                thread, content, [c.model_dump(mode="json") for c in citations]
            )
            await repo.append_event(
                thread,
                run,
                "message.created",
                {"message": message_view(answer).model_dump(mode="json")},
            )
            run.memory_generation = context.memory_generation
            # A mutation turn may itself quote revoked content. Do not carry
            # that turn into the next model context; UI history stays intact.
            run.checkpoint_id = None if context.reset_history else checkpoint_id
            run.owner_token = None
            run.lease_until = None
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            await repo.append_event(
                thread,
                run,
                "run.completed",
                {"run": RunView.model_validate(run).model_dump(mode="json")},
            )

    async def heartbeat(
        self, thread_id: UUID, user_id: str, run_id: UUID, token: UUID
    ) -> None:
        async with self.repository() as repo:
            await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            require_owner(run, token)
            assert run is not None
            run.lease_until = datetime.now(UTC) + timedelta(seconds=30)

    async def command(
        self,
        thread_id: UUID,
        user_id: str,
        run_id: UUID,
        kind: str,
        request: RunCommandRequest,
    ) -> RunView:
        async with self.repository() as repo:
            thread = await self.require_thread(repo, thread_id, user_id, lock=True)
            run = await repo.run(run_id, thread_id)
            if run is None:
                raise DomainError(404, "RUN_NOT_FOUND", "Run not found")
            prior = await repo.command(run_id, request.request_key)
            if prior:
                if (
                    prior.kind != kind
                    or prior.expected_attempt != request.expected_attempt
                ):
                    raise DomainError(
                        409, "REQUEST_KEY_CONFLICT", "Command key payload differs"
                    )
                return RunView.model_validate(run)
            if run.attempts != request.expected_attempt:
                raise DomainError(409, "RUN_CHANGED", "Reload the current attempt")
            if kind == "cancel":
                if run.status in {"queued", "running"}:
                    run.status = "cancelled"
                    run.error_code = "RUN_CANCELLED"
                    run.owner_token = None
                    run.lease_until = None
                    run.finished_at = datetime.now(UTC)
                    await self.run_event(repo, thread, run)
            else:
                latest = await repo.latest_run(thread_id)
                if (
                    run.status not in {"failed", "cancelled"}
                    or not latest
                    or latest.id != run.id
                ):
                    raise DomainError(
                        409,
                        "RUN_NOT_RETRYABLE",
                        "Only the latest failed or cancelled run can retry",
                    )
                if await repo.active_run(thread_id):
                    raise DomainError(
                        409, "THREAD_BUSY", "Thread already has an active run"
                    )
                if run.attempts >= 3:
                    raise DomainError(
                        409,
                        "RUN_ATTEMPTS_EXHAUSTED",
                        "Maximum of three attempts reached",
                    )
                # Explicit retries start afresh from the last published checkpoint.
                run.resume_checkpoint_id = None
                await self.requeue(repo, thread, run)
            repo.session.add(
                RunCommand(
                    run_id=run.id,
                    request_key=request.request_key,
                    kind=kind,
                    expected_attempt=request.expected_attempt,
                )
            )
            return RunView.model_validate(run)

    async def run_event(self, repo: ChatRepository, thread: Thread, run: Run) -> None:
        await repo.append_event(
            thread,
            run,
            f"run.{run.status}",
            {"run": RunView.model_validate(run).model_dump(mode="json")},
        )

    async def requeue(self, repo: ChatRepository, thread: Thread, run: Run) -> None:
        run.status = "queued"
        run.error_code = None
        run.finished_at = None
        run.owner_token = None
        run.lease_until = None
        await self.run_event(repo, thread, run)
        await enqueue_run(self.queue, repo.session, run.id, thread.id, thread.user_id)

    async def recover(self) -> None:
        async with self.repository(read_only=True) as repo:
            stale = await repo.stale_runs()
        for run_id, thread_id, user_id in stale:
            async with self.repository() as repo:
                thread = await self.require_thread(repo, thread_id, user_id, lock=True)
                run = await repo.run(run_id, thread_id)
                if (
                    run is None
                    or run.status != "running"
                    or (run.lease_until and run.lease_until > datetime.now(UTC))
                ):
                    continue
                run.owner_token = None
                run.lease_until = None
                if run.attempts >= 3:
                    run.status = "failed"
                    run.error_code = "WORKER_RECOVERY_EXHAUSTED"
                    run.finished_at = datetime.now(UTC)
                    await self.run_event(repo, thread, run)
                else:
                    await self.requeue(repo, thread, run)
