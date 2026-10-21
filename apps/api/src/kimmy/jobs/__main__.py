import asyncio
import logging
from contextlib import suppress

from kimmy.agent.checkpoints import checkpoints
from kimmy.chat.execution import AgentExecutor
from kimmy.chat.service import ChatService
from kimmy.config import get_settings
from kimmy.database import create_engine
from kimmy.jobs.queue import CHAT_QUEUE, create_queue
from kimmy.jobs.tasks import register_tasks


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    queue = create_queue(settings)
    service = ChatService(engine, queue)
    try:
        async with checkpoints(settings) as saver:
            register_tasks(queue, service, AgentExecutor(settings, service, saver))
            async with queue.open_async():

                async def recover() -> None:
                    while True:
                        try:
                            await service.recover()
                        except Exception:
                            logging.getLogger(__name__).warning(
                                "Recovery scan failed; retrying"
                            )
                        await asyncio.sleep(5)

                recovery = asyncio.create_task(recover())
                try:
                    await queue.run_worker_async(queues=[CHAT_QUEUE], concurrency=4)
                finally:
                    recovery.cancel()
                    with suppress(asyncio.CancelledError):
                        await recovery
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
