from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Depot(Base):
    __tablename__ = "depots"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50))


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    depot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("depots.id"))
    unit_code: Mapped[str] = mapped_column(String(20), unique=True)
    plate_number: Mapped[str] = mapped_column(String(15), unique=True)
    vehicle_class: Mapped[str] = mapped_column(String(30))
    fuel_type: Mapped[str] = mapped_column(String(20))
    tank_capacity_liters: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    max_payload_kg: Mapped[int] = mapped_column(Integer)


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    trip_number: Mapped[str] = mapped_column(String(25), unique=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehicles.id"))
    depot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("depots.id"))
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    planned_departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_odometer_km: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    end_odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    payload_kg: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="trips_status_check",
        ),
        CheckConstraint(
            "end_odometer_km >= start_odometer_km", name="trips_odometer_order"
        ),
        CheckConstraint(
            "actual_arrival_at >= actual_departure_at", name="trips_time_order"
        ),
        CheckConstraint(
            "(status = 'planned' AND actual_departure_at IS NULL) "
            "OR (status IN ('in_progress', 'completed') "
            "AND actual_departure_at IS NOT NULL) OR status = 'cancelled'",
            name="trips_departure_by_status",
        ),
        Index("trips_vehicle_departure_idx", "vehicle_id", "actual_departure_at"),
    )


class FuelEntry(Base):
    __tablename__ = "fuel_entries"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehicles.id"))
    depot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("depots.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    liters: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    unit_price_idr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fill_type: Mapped[str] = mapped_column(String(10))
    meter_valid: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    reset_baseline: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "fill_type IN ('full', 'partial', 'unknown')",
            name="fuel_entries_fill_type_check",
        ),
        Index("fuel_entries_vehicle_occurred_idx", "vehicle_id", "occurred_at"),
    )


class OperationSession(Base):
    __tablename__ = "operation_sessions"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehicles.id"))
    depot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("depots.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engine_on_seconds: Mapped[int | None] = mapped_column(Integer)
    idle_seconds: Mapped[int | None] = mapped_column(Integer)
    coverage_status: Mapped[str] = mapped_column(String(10))
    __table_args__ = (
        CheckConstraint(
            "coverage_status IN ('complete', 'partial', 'none')",
            name="operation_sessions_coverage_status_check",
        ),
        CheckConstraint(
            "idle_seconds <= engine_on_seconds", name="operation_sessions_idle_limit"
        ),
        Index("operation_sessions_vehicle_started_idx", "vehicle_id", "started_at"),
    )


class MaintenanceWorkOrder(Base):
    __tablename__ = "maintenance_work_orders"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    work_order_number: Mapped[str] = mapped_column(String(25), unique=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehicles.id"))
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    total_cost_idr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    __table_args__ = (
        CheckConstraint(
            "type IN ('preventive', 'corrective')",
            name="maintenance_work_orders_type_check",
        ),
        CheckConstraint(
            "status IN ('open', 'scheduled', 'in_progress', 'completed', 'cancelled')",
            name="maintenance_work_orders_status_check",
        ),
    )


class BreakdownEvent(Base):
    __tablename__ = "breakdown_events"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vehicles.id"))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    out_of_service_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    returned_to_service_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    component: Mapped[str] = mapped_column(String(50))
    symptom: Mapped[str] = mapped_column(Text)
    confirmed_cause: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10))
    work_order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("maintenance_work_orders.id")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="breakdown_events_severity_check",
        ),
        Index("breakdown_events_vehicle_reported_idx", "vehicle_id", "reported_at"),
    )
