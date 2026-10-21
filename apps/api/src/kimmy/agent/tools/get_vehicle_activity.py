from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from kimmy.agent.context import AgentContext
from kimmy.agent.tools.common import execute, invalid_input
from kimmy.fleet.analysis import FleetAnalysisService
from kimmy.fleet.tool_schemas import VehiclePeriodInput


def build_tool(service: FleetAnalysisService) -> BaseTool:
    @tool
    async def get_vehicle_activity(
        request: VehiclePeriodInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Read trips and engine-on/idle sessions for one exact unit_code and
        timezone-aware [start,end) period. Depot uses event snapshots. Missing
        engine data stays null; trip duration never substitutes engine hours."""
        return await execute(lambda: service.get_vehicle_activity(request), runtime)

    get_vehicle_activity.handle_validation_error = invalid_input
    get_vehicle_activity.handle_tool_error = True
    return get_vehicle_activity
