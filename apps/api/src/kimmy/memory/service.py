from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.agent.context import AgentContext
from kimmy.chat.ownership import require_owner
from kimmy.chat.repository import ChatRepository
from kimmy.errors import DomainError
from kimmy.memory.models import MemoryRevision
from kimmy.memory.repository import MemoryRepository
from kimmy.memory.schemas import MemoryContent, MemoryProfile, MemoryReceipt, MemoryView


def require_generation(current: int, expected: int) -> None:
    if current != expected:
        raise DomainError(
            409,
            "MEMORY_CHANGED",
            "Memory changed; send a new message with the current context",
        )


class MemoryService:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def profile(self, user_id: str, expected: int | None = None) -> MemoryProfile:
        async with AsyncSession(self.engine) as session, session.begin():
            repo = MemoryRepository(session)
            state = await repo.lock(user_id)
            if expected is not None:
                require_generation(state.generation, expected)
            return MemoryProfile(
                generation=state.generation,
                memories=[
                    MemoryView.model_validate(m) for m in await repo.active(user_id)
                ],
            )

    async def write(
        self,
        user_id: str,
        content: str | None,
        memory_id: UUID | None = None,
        expected_revision: int | None = None,
        context: AgentContext | None = None,
    ) -> MemoryReceipt:
        if content is not None:
            content = TypeAdapter(MemoryContent).validate_python(content)
        async with (
            AsyncSession(self.engine, expire_on_commit=False) as session,
            session.begin(),
        ):
            repo = MemoryRepository(session)
            state = await repo.lock(user_id)
            if context is not None:
                chat = ChatRepository(session)
                await chat.thread(context.thread_id, user_id, lock=True)
                require_owner(
                    await chat.run(context.run_id, context.thread_id),
                    context.owner_token,
                )
                require_generation(state.generation, context.memory_generation)
                if context.user_id != user_id or not await repo.valid_source(
                    user_id,
                    context.thread_id,
                    context.run_id,
                    context.source_message_id,
                ):
                    raise DomainError(
                        409,
                        "INVALID_MEMORY_SOURCE",
                        "Memory source must be the current user message",
                    )
            old = await repo.latest(user_id, memory_id) if memory_id else None
            if memory_id is not None and (old is None or not old.active):
                raise DomainError(404, "MEMORY_NOT_FOUND", "Active memory not found")
            if old is not None and old.revision != expected_revision:
                raise DomainError(
                    409, "MEMORY_REVISION_CONFLICT", "Reload memory before editing"
                )
            active = await repo.active(user_id)
            duplicate = next((m for m in active if m.content == content), None)
            if duplicate is not None and (old is None or duplicate.id == old.id):
                return MemoryReceipt(
                    changed=False,
                    generation=state.generation,
                    memory=MemoryView.model_validate(duplicate),
                )
            if duplicate is not None:
                raise DomainError(
                    409,
                    "MEMORY_DUPLICATE",
                    "That content already exists in another memory",
                )
            if old is None and content is None:
                raise DomainError(422, "INVALID_MEMORY", "Specify a memory to forget")
            if old is None and len(active) >= 8:
                raise DomainError(
                    409,
                    "MEMORY_CAPACITY",
                    "Eight active memories already exist; edit or forget one first",
                )
            if old is not None:
                old.active = False
                await session.flush()
            entry = MemoryRevision(
                id=old.id if old else uuid4(),
                revision=old.revision + 1 if old else 1,
                user_id=user_id,
                content=content if content is not None else "",
                active=content is not None,
                source_message_id=context.source_message_id if context else None,
            )
            await repo.add(entry)
            state.generation += 1
            if context is not None:
                run = await chat.run(context.run_id, context.thread_id)
                assert run is not None
                run.reset_history = True
            receipt = MemoryReceipt(
                changed=True,
                generation=state.generation,
                memory=MemoryView.model_validate(entry),
            )
        # Only advance the initiating run after commit; other runs remain fenced.
        if context is not None:
            context.memory_generation = receipt.generation
            context.reset_history = True
        return receipt
