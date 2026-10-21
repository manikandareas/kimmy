from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.fleet.models import (
    BreakdownEvent,
    FuelEntry,
    MaintenanceWorkOrder,
    OperationSession,
    Trip,
    Vehicle,
)
from kimmy.fleet.schemas import Period


class FleetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def vehicle_by_code(self, unit_code: str) -> Vehicle | None:
        return await self.session.scalar(
            select(Vehicle).where(Vehicle.unit_code == unit_code)
        )

    async def fuel(self, vehicle_id: int, period: Period) -> list[FuelEntry]:
        # Do not filter depot here: that would hide cross-depot interval records.
        return list(
            await self.session.scalars(
                select(FuelEntry)
                .where(
                    FuelEntry.vehicle_id == vehicle_id,
                    FuelEntry.occurred_at >= period.start,
                    FuelEntry.occurred_at < period.end,
                )
                .order_by(FuelEntry.occurred_at, FuelEntry.id)
            )
        )

    async def operations(
        self, vehicle_id: int, period: Period
    ) -> list[OperationSession]:
        return list(
            await self.session.scalars(
                select(OperationSession)
                .where(
                    OperationSession.vehicle_id == vehicle_id,
                    OperationSession.started_at >= period.start,
                    OperationSession.started_at < period.end,
                )
                .order_by(OperationSession.started_at, OperationSession.id)
            )
        )

    async def trips(self, vehicle_id: int, period: Period) -> list[Trip]:
        return list(
            await self.session.scalars(
                select(Trip)
                .where(
                    Trip.vehicle_id == vehicle_id,
                    Trip.actual_departure_at >= period.start,
                    Trip.actual_departure_at < period.end,
                )
                .order_by(Trip.actual_departure_at, Trip.id)
            )
        )

    async def breakdowns(self, vehicle_id: int) -> list[BreakdownEvent]:
        # Include events reported before the period for downtime overlap/status.
        return list(
            await self.session.scalars(
                select(BreakdownEvent)
                .where(
                    BreakdownEvent.vehicle_id == vehicle_id,
                )
                .order_by(BreakdownEvent.reported_at, BreakdownEvent.id)
            )
        )

    async def orders(self, vehicle_id: int) -> list[MaintenanceWorkOrder]:
        return list(
            await self.session.scalars(
                select(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.vehicle_id == vehicle_id,
                )
                .order_by(MaintenanceWorkOrder.opened_at, MaintenanceWorkOrder.id)
            )
        )
