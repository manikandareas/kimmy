"""General user memories and publication generation fencing."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE memory_states (
        user_id varchar(200) PRIMARY KEY,
        generation bigint NOT NULL DEFAULT 0 CHECK (generation >= 0)
    );
    CREATE TABLE memory_revisions (
        id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision > 0),
        user_id varchar(200) NOT NULL REFERENCES memory_states(user_id),
        content text NOT NULL CHECK (length(content) <= 1000),
        active boolean NOT NULL,
        source_message_id uuid REFERENCES chat_messages(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (id, revision),
        CHECK (NOT active OR length(trim(content)) > 0)
    );
    CREATE UNIQUE INDEX memory_one_active_idx ON memory_revisions(id) WHERE active;
    CREATE INDEX memory_user_active_idx ON memory_revisions(user_id, active);
    ALTER TABLE chat_runs ADD COLUMN memory_generation bigint;
    """)


def downgrade() -> None:
    raise RuntimeError("Restore a backup to roll back memory history")
