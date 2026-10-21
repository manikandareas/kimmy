from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from kimmy.chat.router import router as chat_router
from kimmy.config import get_settings
from kimmy.database import create_engine
from kimmy.dependencies import DemoIdentity, get_demo_identity
from kimmy.errors import ErrorResponse, register_error_handlers
from kimmy.jobs.queue import create_queue
from kimmy.knowledge.router import router as knowledge_router
from kimmy.memory.router import router as memory_router


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(get_settings())
    app.state.engine = engine
    app.state.queue = create_queue(get_settings())
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="Kimmy API",
    version="0.1.0",
    lifespan=lifespan,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
register_error_handlers(app)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(knowledge_router)


@app.get("/api/health/live")
async def live() -> HealthResponse:
    return HealthResponse()


@app.get("/api/health/ready", responses={503: {"model": ErrorResponse}})
async def ready(request: Request) -> HealthResponse:
    try:
        async with request.app.state.engine.connect() as connection:
            timezone = await connection.scalar(text("SHOW TIME ZONE"))
            if timezone != "UTC":
                raise HTTPException(503, "Database timezone is not UTC")
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    return HealthResponse()


@app.get("/api/me")
async def me(
    identity: Annotated[DemoIdentity, Depends(get_demo_identity)],
) -> DemoIdentity:
    return identity
