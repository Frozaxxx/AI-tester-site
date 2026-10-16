"""owner_id в прогонах

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 17:11:06.271160
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("owner_id", sa.Uuid(), nullable=False))
    op.create_index(op.f("ix_runs_owner_id"), "runs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_owner_id"), table_name="runs")
    op.drop_column("runs", "owner_id")
