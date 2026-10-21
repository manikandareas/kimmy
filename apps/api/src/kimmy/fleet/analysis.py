"""Read-only domain services exposed by the five fleet tools."""

from collections.abc import AsyncIterator, Sized
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.fleet.metrics import (
    downtime_report,
    fuel_report,
    operation_report,
    ref,
    technical_status,
    trip_distance,
)
from kimmy.fleet.models import Vehicle
from kimmy.fleet.repository import FleetRepository
from kimmy.fleet.schemas import RecordRef
from kimmy.fleet.tool_schemas import (
    ActivityData,
    BreakdownData,
    BreakdownView,
    FuelData,
    FuelView,
    MaintenanceData,
    MaintenanceInput,
    MaintenanceView,
    SearchData,
    SearchVehiclesInput,
    SessionView,
    ToolFailure,
    ToolResult,
    TripView,
    VehiclePeriodInput,
    VehicleSummary,
)

MAX_RECORDS = 200


class FleetQueryError(Exception):
    def __init__(self, failure: ToolFailure):
        self.failure = failure
        super().__init__(failure.message)


def require_bounded(*rows: Sized) -> None:
    if sum(len(items) for items in rows) > MAX_RECORDS:
        raise FleetQueryError(
            ToolFailure(
                code="RESULT_TOO_LARGE",
                message=(
                    "More than 200 source records. Narrow the period or filter; no "
                    "partial aggregate was returned."
                ),
            )
        )


class FleetAnalysisService:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    @asynccontextmanager
    async def repository(self, depot_id: str | None) -> AsyncIterator[FleetRepository]:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            async with session.begin():
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                repository = FleetRepository(session)
                if (
                    depot_id is not None
                    and await repository.depot(int(depot_id)) is None
                ):
                    raise FleetQueryError(
                        ToolFailure(
                            code="INVALID_INPUT",
                            message="Unknown depot_id. Use search_vehicles.",
                        )
                    )
                yield repository

    async def vehicle(self, repo: FleetRepository, unit_code: str) -> Vehicle:
        vehicle = await repo.vehicle_by_code(unit_code.strip().upper())
        if vehicle is None:
            raise FleetQueryError(
                ToolFailure(
                    code="VEHICLE_NOT_FOUND",
                    message="Vehicle not found. Use search_vehicles.",
                )
            )
        return vehicle

    async def summary(
        self, repo: FleetRepository, vehicle: Vehicle, now: datetime
    ) -> tuple[VehicleSummary, list[RecordRef]]:
        events, orders = await repo.status_records(vehicle.id, now, MAX_RECORDS + 1)
        require_bounded(events, orders)
        depot = await repo.depot(vehicle.depot_id)
        assert depot is not None
        evidence = [ref("vehicles", vehicle.id), ref("depots", depot.id)]
        evidence.extend(
            ref("breakdown_events", e.id)
            for e in events
            if e.out_of_service_at <= now
            and (e.returned_to_service_at is None or now < e.returned_to_service_at)
        )
        evidence.extend(
            ref("maintenance_work_orders", o.id)
            for o in orders
            if o.status in {"in_progress", "open", "scheduled"}
        )
        return VehicleSummary(
            vehicle_id=str(vehicle.id),
            unit_code=vehicle.unit_code,
            plate_number=vehicle.plate_number,
            current_vehicle_depot=str(vehicle.depot_id),
            depot_code=depot.code,
            depot_name=depot.name,
            depot_timezone=depot.timezone,
            technical_status=technical_status(events, orders, now),
            status_as_of=now,
        ), evidence

    async def search_vehicles(
        self, request: SearchVehiclesInput
    ) -> ToolResult[SearchData]:
        now = datetime.now(UTC)
        async with self.repository(request.depot_id) as repo:
            rows = await repo.search_vehicles(
                request.unit_code,
                int(request.depot_id) if request.depot_id else None,
                request.technical_status,
                now,
                request.limit + 1,
                request.offset,
            )
            vehicles, refs = [], []
            for row in rows[: request.limit]:
                summary, evidence = await self.summary(repo, row, now)
                vehicles.append(summary)
                refs.extend(evidence)
            return ToolResult(
                status="OK" if vehicles else "NO_DATA",
                method=(
                    "unit_code substring; current depot; breakdown > maintenance > "
                    "maintenance_pending > operational"
                ),
                record_refs=refs,
                observed_period=None,
                coverage=[
                    "Current dataset snapshot; not historical technical status.",
                    "Paginated candidates; next_offset indicates more matches.",
                ],
                depot_filter_basis="current_vehicle_depot",
                depot_filter=request.depot_id,
                data=SearchData(
                    vehicles=vehicles,
                    next_offset=request.offset + request.limit
                    if len(rows) > request.limit
                    else None,
                ),
            )

    async def get_vehicle_activity(
        self, request: VehiclePeriodInput
    ) -> ToolResult[ActivityData]:
        async with self.repository(request.depot_id) as repo:
            vehicle = await self.vehicle(repo, request.unit_code)
            summary, evidence = await self.summary(repo, vehicle, datetime.now(UTC))
            depot = int(request.depot_id) if request.depot_id else None
            trips = await repo.trips(
                vehicle.id, request.period, MAX_RECORDS + 1, depot_id=depot
            )
            sessions = await repo.operations(
                vehicle.id, request.period, MAX_RECORDS + 1, depot_id=depot
            )
            require_bounded(trips, sessions)
            operations = operation_report(sessions, request.period)
            views = [
                TripView.model_validate(t).model_copy(
                    update={"distance_km": trip_distance(t)}
                )
                for t in trips
            ]
            return ToolResult(
                status="OK" if trips or sessions else "NO_DATA",
                method=(
                    "[start,end): actual_departure_at for trips, started_at for "
                    "sessions; distance=end-start odometer; engine-on from sessions "
                    "only"
                ),
                record_refs=evidence
                + [ref("trips", t.id) for t in trips]
                + operations.record_refs,
                observed_period=request.period,
                coverage=[
                    "Planned trips without actual departure are excluded.",
                    (
                        "Null stays unavailable. See operations.coverage for partial, "
                        "none, open, and cross-period sessions."
                    ),
                ],
                depot_filter_basis="snapshot_depot",
                depot_filter=request.depot_id,
                data=ActivityData(
                    vehicle=summary,
                    trips=views,
                    sessions=[SessionView.model_validate(s) for s in sessions],
                    operations=operations,
                ),
            )

    async def analyze_fuel_consumption(
        self, request: VehiclePeriodInput
    ) -> ToolResult[FuelData]:
        async with self.repository(request.depot_id) as repo:
            vehicle = await self.vehicle(repo, request.unit_code)
            summary, evidence = await self.summary(repo, vehicle, datetime.now(UTC))
            entries = await repo.fuel(vehicle.id, request.period, MAX_RECORDS + 1)
            require_bounded(entries)
            depot = int(request.depot_id) if request.depot_id else None
            analysis = fuel_report(entries, request.period, depot)
            selected = [e for e in entries if depot is None or e.depot_id == depot]
            return ToolResult(
                status="OK" if selected else "NO_DATA",
                method=(
                    "SUM(liters * unit_price_idr) by occurred_at in [start,end); full-"
                    "to-full uses all intervening liters excluding baseline; reset "
                    "breaks interval"
                ),
                record_refs=evidence + analysis.record_refs,
                observed_period=request.period,
                coverage=[
                    (
                        "Efficiency is an estimate assuming all refills recorded; only "
                        "wholly contained intervals eligible."
                    ),
                    (
                        "fill_type_partial/unknown and meter_invalid describe boundary "
                        "eligibility, NOT excluded volume. volume_record_refs includes "
                        "every refill contributing liters; baseline_record_ref only "
                        "provides the starting odometer, not its liters."
                    ),
                    (
                        "Cross-depot intervals excluded for a depot filter. See "
                        "analysis.coverage for eligibility; late_record_refs for >24h "
                        "recording delay."
                    ),
                ],
                depot_filter_basis="snapshot_depot",
                depot_filter=request.depot_id,
                data=FuelData(
                    vehicle=summary,
                    entries=[FuelView.model_validate(e) for e in selected],
                    analysis=analysis,
                ),
            )

    async def get_maintenance_history(
        self, request: MaintenanceInput
    ) -> ToolResult[MaintenanceData]:
        async with self.repository(request.depot_id) as repo:
            vehicle = await self.vehicle(repo, request.unit_code)
            summary, evidence = await self.summary(repo, vehicle, datetime.now(UTC))
            orders = await repo.orders(
                vehicle.id, MAX_RECORDS + 1, period=request.period
            )
            require_bounded(orders)
            selected = [
                o
                for o in orders
                if (request.period is None or request.period.contains(o.opened_at))
                and (
                    request.depot_id is None
                    or str(vehicle.depot_id) == request.depot_id
                )
            ]
            return ToolResult(
                status="OK" if selected else "NO_DATA",
                method=(
                    "Per-unit WO history and schedule; optional [start,end) filter by "
                    "opened_at; total_cost_idr is recorded WO cost"
                ),
                record_refs=evidence
                + [ref("maintenance_work_orders", o.id) for o in selected],
                observed_period=request.period,
                coverage=[
                    (
                        "Historical depot attribution unavailable; depot filter uses "
                        "current_vehicle_depot."
                    ),
                    (
                        "No period means all history and schedules. Null cost/due"
                        " fields remain unavailable."
                    ),
                ],
                depot_filter_basis="current_vehicle_depot",
                depot_filter=request.depot_id,
                data=MaintenanceData(
                    vehicle=summary,
                    orders=[MaintenanceView.model_validate(o) for o in selected],
                ),
            )

    async def get_breakdown_history(
        self, request: VehiclePeriodInput
    ) -> ToolResult[BreakdownData]:
        now = datetime.now(UTC)
        async with self.repository(request.depot_id) as repo:
            vehicle = await self.vehicle(repo, request.unit_code)
            summary, evidence = await self.summary(repo, vehicle, now)
            events = await repo.breakdowns(
                vehicle.id, MAX_RECORDS + 1, period=request.period, as_of=now
            )
            require_bounded(events)
            if (
                request.depot_id is not None
                and str(vehicle.depot_id) != request.depot_id
            ):
                events = []
            selected = [e for e in events if request.period.contains(e.reported_at)]
            downtime = downtime_report(events, request.period, now)
            # Downtime can include events reported before the requested period.
            refs = {
                r.id: r
                for r in [
                    *[ref("breakdown_events", e.id) for e in selected],
                    *downtime.record_refs,
                ]
            }
            return ToolResult(
                status="OK" if refs else "NO_DATA",
                method=(
                    "History by reported_at in [start,end); downtime is union of out-"
                    "of-service intervals intersected with period and current time"
                ),
                record_refs=evidence + list(refs.values()),
                observed_period=request.period,
                coverage=[
                    (
                        "Historical depot attribution unavailable; depot filter uses "
                        "current_vehicle_depot."
                    ),
                    (
                        "Downtime can include events reported before the period. Open "
                        "events end at status_as_of; overlapping intervals counted"
                        " once. Null confirmed_cause is unknown."
                    ),
                ],
                depot_filter_basis="current_vehicle_depot",
                depot_filter=request.depot_id,
                data=BreakdownData(
                    vehicle=summary,
                    events=[BreakdownView.model_validate(e) for e in selected],
                    downtime=downtime,
                ),
            )
