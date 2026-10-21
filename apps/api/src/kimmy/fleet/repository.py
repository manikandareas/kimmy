from datetime import datetime

from sqlalchemy import and_, case, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.fleet.models import (
    BreakdownEvent,
    Depot,
    FuelEntry,
    MaintenanceWorkOrder,
    OperationSession,
    Trip,
    Vehicle,
)
from kimmy.fleet.schemas import Period, TechnicalStatus


class FleetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def vehicle_by_code(self, unit_code: str) -> Vehicle | None:
        return await self.session.scalar(
            select(Vehicle).where(Vehicle.unit_code == unit_code)
        )

    async def fuel(
        self, vehicle_id: int, period: Period, limit: int | None = None
    ) -> list[FuelEntry]:
        return list(
            await self.session.scalars(
                select(FuelEntry)
                .where(
                    FuelEntry.vehicle_id == vehicle_id,
                    FuelEntry.occurred_at >= period.start,
                    FuelEntry.occurred_at < period.end,
                )
                .order_by(FuelEntry.occurred_at, FuelEntry.id)
                .limit(limit)
            )
        )

    async def operations(
        self,
        vehicle_id: int,
        period: Period,
        limit: int | None = None,
        *,
        depot_id: int | None = None,
    ) -> list[OperationSession]:
        return list(
            await self.session.scalars(
                select(OperationSession)
                .where(
                    OperationSession.vehicle_id == vehicle_id,
                    OperationSession.started_at >= period.start,
                    OperationSession.started_at < period.end,
                    *(
                        [OperationSession.depot_id == depot_id]
                        if depot_id is not None
                        else []
                    ),
                )
                .order_by(OperationSession.started_at, OperationSession.id)
                .limit(limit)
            )
        )

    async def trips(
        self,
        vehicle_id: int,
        period: Period,
        limit: int | None = None,
        *,
        depot_id: int | None = None,
    ) -> list[Trip]:
        return list(
            await self.session.scalars(
                select(Trip)
                .where(
                    Trip.vehicle_id == vehicle_id,
                    Trip.actual_departure_at >= period.start,
                    Trip.actual_departure_at < period.end,
                    *([Trip.depot_id == depot_id] if depot_id is not None else []),
                )
                .order_by(Trip.actual_departure_at, Trip.id)
                .limit(limit)
            )
        )

    async def breakdowns(
        self,
        vehicle_id: int,
        limit: int | None = None,
        *,
        period: Period | None = None,
        as_of: datetime | None = None,
    ) -> list[BreakdownEvent]:
        filters = []
        if period is not None:
            assert as_of is not None
            filters.append(
                or_(
                    and_(
                        BreakdownEvent.reported_at >= period.start,
                        BreakdownEvent.reported_at < period.end,
                    ),
                    and_(
                        literal(period.start < as_of),
                        BreakdownEvent.out_of_service_at < min(period.end, as_of),
                        or_(
                            BreakdownEvent.returned_to_service_at.is_(None),
                            BreakdownEvent.returned_to_service_at > period.start,
                        ),
                    ),
                )
            )
        return list(
            await self.session.scalars(
                select(BreakdownEvent)
                .where(
                    BreakdownEvent.vehicle_id == vehicle_id,
                    *filters,
                )
                .order_by(BreakdownEvent.reported_at, BreakdownEvent.id)
                .limit(limit)
            )
        )

    async def orders(
        self, vehicle_id: int, limit: int | None = None, *, period: Period | None = None
    ) -> list[MaintenanceWorkOrder]:
        return list(
            await self.session.scalars(
                select(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.vehicle_id == vehicle_id,
                    *(
                        [
                            MaintenanceWorkOrder.opened_at >= period.start,
                            MaintenanceWorkOrder.opened_at < period.end,
                        ]
                        if period
                        else []
                    ),
                )
                .order_by(MaintenanceWorkOrder.opened_at, MaintenanceWorkOrder.id)
                .limit(limit)
            )
        )

    async def depot(self, depot_id: int) -> Depot | None:
        return await self.session.get(Depot, depot_id)

    async def search_vehicles(
        self,
        unit_code: str | None,
        depot_id: int | None,
        status: TechnicalStatus | None,
        as_of: datetime,
        limit: int,
        offset: int,
    ) -> list[Vehicle]:
        breakdown = (
            select(BreakdownEvent.id)
            .where(
                BreakdownEvent.vehicle_id == Vehicle.id,
                BreakdownEvent.out_of_service_at <= as_of,
                or_(
                    BreakdownEvent.returned_to_service_at.is_(None),
                    BreakdownEvent.returned_to_service_at > as_of,
                ),
            )
            .exists()
        )
        maintenance = (
            select(MaintenanceWorkOrder.id)
            .where(
                MaintenanceWorkOrder.vehicle_id == Vehicle.id,
                MaintenanceWorkOrder.status == "in_progress",
            )
            .exists()
        )
        pending = (
            select(MaintenanceWorkOrder.id)
            .where(
                MaintenanceWorkOrder.vehicle_id == Vehicle.id,
                MaintenanceWorkOrder.status.in_(["open", "scheduled"]),
            )
            .exists()
        )
        statement = select(Vehicle)
        if unit_code is not None:
            statement = statement.where(
                Vehicle.unit_code.icontains(unit_code, autoescape=True)
            )
        if depot_id is not None:
            statement = statement.where(Vehicle.depot_id == depot_id)
        if status is not None:
            statement = statement.where(
                case(
                    (breakdown, "breakdown"),
                    (maintenance, "maintenance"),
                    (pending, "maintenance_pending"),
                    else_="operational",
                )
                == status
            )
        return list(
            await self.session.scalars(
                statement.order_by(Vehicle.unit_code, Vehicle.id)
                .offset(offset)
                .limit(limit)
            )
        )

    async def status_records(
        self,
        vehicle_id: int,
        as_of: datetime,
        limit: int,
    ) -> tuple[list[BreakdownEvent], list[MaintenanceWorkOrder]]:
        events = list(
            await self.session.scalars(
                select(BreakdownEvent)
                .where(
                    BreakdownEvent.vehicle_id == vehicle_id,
                    BreakdownEvent.out_of_service_at <= as_of,
                    or_(
                        BreakdownEvent.returned_to_service_at.is_(None),
                        BreakdownEvent.returned_to_service_at > as_of,
                    ),
                )
                .order_by(BreakdownEvent.id)
                .limit(limit)
            )
        )
        orders = list(
            await self.session.scalars(
                select(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.vehicle_id == vehicle_id,
                    MaintenanceWorkOrder.status.in_(
                        ["in_progress", "open", "scheduled"]
                    ),
                )
                .order_by(MaintenanceWorkOrder.id)
                .limit(limit)
            )
        )
        return events, orders
