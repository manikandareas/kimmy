from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from kimmy.agent.context import AgentContext
from kimmy.agent.tools.common import execute, invalid_input
from kimmy.fleet.analysis import FleetAnalysisService
from kimmy.fleet.tool_schemas import MaintenanceInput


def build_tool(service: FleetAnalysisService) -> BaseTool:
    @tool
    async def get_maintenance_history(
        request: MaintenanceInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Read all work-order history and schedules for one exact unit_code, or
        optionally filter opened_at by [start,end). Costs are recorded WO
        costs. Depot filter means current_vehicle_depot; historical depot
        attribution is unavailable."""
        return await execute(lambda: service.get_maintenance_history(request), runtime)

    get_maintenance_history.handle_validation_error = invalid_input
    get_maintenance_history.handle_tool_error = True
    return get_maintenance_history
