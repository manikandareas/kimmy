"""Checkpoint writes share the ownership transaction, including pending writes."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import ChannelVersions, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection

from kimmy.agent.context import AgentContext
from kimmy.chat.models import Run
from kimmy.chat.ownership import require_owner
from kimmy.chat.service import ChatService
from kimmy.memory.repository import MemoryRepository
from kimmy.memory.service import require_generation


class FencedCheckpoints(AsyncPostgresSaver):
    def __init__(
        self, saver: AsyncPostgresSaver, service: ChatService, context: AgentContext
    ):
        super().__init__(saver.conn, serde=saver.serde)
        self.service = service
        self.context = context
        self.latest_id: str | None = None

    @asynccontextmanager
    async def writer(self) -> AsyncIterator[tuple[AsyncPostgresSaver, Run]]:
        context = self.context
        async with self.service.repository() as repo:
            state = await MemoryRepository(repo.session).lock(context.user_id)
            require_generation(state.generation, context.memory_generation)
            await self.service.require_thread(
                repo, context.thread_id, context.user_id, lock=True
            )
            run = await repo.run(context.run_id, context.thread_id)
            require_owner(run, context.owner_token)
            assert run is not None
            connection = await repo.session.connection()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            assert isinstance(driver, AsyncConnection)
            yield AsyncPostgresSaver(driver, serde=self.serde), run

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        async with self.writer() as (saver, run):
            result = await saver.aput(config, checkpoint, metadata, new_versions)
            run.resume_checkpoint_id = checkpoint["id"]
            run.memory_generation = self.context.memory_generation
        self.latest_id = checkpoint["id"]
        return result

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        async with self.writer() as (saver, _):
            await saver.aput_writes(config, writes, task_id, task_path)
