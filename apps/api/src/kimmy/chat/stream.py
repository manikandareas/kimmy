import asyncio
import logging
from collections.abc import AsyncIterator
from time import monotonic
from uuid import UUID

from fastapi import Request

from kimmy.chat.schemas import EventPage
from kimmy.chat.service import ChatService

logger = logging.getLogger(__name__)


async def stream_events(
    request: Request,
    service: ChatService,
    thread_id: UUID,
    user_id: str,
    first_page: EventPage,
) -> AsyncIterator[str]:
    """Read the ledger in short transactions; connections never execute work."""
    yield "retry: 2000\n\n"
    page = first_page
    heartbeat = monotonic()
    try:
        while not await request.is_disconnected():
            for event in page.events:
                yield (
                    f"id: {event.seq}\nevent: {event.kind}\n"
                    f"data: {event.model_dump_json()}\n\n"
                )
            if monotonic() - heartbeat >= 15:
                yield ": heartbeat\n\n"
                heartbeat = monotonic()
            if not page.has_more:
                await asyncio.sleep(0.2)
            page = await service.events(thread_id, user_id, int(page.next_after_seq))
    except asyncio.CancelledError:
        raise
    except Exception:
        # Do not include DB errors, SQL parameters, or user messages in SSE/logs.
        logger.warning("Chat event stream interrupted for thread %s", thread_id)
        yield 'event: stream.error\ndata: {"code":"STREAM_UNAVAILABLE"}\n\n'
