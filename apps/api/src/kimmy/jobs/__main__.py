import asyncio
import logging

from kimmy.chat.service import ChatService
from kimmy.config import get_settings
from kimmy.database import create_engine
from kimmy.jobs.queue import CHAT_QUEUE, create_queue
from kimmy.jobs.tasks import register_tasks


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    queue = create_queue(settings)
    register_tasks(queue, ChatService(engine, queue))
    try:
        async with queue.open_async():
            await queue.run_worker_async(queues=[CHAT_QUEUE], concurrency=4)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
