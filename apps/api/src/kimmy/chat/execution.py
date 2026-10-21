import asyncio
import logging
from time import monotonic
from uuid import UUID

from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.errors import GraphRecursionError

from kimmy.agent.context import AgentContext
from kimmy.agent.factory import AgentGraph, build_agent
from kimmy.agent.tools import fleet_tools
from kimmy.chat.service import ChatService
from kimmy.config import Settings
from kimmy.llm import ModelConfigurationError, chat_model

logger = logging.getLogger(__name__)

EMPTY_CHECKPOINT = "00000000-0000-0000-0000-000000000000"


class InvalidAgentResult(ValueError):
    pass


async def stream_answer(
    agent: AgentGraph,
    service: ChatService,
    context: AgentContext,
    content: str,
    parent_checkpoint: str | None,
    settings: Settings,
) -> tuple[str, str]:
    config: RunnableConfig = {
        "configurable": {
            "thread_id": str(context.thread_id),
            "checkpoint_id": parent_checkpoint or EMPTY_CHECKPOINT,
        },
        "recursion_limit": settings.agent_max_model_calls * 4 + 10,
        "metadata": {"run_id": str(context.run_id)},
    }
    if parent_checkpoint:
        previous = await agent.aget_state(config)
        if not previous.values or previous.next:
            raise InvalidAgentResult("Successful checkpoint is missing or unfinished")

    pending = ""
    pending_id: str | None = None
    flushed_at = monotonic()
    final: AIMessage | None = None

    async def flush() -> None:
        nonlocal pending, flushed_at
        if pending:
            await service.progress(
                context,
                "agent.text_delta",
                {
                    "model_message_id": pending_id,
                    "text": pending,
                },
            )
            pending = ""
            flushed_at = monotonic()

    async for part in agent.astream(
        {
            "messages": [
                HumanMessage(content=content, id=str(context.source_message_id))
            ]
        },
        config,
        context=context,
        stream_mode=["messages", "updates"],
        durability="sync",
        version="v2",
    ):
        if part["type"] == "messages":
            chunk, metadata = part["data"]
            # Only public model text; do not expose reasoning or tool arguments.
            if (
                isinstance(chunk, AIMessageChunk)
                and metadata.get("langgraph_node") == "model"
            ):
                if pending_id != chunk.id:
                    await flush()
                    pending_id = chunk.id
                pending += chunk.text
                if len(pending) >= 256 or monotonic() - flushed_at >= 0.15:
                    await flush()
        elif part["type"] == "updates":
            for update in part["data"].values():
                if not isinstance(update, dict):
                    continue
                for message in update.get("messages", []):
                    if isinstance(message, AIMessage):
                        final = message
                        for call in message.tool_calls:
                            await service.progress(
                                context,
                                "tool.requested",
                                {
                                    "tool_call_id": call["id"],
                                    "name": call["name"],
                                },
                            )
                            logger.info(
                                "Tool requested run_id=%s tool_call_id=%s",
                                context.run_id,
                                call["id"],
                            )
                    elif isinstance(message, ToolMessage):
                        await service.progress(
                            context,
                            "tool.completed",
                            {
                                "tool_call_id": message.tool_call_id,
                                "name": message.name,
                                "status": message.status,
                            },
                        )
                        logger.info(
                            "Tool finished run_id=%s tool_call_id=%s",
                            context.run_id,
                            message.tool_call_id,
                        )
    await flush()
    if (
        final is None
        or final.tool_calls
        or final.invalid_tool_calls
        or not final.text.strip()
    ):
        raise InvalidAgentResult("Agent did not produce a final text answer")
    if final.response_metadata.get("finish_reason") in {"length", "content_filter"}:
        raise InvalidAgentResult("Provider did not finish the answer")
    latest = await agent.aget_state(
        {"configurable": {"thread_id": str(context.thread_id)}}
    )
    checkpoint_id = latest.config.get("configurable", {}).get("checkpoint_id")
    if latest.next or not isinstance(checkpoint_id, str):
        raise InvalidAgentResult("Final checkpoint is not complete")
    return final.text, checkpoint_id


class AgentExecutor:
    def __init__(
        self, settings: Settings, service: ChatService, saver: AsyncPostgresSaver
    ):
        self.settings = settings
        self.service = service
        self.saver = saver

    async def execute(self, thread_id: UUID, user_id: str, run_id: UUID) -> None:
        try:
            async with asyncio.timeout(self.settings.agent_timeout_seconds):
                context, content, parent = await self.service.execution_input(
                    thread_id, user_id, run_id
                )
                async with chat_model(self.settings) as model:
                    agent = build_agent(
                        model,
                        self.saver,
                        self.settings,
                        fleet_tools(self.service.engine),
                    )
                    answer, checkpoint_id = await stream_answer(
                        agent, self.service, context, content, parent, self.settings
                    )
                await self.service.complete(context, answer, checkpoint_id)
            logger.info("Chat run completed run_id=%s", run_id)
            return
        except ModelConfigurationError:
            code = "AGENT_NOT_CONFIGURED"
        except TimeoutError:
            code = "AGENT_TIMEOUT"
        except (
            ModelCallLimitExceededError,
            ToolCallLimitExceededError,
            GraphRecursionError,
        ):
            code = "AGENT_LIMIT_EXCEEDED"
        except InvalidAgentResult:
            code = "AGENT_INVALID_RESULT"
        except asyncio.CancelledError:
            # Graceful process cancellation; SIGKILL/crash recovery is KM-012.
            await self.service.fail(thread_id, user_id, run_id, "WORKER_INTERRUPTED")
            raise
        except Exception as error:
            # Provider exceptions can include request text or credentials. Log only
            # the type and app identity; persist a stable public error code.
            logger.warning(
                "Agent failed run_id=%s error_type=%s", run_id, type(error).__name__
            )
            code = "AGENT_EXECUTION_FAILED"
        await self.service.fail(thread_id, user_id, run_id, code)
        logger.info("Chat run failed run_id=%s code=%s", run_id, code)
