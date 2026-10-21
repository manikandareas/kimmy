from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from kimmy.agent.context import AgentContext
from kimmy.agent.tools.common import execute, invalid_input
from kimmy.fleet.analysis import FleetAnalysisService
from kimmy.fleet.tool_schemas import SearchVehiclesInput


def build_tool(service: FleetAnalysisService) -> BaseTool:
    @tool
    async def search_vehicles(
        request: SearchVehiclesInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Find vehicle candidates by unit_code substring, current depot, or
        computed current technical status. Returns depot IDs/names/timezones
        and paginated candidates; use exact unit_code from results for
        analysis. Depot is a report filter, not authorization."""
        return await execute(lambda: service.search_vehicles(request), runtime)

    search_vehicles.handle_validation_error = invalid_input
    search_vehicles.handle_tool_error = True
    return search_vehicles
