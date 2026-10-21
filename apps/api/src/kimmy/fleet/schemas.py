from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, model_validator

from kimmy.schemas import FleetId


class Period(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self) -> "Period":
        if self.start >= self.end:
            raise ValueError("Period must have start < end")
        return self

    def contains(self, instant: datetime) -> bool:
        return self.start <= instant < self.end


class RecordRef(BaseModel):
    table: str
    id: FleetId


class Observation(BaseModel):
    record_ref: RecordRef
    reasons: list[str]
    engine_on_seconds: int | None = None


class FuelInterval(BaseModel):
    vehicle_id: FleetId
    observed_period: Period
    record_refs: list[RecordRef]
    depot_ids: list[FleetId]
    liters: Decimal
    distance_km: Decimal
    liters_per_100_km: Decimal


class FuelReport(BaseModel):
    method: str = "full_to_full; assumes all interval refills recorded"
    observed_period: Period
    record_refs: list[RecordRef]
    coverage: list[Observation]
    spending_idr: Decimal
    intervals: list[FuelInterval]
    liters_per_100_km: Decimal | None
    late_record_refs: list[RecordRef]


class OperationReport(BaseModel):
    method: str = "closed complete sessions wholly within period; no prorating"
    observed_period: Period
    record_refs: list[RecordRef]
    coverage: list[Observation]
    complete_engine_on_seconds: int | None
    complete_idle_seconds: int | None
    all_selected_sessions_complete: bool


class DowntimeReport(BaseModel):
    method: str = "union of out-of-service intervals clipped to period and as_of"
    observed_period: Period
    record_refs: list[RecordRef]
    seconds: Decimal


TechnicalStatus = Literal[
    "breakdown", "maintenance", "maintenance_pending", "operational"
]


class TripObservation(BaseModel):
    record_ref: RecordRef
    depot_id: FleetId
    distance_km: Decimal | None


class FleetReport(BaseModel):
    vehicle_id: FleetId
    unit_code: str
    current_vehicle_depot: FleetId
    snapshot_depot_filter: FleetId | None
    observed_period: Period
    status_as_of: datetime
    technical_status: TechnicalStatus
    fuel: FuelReport
    operations: OperationReport
    trips: list[TripObservation]
    downtime: DowntimeReport
    breakdown_record_refs: list[RecordRef]
    maintenance_record_refs: list[RecordRef]
    historical_depot_available_for_maintenance_breakdown: bool = False
