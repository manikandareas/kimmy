from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from kimmy.dependencies import DemoIdentity, get_demo_identity
from kimmy.memory.schemas import (
    MemoryCreate,
    MemoryForget,
    MemoryProfile,
    MemoryReceipt,
    MemoryUpdate,
)
from kimmy.memory.service import MemoryService

router = APIRouter(prefix="/api/memories", tags=["memory"])
Identity = Annotated[DemoIdentity, Depends(get_demo_identity)]


def get_service(request: Request) -> MemoryService:
    return MemoryService(request.app.state.engine)


Service = Annotated[MemoryService, Depends(get_service)]


@router.get("")
async def list_memories(identity: Identity, service: Service) -> MemoryProfile:
    return await service.profile(identity.user_id)


@router.post("", status_code=201)
async def create_memory(
    body: MemoryCreate, identity: Identity, service: Service
) -> MemoryReceipt:
    return await service.write(identity.user_id, body.content)


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: UUID, body: MemoryUpdate, identity: Identity, service: Service
) -> MemoryReceipt:
    return await service.write(
        identity.user_id, body.content, memory_id, body.expected_revision
    )


@router.post("/{memory_id}/forget")
async def forget_memory(
    memory_id: UUID, body: MemoryForget, identity: Identity, service: Service
) -> MemoryReceipt:
    return await service.write(
        identity.user_id, None, memory_id, body.expected_revision
    )
