import asyncio
import logging
from contextlib import suppress
from uuid import UUID

import procrastinate

from kimmy.chat.execution import AgentExecutor
from kimmy.chat.service import ChatService
from kimmy.jobs.queue import CHAT_QUEUE, CHAT_TASK

logger = logging.getLogger(__name__)


def register_tasks(
    queue: procrastinate.App, service: ChatService, executor: AgentExecutor
) -> None:
    @queue.task(name=CHAT_TASK, queue=CHAT_QUEUE, retry=False)
    async def execute_chat(run_id: str, thread_id: str, user_id: str) -> None:
        run, thread = UUID(run_id), UUID(thread_id)
        token = await service.claim(thread, user_id, run)
        if token is None:
            return
        logger.info("Chat run claimed run_id=%s", run)
        work = asyncio.create_task(executor.execute(thread, user_id, run, token))

        async def heartbeat() -> None:
            try:
                while True:
                    await asyncio.sleep(5)
                    await service.heartbeat(thread, user_id, run, token)
            except Exception:
                work.cancel()

        pulse = asyncio.create_task(heartbeat())
        try:
            await work
        finally:
            pulse.cancel()
            with suppress(asyncio.CancelledError):
                await pulse
