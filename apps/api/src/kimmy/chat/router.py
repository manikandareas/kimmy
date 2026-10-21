from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse

from kimmy.chat.schemas import (
    Admission,
    CreateThread,
    Cursor,
    EventPage,
    RunView,
    SendMessage,
    Snapshot,
    ThreadPage,
    ThreadView,
)
from kimmy.chat.service import ChatService
from kimmy.chat.stream import stream_events
from kimmy.dependencies import DemoIdentity, get_demo_identity
from kimmy.errors import DomainError, ErrorResponse

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
Identity = Annotated[DemoIdentity, Depends(get_demo_identity)]


def get_chat_service(request: Request) -> ChatService:
    return ChatService(request.app.state.engine, request.app.state.queue)


Service = Annotated[ChatService, Depends(get_chat_service)]


def parse_cursor(value: str) -> int:
    if (
        not value.isascii()
        or not value.isdecimal()
        or len(value) > 19
        or (len(value) > 1 and value.startswith("0"))
        or int(value) > 9223372036854775807
    ):
        raise DomainError(
            422, "INVALID_CURSOR", "Cursor must be a nonnegative bigint decimal string"
        )
    return int(value)


@router.post("/threads", status_code=201)
async def create_thread(
    body: CreateThread, identity: Identity, service: Service
) -> ThreadView:
    return await service.create_thread(identity.user_id, body.title)


@router.get("/threads")
async def list_threads(
    identity: Identity,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> ThreadPage:
    return await service.list_threads(identity.user_id, limit, offset)


@router.post("/threads/{thread_id}/messages", status_code=202)
async def send_message(
    thread_id: UUID, body: SendMessage, identity: Identity, service: Service
) -> Admission:
    return await service.admit(thread_id, identity.user_id, body)


@router.get("/threads/{thread_id}/snapshot")
async def snapshot(
    thread_id: UUID,
    identity: Identity,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    before_seq: Cursor | None = None,
) -> Snapshot:
    return await service.snapshot(
        thread_id,
        identity.user_id,
        limit,
        parse_cursor(before_seq) if before_seq is not None else None,
    )


@router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(
    thread_id: UUID, run_id: UUID, identity: Identity, service: Service
) -> RunView:
    return await service.get_run(thread_id, identity.user_id, run_id)


@router.get("/threads/{thread_id}/events")
async def events(
    thread_id: UUID,
    identity: Identity,
    service: Service,
    after_seq: Cursor = "0",
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> EventPage:
    return await service.events(
        thread_id, identity.user_id, parse_cursor(after_seq), limit
    )


@router.get(
    "/threads/{thread_id}/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "Persisted events; SSE id is the per-thread sequence",
        }
    },
)
async def stream(
    request: Request,
    thread_id: UUID,
    identity: Identity,
    service: Service,
    after_seq: Cursor = "0",
    last_event_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    # EventSource sends Last-Event-ID on reconnect while its URL stays unchanged.
    cursor = parse_cursor(last_event_id if last_event_id is not None else after_seq)
    page = await service.events(thread_id, identity.user_id, cursor)
    return StreamingResponse(
        stream_events(request, service, thread_id, identity.user_id, page),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
