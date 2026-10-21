from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from kimmy.agent.context import AgentContext
from kimmy.agent.tools.common import execute, invalid_input
from kimmy.fleet.analysis import FleetAnalysisService
from kimmy.fleet.tool_schemas import VehiclePeriodInput


def build_tool(service: FleetAnalysisService) -> BaseTool:
    @tool
    async def analyze_fuel_consumption(
        request: VehiclePeriodInput, runtime: ToolRuntime[AgentContext]
    ) -> str:
        """Analyze fuel spending and estimated full-to-full L/100 km for one
        exact unit_code and [start,end) period. Snapshot depot filter excludes
        cross-depot intervals; resets break intervals. Includes raw refills,
        coverage, and recording delays. Spending is not consumption."""
        return await execute(lambda: service.analyze_fuel_consumption(request), runtime)

    analyze_fuel_consumption.handle_validation_error = invalid_input
    analyze_fuel_consumption.handle_tool_error = True
    return analyze_fuel_consumption
