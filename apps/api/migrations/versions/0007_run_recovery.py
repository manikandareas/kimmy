"""Fenced run execution and explicit commands."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE chat_runs DROP CONSTRAINT chat_runs_status_check;
    ALTER TABLE chat_runs ADD CONSTRAINT chat_runs_status_check
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));
    ALTER TABLE chat_runs ADD COLUMN owner_token uuid,
        ADD COLUMN lease_until timestamptz,
        ADD COLUMN attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 3),
        ADD COLUMN provider varchar(20) NOT NULL DEFAULT 'openai',
        ADD COLUMN model varchar(200),
        ADD COLUMN resume_checkpoint_id varchar(80),
        ADD COLUMN reset_history boolean NOT NULL DEFAULT false;
    CREATE TABLE chat_run_commands (
        run_id uuid NOT NULL REFERENCES chat_runs(id),
        request_key varchar(128) NOT NULL,
        kind varchar(20) NOT NULL CHECK (kind IN ('cancel', 'retry')),
        expected_attempt integer NOT NULL,
        PRIMARY KEY(run_id, request_key)
    );
    CREATE INDEX chat_runs_lease_idx ON chat_runs(lease_until) WHERE status = 'running';
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE chat_run_commands;
    DROP INDEX chat_runs_lease_idx;
    UPDATE chat_runs SET status = 'failed', error_code = 'RUN_CANCELLED'
    WHERE status = 'cancelled';
    ALTER TABLE chat_runs DROP CONSTRAINT chat_runs_status_check;
    ALTER TABLE chat_runs ADD CONSTRAINT chat_runs_status_check
        CHECK (status IN ('queued', 'running', 'completed', 'failed'));
    ALTER TABLE chat_runs DROP COLUMN owner_token, DROP COLUMN lease_until,
        DROP COLUMN attempts, DROP COLUMN provider, DROP COLUMN model,
        DROP COLUMN resume_checkpoint_id, DROP COLUMN reset_history;
    """)
