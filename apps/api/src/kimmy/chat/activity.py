"""Public activity projections; never expose checkpoints or model reasoning."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter

from kimmy.chat.models import Event, Run
from kimmy.fleet.tool_schemas import (
    ActivityData,
    BreakdownData,
    FuelData,
    MaintenanceData,
    SearchData,
    ToolFailure,
    ToolResult,
)

FleetResult = (
    ToolResult[SearchData]
    | ToolResult[ActivityData]
    | ToolResult[FuelData]
    | ToolResult[MaintenanceData]
    | ToolResult[BreakdownData]
    | ToolFailure
)
FLEET_RESULT: TypeAdapter[FleetResult] = TypeAdapter(FleetResult)
FLEET_TOOLS = frozenset(
    {
        "search_vehicles",
        "get_vehicle_activity",
        "analyze_fuel_consumption",
        "get_maintenance_history",
        "get_breakdown_history",
    }
)


class ToolActivity(BaseModel):
    tool_call_id: str
    name: str
    status: Literal["running", "success", "error"] = "running"
    result: FleetResult | None = None


class RunActivity(BaseModel):
    run_id: UUID
    message_id: UUID
    text: str = ""
    model_message_id: str | None = None
    tools: list[ToolActivity] = Field(default_factory=list)


def project_activity(runs: list[Run], events: list[Event]) -> list[RunActivity]:
    activities = {
        run.id: RunActivity(run_id=run.id, message_id=run.message_id) for run in runs
    }
    active_ids = {run.id for run in runs if run.status in {"queued", "running"}}
    for event in events:
        item = activities[event.run_id]
        if event.kind == "run.queued":
            item.text = ""
            item.model_message_id = None
            item.tools = []
        elif event.kind == "agent.text_delta" and event.run_id in active_ids:
            model_id = event.payload.get("model_message_id")
            if model_id != item.model_message_id:
                item.text = ""
                item.model_message_id = str(model_id) if model_id else None
            item.text += str(event.payload.get("text", ""))
        elif event.kind in {"tool.requested", "tool.completed"}:
            tool = ToolActivity.model_validate(event.payload)
            item.tools = [t for t in item.tools if t.tool_call_id != tool.tool_call_id]
            item.tools.append(tool)
    for item in activities.values():
        if item.run_id not in active_ids:
            for tool in item.tools:
                if tool.status == "running":
                    tool.status = "error"
    return list(activities.values())
