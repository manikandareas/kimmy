from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DDL = """
CREATE TABLE chat_threads (
    id uuid PRIMARY KEY,
    user_id varchar(200) NOT NULL,
    title varchar(200) NOT NULL,
    last_seq bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chat_threads_seq_check CHECK (last_seq >= 0)
);
CREATE INDEX chat_threads_user_updated_idx ON chat_threads (user_id, updated_at, id);
CREATE TABLE chat_messages (
    id uuid PRIMARY KEY,
    thread_id uuid NOT NULL REFERENCES chat_threads(id),
    seq bigint NOT NULL,
    role varchar(20) NOT NULL,
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chat_messages_thread_seq_key UNIQUE (thread_id, seq),
    CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant')),
    CONSTRAINT chat_messages_seq_check CHECK (seq > 0)
);
CREATE TABLE chat_runs (
    id uuid PRIMARY KEY,
    thread_id uuid NOT NULL REFERENCES chat_threads(id),
    message_id uuid NOT NULL UNIQUE REFERENCES chat_messages(id),
    request_key varchar(128) NOT NULL,
    status varchar(20) NOT NULL,
    error_code varchar(80),
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    CONSTRAINT chat_runs_request_key UNIQUE (thread_id, request_key),
    CONSTRAINT chat_runs_status_check CHECK (status IN
        ('queued', 'running', 'completed', 'failed'))
);
CREATE UNIQUE INDEX chat_runs_one_active_idx ON chat_runs (thread_id)
    WHERE status IN ('queued', 'running');
CREATE INDEX chat_runs_thread_created_idx ON chat_runs (thread_id, created_at, id);
CREATE TABLE chat_events (
    thread_id uuid NOT NULL REFERENCES chat_threads(id),
    seq bigint NOT NULL,
    run_id uuid NOT NULL REFERENCES chat_runs(id),
    kind varchar(80) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, seq),
    CONSTRAINT chat_events_seq_check CHECK (seq > 0)
);
"""


def upgrade() -> None:
    for statement in DDL.split(";"):
        if statement.strip():
            op.execute(statement)
    # Frozen upstream schema, so a future library upgrade cannot change history.
    schema = Path(__file__).parents[1] / "sql" / "procrastinate-3.10.0.sql"
    op.execute(schema.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError(
        "0002 preserves durable chat and queue data; restore a backup to roll back"
    )
