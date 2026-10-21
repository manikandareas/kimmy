from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.fleet.models import (
    Base,
    BreakdownEvent,
    Depot,
    FuelEntry,
    MaintenanceWorkOrder,
    OperationSession,
    Trip,
    Vehicle,
)

SEED_START = datetime(2026, 8, 22, tzinfo=UTC)
SEED_END = SEED_START + timedelta(days=60)
TRANSFER_AT = SEED_START + timedelta(days=30)


class SeedNotEmptyError(ValueError):
    """At least one fleet table contains data; nothing may be seeded."""


async def seed_fleet(engine: AsyncEngine) -> dict[str, int]:
    """Insert all records atomically, using database-returned identity keys."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            # Also serializes concurrent seed invocations and excludes other writers.
            names = ", ".join(sorted(Base.metadata.tables))
            await session.execute(text(f"LOCK TABLE {names} IN EXCLUSIVE MODE"))
            for table in Base.metadata.sorted_tables:
                if await session.scalar(select(exists().select_from(table))):
                    raise SeedNotEmptyError(
                        f"Seed refused: {table.name} already contains data; no changes."
                    )
            depots = [
                Depot(code="MKS", name="Makassar", timezone="Asia/Makassar"),
                Depot(code="PRE", name="Parepare", timezone="Asia/Makassar"),
            ]
            for depot in depots:
                ZoneInfo(depot.timezone)
            session.add_all(depots)
            await session.flush()
            for number in range(1, 13):
                current_depot = depots[1] if number == 1 or number > 6 else depots[0]
                vehicle = Vehicle(
                    depot_id=current_depot.id,
                    unit_code=f"KM-{number:03}",
                    plate_number=f"SIM-{number:03}",
                    vehicle_class="medium_truck",
                    fuel_type="diesel",
                    tank_capacity_liters=Decimal("300.0"),
                    max_payload_kg=8000,
                )
                session.add(vehicle)
                await session.flush()
                await seed_vehicle(session, vehicle, number, depots)
            await session.flush()
            counts = {}
            for table in Base.metadata.sorted_tables:
                counts[table.name] = int(
                    await session.scalar(select(func.count()).select_from(table)) or 0
                )
            return counts


async def seed_vehicle(
    session: AsyncSession, vehicle: Vehicle, number: int, depots: list[Depot]
) -> None:
    """Coherent odometer/fuel ledger with maintenance and breakdown pauses."""
    odometer = Decimal(100000 + (number - 1) * 10000 - 250)
    fuel_deficit = Decimal(0)
    for day in range(60):
        instant = SEED_START + timedelta(days=day)
        depot = (
            depots[0]
            if number == 1 and day < 30
            else (depots[1] if number == 1 or number > 6 else depots[0])
        )
        stopped = (number in {2, 3} and day == 59) or (number == 7 and day in {10, 11})
        if stopped:
            continue
        status = "completed"
        if day == 59 and number == 5:
            status = "planned"
        elif day == 59 and number == 6:
            status = "cancelled"
        elif day == 59 and number == 12:
            status = "in_progress"
        departure = instant + timedelta(hours=1)
        start_odometer = odometer
        if status in {"completed", "in_progress"}:
            odometer += 250
            fuel_deficit += 50
        session.add(
            Trip(
                trip_number=f"TR-{number:03}-{day:03}",
                vehicle_id=vehicle.id,
                depot_id=depot.id,
                origin=depot.name,
                destination="Gudang regional",
                planned_departure_at=departure - timedelta(minutes=15),
                actual_departure_at=(
                    departure if status in {"completed", "in_progress"} else None
                ),
                actual_arrival_at=(
                    departure + timedelta(hours=7) if status == "completed" else None
                ),
                start_odometer_km=start_odometer,
                end_odometer_km=odometer if status == "completed" else None,
                payload_kg=3000 + number * 200,
                status=status,
                recorded_at=departure + timedelta(minutes=5),
            )
        )
        if status in {"planned", "cancelled"}:
            continue
        coverage = "complete"
        if number == 2 and day in {5, 6}:
            coverage = "partial" if day == 5 else "none"
        session.add(
            OperationSession(
                vehicle_id=vehicle.id,
                depot_id=depot.id,
                started_at=departure,
                ended_at=(
                    departure + timedelta(hours=7) if status == "completed" else None
                ),
                engine_on_seconds=(
                    None
                    if coverage == "none"
                    else 10800
                    if coverage == "partial"
                    else 21600
                ),
                idle_seconds=None if coverage == "none" else 1800,
                coverage_status=coverage,
            )
        )
        # A running trip has no terminal odometer/refill yet.
        if status != "completed":
            continue
        fill_type = "full" if day % 2 == 0 else "partial"
        if number == 2 and day == 3:
            fill_type = "unknown"
        liters = fuel_deficit if fill_type == "full" else Decimal(40)
        fuel_deficit -= liters
        occurred = instant + timedelta(hours=9)
        session.add(
            FuelEntry(
                vehicle_id=vehicle.id,
                depot_id=depot.id,
                occurred_at=occurred,
                odometer_km=None if number == 2 and day == 4 else odometer,
                liters=liters,
                unit_price_idr=Decimal("10000.00"),
                fill_type=fill_type,
                meter_valid=not (number == 2 and day in {6, 7}),
                reset_baseline=number == 2 and day in {20, 25},
                recorded_at=occurred
                + timedelta(hours=30 if number == 1 and day == 12 else 1),
            )
        )
    order_status = {
        2: "open",
        3: "in_progress",
        4: "scheduled",
        7: "completed",
        8: "cancelled",
    }.get(number)
    order = None
    if order_status:
        historical = order_status in {"completed", "cancelled"}
        opened = SEED_START + timedelta(days=9 if historical else 59)
        order = MaintenanceWorkOrder(
            work_order_number=f"WO-{number:03}",
            vehicle_id=vehicle.id,
            type="corrective" if number in {2, 7} else "preventive",
            status=order_status,
            opened_at=opened,
            scheduled_at=opened + timedelta(days=1)
            if number == 7
            else opened + timedelta(hours=1),
            started_at=(
                (
                    opened + timedelta(days=1)
                    if number == 7
                    else opened + timedelta(hours=2)
                )
                if order_status in {"in_progress", "completed"}
                else None
            ),
            completed_at=(
                SEED_START + timedelta(days=12) if order_status == "completed" else None
            ),
            service_odometer_km=(
                Decimal(160000 + 9 * 250) if number == 7 else odometer
            ),
            due_at=opened + timedelta(days=2),
            due_odometer_km=odometer + 500,
            total_cost_idr=Decimal("1500000.00") if historical else None,
        )
        session.add(order)
        await session.flush()
    if number in {2, 7}:
        assert order is not None and order.vehicle_id == vehicle.id
        start = SEED_START + timedelta(days=59 if number == 2 else 10)
        session.add(
            BreakdownEvent(
                vehicle_id=vehicle.id,
                reported_at=start + timedelta(minutes=10),
                out_of_service_at=start,
                returned_to_service_at=(
                    None if number == 2 else start + timedelta(days=2)
                ),
                component="cooling",
                symptom="Suhu mesin tinggi",
                confirmed_cause=None if number == 2 else "Kebocoran selang radiator",
                severity="high",
                work_order_id=order.id,
                recorded_at=start + timedelta(minutes=20),
            )
        )
        if number == 7:
            session.add(
                BreakdownEvent(
                    vehicle_id=vehicle.id,
                    reported_at=start + timedelta(hours=2),
                    out_of_service_at=start + timedelta(hours=1),
                    returned_to_service_at=start + timedelta(hours=24),
                    component="hose",
                    symptom="Kebocoran teramati",
                    confirmed_cause="Selang retak",
                    severity="medium",
                    work_order_id=order.id,
                    recorded_at=start + timedelta(hours=3),
                )
            )
