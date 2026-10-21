from datetime import UTC, datetime

from kimmy.fleet.metrics import (
    downtime_report,
    fuel_report,
    operation_report,
    ref,
    technical_status,
    trip_distance,
)
from kimmy.fleet.repository import FleetRepository
from kimmy.fleet.schemas import FleetReport, Period, TripObservation


class FleetService:
    def __init__(self, repository: FleetRepository) -> None:
        self.repository = repository

    async def report(
        self,
        unit_code: str,
        period: Period,
        depot_id: int | None = None,
        as_of: datetime | None = None,
    ) -> FleetReport:
        vehicle = await self.repository.vehicle_by_code(unit_code)
        if vehicle is None:
            raise ValueError(f"Unknown vehicle: {unit_code}")
        now = as_of or datetime.now(UTC)
        fuel = await self.repository.fuel(vehicle.id, period)
        sessions = await self.repository.operations(vehicle.id, period)
        trips = await self.repository.trips(vehicle.id, period)
        breakdowns = await self.repository.breakdowns(vehicle.id)
        orders = await self.repository.orders(vehicle.id)
        return FleetReport(
            vehicle_id=str(vehicle.id),
            unit_code=vehicle.unit_code,
            current_vehicle_depot=str(vehicle.depot_id),
            snapshot_depot_filter=str(depot_id) if depot_id is not None else None,
            observed_period=period,
            status_as_of=now,
            technical_status=technical_status(breakdowns, orders, now),
            fuel=fuel_report(fuel, period, depot_id),
            operations=operation_report(sessions, period, depot_id),
            trips=[
                TripObservation(
                    record_ref=ref("trips", trip.id),
                    depot_id=str(trip.depot_id),
                    distance_km=trip_distance(trip),
                )
                for trip in trips
                if depot_id is None or trip.depot_id == depot_id
            ],
            # These sections are explicitly per-unit, never historical depot reports.
            downtime=downtime_report(breakdowns, period, now),
            breakdown_record_refs=[
                ref("breakdown_events", row.id)
                for row in breakdowns
                if period.contains(row.reported_at)
            ],
            maintenance_record_refs=[
                ref("maintenance_work_orders", row.id) for row in orders
            ],
        )
