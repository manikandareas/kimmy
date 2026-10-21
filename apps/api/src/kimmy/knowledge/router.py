from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from kimmy.config import get_settings
from kimmy.dependencies import DemoIdentity, get_demo_identity
from kimmy.errors import ErrorResponse
from kimmy.knowledge.schemas import SourceChunk
from kimmy.knowledge.service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def get_service(request: Request) -> KnowledgeService:
    return KnowledgeService(request.app.state.engine, get_settings())


@router.get("/sources/{chunk_id}", responses={404: {"model": ErrorResponse}})
async def read_source(
    chunk_id: UUID,
    identity: Annotated[DemoIdentity, Depends(get_demo_identity)],
    service: Annotated[KnowledgeService, Depends(get_service)],
) -> SourceChunk:
    # The demo has one shared corpus; source reads require no embedding request.
    return await service.source(chunk_id)
