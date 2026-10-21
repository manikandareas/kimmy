"""Reference the successful agent checkpoint from its published run."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_runs", sa.Column("checkpoint_id", sa.String(80), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Restore a database backup to roll back agent checkpoints")
