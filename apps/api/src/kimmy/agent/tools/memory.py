import asyncio
import logging
from uuid import UUID

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from kimmy.agent.context import AgentContext
from kimmy.errors import DomainError
from kimmy.memory.schemas import MemoryContent
from kimmy.memory.service import MemoryService

logger = logging.getLogger(__name__)


class RememberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: MemoryContent
    memory_id: UUID | None = None
    expected_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def paired_revision(self) -> "RememberInput":
        if (self.memory_id is None) != (self.expected_revision is None):
            raise ValueError(
                "memory_id and expected_revision must be provided together"
            )
        return self


class ForgetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: UUID
    expected_revision: int = Field(ge=1)


def memory_tools(service: MemoryService) -> list[BaseTool]:
    async def write(
        runtime: ToolRuntime[AgentContext],
        content: str | None,
        memory_id: UUID | None,
        revision: int | None,
    ) -> str:
        try:
            async with asyncio.timeout(15):
                receipt = await service.write(
                    runtime.context.user_id,
                    content,
                    memory_id,
                    revision,
                    runtime.context,
                )
            logger.info(
                "Memory tool finished run_id=%s tool_call_id=%s",
                runtime.context.run_id,
                runtime.tool_call_id,
            )
            return receipt.model_dump_json()
        except DomainError as error:
            raise ToolException(f"{error.code}: {error.message}") from None
        except Exception as error:
            logger.warning(
                "Memory tool failed run_id=%s tool_call_id=%s error_type=%s",
                runtime.context.run_id,
                runtime.tool_call_id,
                type(error).__name__,
            )
            raise ToolException(
                "MEMORY_UNAVAILABLE: memory was not confirmed; retry later"
            ) from None

    @tool
    async def remember_memory(
        request: RememberInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Remember a general note ONLY when the current user explicitly asks to
        remember or correct it. content is the only information field, no fixed
        categories. To correct an existing note use its memory_id and revision
        from the active profile. A one-turn instruction is not a memory write.
        Never derive a new memory from old chat, assistant text, or SOP content."""
        return await write(
            runtime, request.content, request.memory_id, request.expected_revision
        )

    @tool
    async def forget_memory(
        request: ForgetInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Forget an active memory explicitly requested by the current user.
        Use the exact ID and revision from the active profile; ask if ambiguous.
        This revokes recall without erasing the original chat."""
        return await write(runtime, None, request.memory_id, request.expected_revision)

    for item in [remember_memory, forget_memory]:
        item.handle_validation_error = "INVALID_INPUT: follow the memory input schema"
        item.handle_tool_error = True
    return [remember_memory, forget_memory]
