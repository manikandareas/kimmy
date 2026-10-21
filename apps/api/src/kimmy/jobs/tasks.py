import logging
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
        if not await service.claim(thread, user_id, run):
            return
        logger.info("Chat run claimed run_id=%s", run)
        await executor.execute(thread, user_id, run)
