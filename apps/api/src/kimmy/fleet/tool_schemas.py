"""Validated contracts for read-only fleet analysis tools."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kimmy.fleet.schemas import (
    DowntimeReport,
    FuelReport,
    OperationReport,
    Period,
    RecordRef,
    TechnicalStatus,
)
from kimmy.schemas import FleetId


class SearchVehiclesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit_code: str | None = Field(default=None, min_length=1, max_length=20)
    depot_id: FleetId | None = Field(
        default=None,
        description=(
            "Only filter when the user explicitly requests a depot. Otherwise null; "
            "never infer this filter from the vehicle current depot."
        ),
    )
    technical_status: TechnicalStatus | None = None
    limit: int = Field(default=20, ge=1, le=50, strict=True)
    offset: int = Field(default=0, ge=0, le=10000, strict=True)


class VehiclePeriodInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit_code: str = Field(min_length=1, max_length=20)
    period: Period
    depot_id: FleetId | None = Field(
        default=None,
        description=(
            "Only filter when the user explicitly requests a depot. Otherwise null; "
            "never infer this filter from the vehicle current depot."
        ),
    )


class MaintenanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unit_code: str = Field(min_length=1, max_length=20)
    depot_id: FleetId | None = Field(
        default=None,
        description=(
            "Only filter when the user explicitly requests a depot. Otherwise null; "
            "never infer this filter from the vehicle current depot."
        ),
    )
    period: Period | None = Field(
        default=None,
        description="Optional opened_at filter; omit for all history and schedules",
    )


class FleetRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: FleetId
    vehicle_id: FleetId

    @field_validator(
        "id",
        "vehicle_id",
        "depot_id",
        "work_order_id",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def decimal_id(cls, value: object) -> object:
        return str(value) if isinstance(value, int) else value


class TripView(FleetRecord):
    depot_id: FleetId
    trip_number: str
    origin: str
    destination: str
    actual_departure_at: datetime | None
    actual_arrival_at: datetime | None
    status: str
    start_odometer_km: Decimal
    end_odometer_km: Decimal | None
    distance_km: Decimal | None = None


class SessionView(FleetRecord):
    depot_id: FleetId
    started_at: datetime
    ended_at: datetime | None
    engine_on_seconds: int | None
    idle_seconds: int | None
    coverage_status: str


class FuelView(FleetRecord):
    depot_id: FleetId
    occurred_at: datetime
    recorded_at: datetime
    liters: Decimal
    unit_price_idr: Decimal
    odometer_km: Decimal | None
    fill_type: str
    meter_valid: bool
    reset_baseline: bool


class MaintenanceView(FleetRecord):
    work_order_number: str
    type: str
    status: str
    opened_at: datetime
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    due_at: datetime | None
    service_odometer_km: Decimal | None
    due_odometer_km: Decimal | None
    total_cost_idr: Decimal | None


class BreakdownView(FleetRecord):
    reported_at: datetime
    recorded_at: datetime
    out_of_service_at: datetime
    returned_to_service_at: datetime | None
    component: str
    symptom: str
    confirmed_cause: str | None
    severity: str
    work_order_id: FleetId | None


class VehicleSummary(BaseModel):
    vehicle_id: FleetId
    unit_code: str
    plate_number: str
    current_vehicle_depot: FleetId
    depot_code: str
    depot_name: str
    depot_timezone: str
    technical_status: TechnicalStatus
    status_as_of: datetime


class SearchData(BaseModel):
    vehicles: list[VehicleSummary]
    next_offset: int | None


class ActivityData(BaseModel):
    vehicle: VehicleSummary
    trips: list[TripView]
    sessions: list[SessionView]
    operations: OperationReport


class FuelData(BaseModel):
    vehicle: VehicleSummary
    entries: list[FuelView]
    analysis: FuelReport


class MaintenanceData(BaseModel):
    vehicle: VehicleSummary
    orders: list[MaintenanceView]
    historical_depot_available: Literal[False] = False


class BreakdownData(BaseModel):
    vehicle: VehicleSummary
    events: list[BreakdownView]
    downtime: DowntimeReport
    historical_depot_available: Literal[False] = False


class ToolResult[T: BaseModel](BaseModel):
    status: Literal["OK", "NO_DATA"]
    method: str
    record_refs: list[RecordRef]
    observed_period: Period | None
    coverage: list[str]
    depot_filter_basis: Literal["snapshot_depot", "current_vehicle_depot"]
    depot_filter: FleetId | None
    data: T


class ToolFailure(BaseModel):
    status: Literal["ERROR"] = "ERROR"
    code: Literal[
        "INVALID_INPUT", "VEHICLE_NOT_FOUND", "SERVICE_UNAVAILABLE", "RESULT_TOO_LARGE"
    ]
    message: str
