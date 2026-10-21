"""Persist validated source metadata with assistant messages."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE chat_messages ADD COLUMN citations jsonb "
        "NOT NULL DEFAULT '[]'::jsonb"
    )


def downgrade() -> None:
    raise RuntimeError("Restore a backup to roll back message citations")
