"""Shared tool boundary: bounded execution and safe, structured errors."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from langchain.tools import ToolRuntime
from langchain_core.tools import ToolException
from pydantic import BaseModel, ValidationError
from pydantic.v1 import ValidationError as ValidationErrorV1

from kimmy.agent.context import AgentContext
from kimmy.fleet.analysis import FleetQueryError
from kimmy.fleet.tool_schemas import ToolFailure

logger = logging.getLogger(__name__)


def invalid_input(error: ValidationError | ValidationErrorV1) -> str:
    # Do not echo raw inputs or arbitrary exception messages to the model/logs.
    fields = ", ".join(".".join(map(str, item["loc"])) for item in error.errors())
    return ToolFailure(
        code="INVALID_INPUT",
        message=(
            f"Invalid tool input at: {fields}. "
            "Follow the input schema; dates require a timezone and start < end."
        ),
    ).model_dump_json()


async def execute[T: BaseModel](
    operation: Callable[[], Awaitable[T]],
    runtime: ToolRuntime[AgentContext],
) -> str:
    try:
        async with asyncio.timeout(15):
            result = await operation()
        logger.info(
            "Fleet tool finished run_id=%s tool_call_id=%s",
            runtime.context.run_id,
            runtime.tool_call_id,
        )
        return result.model_dump_json()
    except FleetQueryError as error:
        failure = error.failure
    except Exception as error:
        logger.warning(
            "Fleet tool failed run_id=%s tool_call_id=%s error_type=%s",
            runtime.context.run_id,
            runtime.tool_call_id,
            type(error).__name__,
        )
        failure = ToolFailure(
            code="SERVICE_UNAVAILABLE",
            message="Fleet analysis unavailable. No result produced; retry later.",
        )
    raise ToolException(failure.model_dump_json())
