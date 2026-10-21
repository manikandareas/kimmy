from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

DDL = """
SET TIME ZONE 'UTC';

CREATE TABLE depots (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code varchar(20) NOT NULL UNIQUE,
    name varchar(100) NOT NULL,
    timezone varchar(50) NOT NULL
);

CREATE TABLE vehicles (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    depot_id bigint NOT NULL REFERENCES depots(id),
    unit_code varchar(20) NOT NULL UNIQUE,
    plate_number varchar(15) NOT NULL UNIQUE,
    vehicle_class varchar(30) NOT NULL,
    fuel_type varchar(20) NOT NULL,
    tank_capacity_liters numeric(8,1) NOT NULL,
    max_payload_kg int NOT NULL
);

CREATE TABLE trips (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_number varchar(25) NOT NULL UNIQUE,
    vehicle_id bigint NOT NULL REFERENCES vehicles(id),
    depot_id bigint NOT NULL REFERENCES depots(id),
    origin varchar(100) NOT NULL,
    destination varchar(100) NOT NULL,
    planned_departure_at timestamptz NOT NULL,
    actual_departure_at timestamptz NULL,
    actual_arrival_at timestamptz NULL,
    start_odometer_km numeric(10,1) NOT NULL,
    end_odometer_km numeric(10,1) NULL,
    payload_kg int NULL,
    status varchar(20) NOT NULL CHECK (status IN ('planned', 'in_progress',
        'completed', 'cancelled')),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT trips_odometer_order CHECK (end_odometer_km >= start_odometer_km),
    CONSTRAINT trips_time_order CHECK (actual_arrival_at >= actual_departure_at),
    CONSTRAINT trips_departure_by_status CHECK ((status = 'planned' AND
        actual_departure_at IS NULL) OR (status IN ('in_progress', 'completed') AND
        actual_departure_at IS NOT NULL) OR status = 'cancelled')
);

CREATE TABLE fuel_entries (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL REFERENCES vehicles(id),
    depot_id bigint NOT NULL REFERENCES depots(id),
    occurred_at timestamptz NOT NULL,
    odometer_km numeric(10,1) NULL,
    liters numeric(8,2) NOT NULL,
    unit_price_idr numeric(12,2) NOT NULL,
    fill_type varchar(10) NOT NULL CHECK (fill_type IN ('full', 'partial', 'unknown')),
    meter_valid boolean NOT NULL DEFAULT true,
    reset_baseline boolean NOT NULL DEFAULT false,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE operation_sessions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL REFERENCES vehicles(id),
    depot_id bigint NOT NULL REFERENCES depots(id),
    started_at timestamptz NOT NULL,
    ended_at timestamptz NULL,
    engine_on_seconds int NULL,
    idle_seconds int NULL,
    coverage_status varchar(10) NOT NULL CHECK (coverage_status IN ('complete',
        'partial', 'none')),
    CONSTRAINT operation_sessions_idle_limit CHECK (idle_seconds <= engine_on_seconds)
);

CREATE TABLE maintenance_work_orders (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    work_order_number varchar(25) NOT NULL UNIQUE,
    vehicle_id bigint NOT NULL REFERENCES vehicles(id),
    type varchar(20) NOT NULL CHECK (type IN ('preventive', 'corrective')),
    status varchar(20) NOT NULL CHECK (status IN ('open', 'scheduled', 'in_progress',
        'completed', 'cancelled')),
    opened_at timestamptz NOT NULL,
    scheduled_at timestamptz NULL,
    started_at timestamptz NULL,
    completed_at timestamptz NULL,
    service_odometer_km numeric(10,1) NULL,
    due_at timestamptz NULL,
    due_odometer_km numeric(10,1) NULL,
    total_cost_idr numeric(14,2) NULL
);

CREATE TABLE breakdown_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id bigint NOT NULL REFERENCES vehicles(id),
    reported_at timestamptz NOT NULL,
    out_of_service_at timestamptz NOT NULL,
    returned_to_service_at timestamptz NULL,
    component varchar(50) NOT NULL,
    symptom text NOT NULL,
    confirmed_cause text NULL,
    severity varchar(10) NOT NULL CHECK (severity IN ('low', 'medium', 'high',
        'critical')),
    work_order_id bigint NULL REFERENCES maintenance_work_orders(id),
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX fuel_entries_vehicle_occurred_idx ON fuel_entries (vehicle_id,
        occurred_at);
CREATE INDEX operation_sessions_vehicle_started_idx ON operation_sessions (vehicle_id,
        started_at);
CREATE INDEX breakdown_events_vehicle_reported_idx ON breakdown_events (vehicle_id,
        reported_at);
CREATE INDEX trips_vehicle_departure_idx ON trips (vehicle_id, actual_departure_at);
"""


def upgrade() -> None:
    for statement in DDL.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for table in (
        "breakdown_events",
        "maintenance_work_orders",
        "operation_sessions",
        "fuel_entries",
        "trips",
        "vehicles",
        "depots",
    ):
        op.drop_table(table)
