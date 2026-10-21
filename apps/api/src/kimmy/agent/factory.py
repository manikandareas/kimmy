from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    InputAgentState,
    OutputAgentState,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph

from kimmy.agent.context import AgentContext
from kimmy.agent.memory import MemoryMiddleware
from kimmy.config import Settings
from kimmy.memory.service import MemoryService

AgentGraph = CompiledStateGraph[
    AgentState[object], AgentContext, InputAgentState, OutputAgentState[object]
]


def build_agent(
    model: BaseChatModel,
    checkpointer: AsyncPostgresSaver,
    settings: Settings,
    tools: Sequence[BaseTool] = (),
    memory: MemoryService | None = None,
) -> AgentGraph:
    middleware: list[AgentMiddleware[Any, AgentContext]] = [
        ModelCallLimitMiddleware(
            run_limit=settings.agent_max_model_calls, exit_behavior="error"
        ),
        ToolCallLimitMiddleware(
            run_limit=settings.agent_max_tool_calls, exit_behavior="error"
        ),
    ]
    if memory is not None:
        middleware.append(MemoryMiddleware(memory))
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=Path(__file__).with_name("prompt.md").read_text(),
        context_schema=AgentContext,
        checkpointer=checkpointer,
        middleware=middleware,
        name="kimmy",
    )
