from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncEngine

from kimmy.agent.tools import (
    analyze_fuel_consumption,
    get_breakdown_history,
    get_maintenance_history,
    get_vehicle_activity,
    search_vehicles,
)
from kimmy.fleet.analysis import FleetAnalysisService


def fleet_tools(engine: AsyncEngine) -> list[BaseTool]:
    service = FleetAnalysisService(engine)
    return [
        module.build_tool(service)
        for module in (
            search_vehicles,
            get_vehicle_activity,
            analyze_fuel_consumption,
            get_maintenance_history,
            get_breakdown_history,
        )
    ]
