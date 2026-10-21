from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal

from kimmy.fleet.models import (
    BreakdownEvent,
    FuelEntry,
    MaintenanceWorkOrder,
    OperationSession,
    Trip,
)
from kimmy.fleet.schemas import (
    DowntimeReport,
    FuelInterval,
    FuelReport,
    Observation,
    OperationReport,
    Period,
    RecordRef,
    TechnicalStatus,
)


def ref(table: str, record_id: int) -> RecordRef:
    return RecordRef(table=table, id=str(record_id))


def trip_distance(trip: Trip) -> Decimal | None:
    if trip.end_odometer_km is None:
        return None
    return trip.end_odometer_km - trip.start_odometer_km


def fuel_report(
    entries: Sequence[FuelEntry], period: Period, depot_id: int | None = None
) -> FuelReport:
    """Inspect unfiltered depot records so cross-depot intervals cannot be bridged."""
    ordered = sorted(entries, key=lambda entry: (entry.occurred_at, entry.id))
    selected = [
        entry
        for entry in ordered
        if period.contains(entry.occurred_at)
        and (depot_id is None or entry.depot_id == depot_id)
    ]
    baselines: dict[int, FuelEntry] = {}
    pending: dict[int, list[FuelEntry]] = {}
    intervals: list[FuelInterval] = []
    coverage: list[Observation] = []
    used: set[int] = set()
    for entry in ordered:
        # Outside-period entries cannot establish an eligible interval baseline.
        if not period.contains(entry.occurred_at):
            continue
        vehicle = entry.vehicle_id
        boundary = (
            entry.fill_type == "full"
            and entry.meter_valid
            and entry.odometer_km is not None
        )
        reasons = []
        if entry.fill_type != "full":
            reasons.append(f"fill_type_{entry.fill_type}")
        if not entry.meter_valid:
            reasons.append("meter_invalid")
        if entry.odometer_km is None:
            reasons.append("odometer_unavailable")
        if entry.reset_baseline:
            baselines.pop(vehicle, None)
            pending.pop(vehicle, None)
            reasons.append("reset_baseline")
        baseline = baselines.get(vehicle)
        if baseline is not None:
            pending[vehicle].append(entry)
        if boundary:
            if baseline is not None:
                assert baseline.odometer_km is not None
                assert entry.odometer_km is not None
                records = [baseline, *pending[vehicle]]
                distance = entry.odometer_km - baseline.odometer_km
                if distance <= 0:
                    reasons.append("nonpositive_odometer_delta")
                elif entry.occurred_at <= baseline.occurred_at:
                    reasons.append("ambiguous_boundary_time")
                elif depot_id is not None and any(
                    row.depot_id != depot_id for row in records
                ):
                    reasons.append("cross_depot_interval")
                else:
                    liters = sum((row.liters for row in pending[vehicle]), Decimal(0))
                    intervals.append(
                        FuelInterval(
                            vehicle_id=str(vehicle),
                            observed_period=Period(
                                start=baseline.occurred_at, end=entry.occurred_at
                            ),
                            record_refs=[
                                ref("fuel_entries", row.id) for row in records
                            ],
                            depot_ids=[
                                str(value)
                                for value in sorted({row.depot_id for row in records})
                            ],
                            liters=liters,
                            distance_km=distance,
                            liters_per_100_km=liters / distance * 100,
                        )
                    )
                    used.update(row.id for row in records)
            else:
                reasons.append("baseline_only")
            baselines[vehicle] = entry
            pending[vehicle] = []
        if reasons and (depot_id is None or entry.depot_id == depot_id):
            coverage.append(
                Observation(record_ref=ref("fuel_entries", entry.id), reasons=reasons)
            )
    for entry in selected:
        if entry.id not in used:
            coverage.append(
                Observation(
                    record_ref=ref("fuel_entries", entry.id),
                    reasons=["not_in_eligible_interval"],
                )
            )
    distance = sum((item.distance_km for item in intervals), Decimal(0))
    liters = sum((item.liters for item in intervals), Decimal(0))
    return FuelReport(
        observed_period=period,
        record_refs=[ref("fuel_entries", entry.id) for entry in selected],
        coverage=coverage,
        spending_idr=sum(
            (entry.liters * entry.unit_price_idr for entry in selected), Decimal(0)
        ),
        intervals=intervals,
        liters_per_100_km=liters / distance * 100 if distance else None,
        late_record_refs=[
            ref("fuel_entries", entry.id)
            for entry in selected
            if entry.recorded_at - entry.occurred_at > timedelta(hours=24)
        ],
    )


def operation_report(
    sessions: Sequence[OperationSession], period: Period, depot_id: int | None = None
) -> OperationReport:
    selected = [
        row
        for row in sessions
        if period.contains(row.started_at)
        and (depot_id is None or row.depot_id == depot_id)
    ]
    eligible: list[OperationSession] = []
    coverage: list[Observation] = []
    for row in selected:
        reasons = []
        if row.ended_at is None:
            reasons.append("session_open")
        elif row.ended_at > period.end:
            reasons.append("crosses_period_end")
        if row.coverage_status != "complete":
            reasons.append(f"coverage_{row.coverage_status}")
        if row.engine_on_seconds is None:
            reasons.append("engine_on_unavailable")
        if reasons:
            coverage.append(
                Observation(
                    record_ref=ref("operation_sessions", row.id),
                    reasons=reasons,
                    engine_on_seconds=row.engine_on_seconds,
                )
            )
        else:
            eligible.append(row)
    return OperationReport(
        observed_period=period,
        record_refs=[ref("operation_sessions", row.id) for row in selected],
        coverage=coverage,
        complete_engine_on_seconds=(
            sum(
                row.engine_on_seconds
                for row in eligible
                if row.engine_on_seconds is not None
            )
            if eligible
            else None
        ),
        complete_idle_seconds=(
            sum(row.idle_seconds for row in eligible if row.idle_seconds is not None)
            if eligible and all(row.idle_seconds is not None for row in eligible)
            else None
        ),
        all_selected_sessions_complete=bool(selected) and not coverage,
    )


def downtime_report(
    events: Sequence[BreakdownEvent], period: Period, as_of: datetime
) -> DowntimeReport:
    if as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    # Union per vehicle: concurrent downtime on two vehicles is two vehicle-hours.
    by_vehicle: dict[int, list[tuple[datetime, datetime]]] = {}
    refs: list[RecordRef] = []
    for event in events:
        start = max(period.start, event.out_of_service_at)
        end = min(period.end, event.returned_to_service_at or as_of, as_of)
        if start < end:
            by_vehicle.setdefault(event.vehicle_id, []).append((start, end))
            refs.append(ref("breakdown_events", event.id))
    total = timedelta()
    for spans in by_vehicle.values():
        merged: list[tuple[datetime, datetime]] = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        total += sum((end - start for start, end in merged), timedelta())
    seconds = Decimal(total.days * 86400 + total.seconds)
    seconds += Decimal(total.microseconds) / 1_000_000
    return DowntimeReport(observed_period=period, record_refs=refs, seconds=seconds)


def technical_status(
    events: Sequence[BreakdownEvent],
    orders: Sequence[MaintenanceWorkOrder],
    as_of: datetime,
) -> TechnicalStatus:
    """Current dataset status for one vehicle, not reconstructed WO history."""
    if as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    if any(
        row.out_of_service_at <= as_of
        and (row.returned_to_service_at is None or as_of < row.returned_to_service_at)
        for row in events
    ):
        return "breakdown"
    if any(row.status == "in_progress" for row in orders):
        return "maintenance"
    if any(row.status in {"open", "scheduled"} for row in orders):
        return "maintenance_pending"
    return "operational"
