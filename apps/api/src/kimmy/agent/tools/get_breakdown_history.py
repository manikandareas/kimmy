from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from kimmy.agent.context import AgentContext
from kimmy.agent.tools.common import execute, invalid_input
from kimmy.fleet.analysis import FleetAnalysisService
from kimmy.fleet.tool_schemas import VehiclePeriodInput


def build_tool(service: FleetAnalysisService) -> BaseTool:
    @tool
    async def get_breakdown_history(
        request: VehiclePeriodInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Read breakdown history by reported_at and union downtime intersecting
        [start,end) for one exact unit_code. Open downtime ends at current
        time. Depot filter means current_vehicle_depot, never historical
        depot. Unknown cause is not a confirmed diagnosis."""
        return await execute(lambda: service.get_breakdown_history(request), runtime)

    get_breakdown_history.handle_validation_error = invalid_input
    get_breakdown_history.handle_tool_error = True
    return get_breakdown_history
