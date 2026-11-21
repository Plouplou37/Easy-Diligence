"""run time without the pauses

The run card showed the time since the first answer, pauses included: a run
paused for an hour showed an hour. dd_executions now keeps the time spent
running (run_seconds), and the start of the stretch going on (running_since).

The existing runs get an estimate from their answers: the sum of the gaps
between two answers, a gap of more than 5 minutes counting as a pause. A run
in progress starts a new stretch now. The data is moved online only: offline,
the SQL written (db/schema.sql) builds an empty database.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21 15:06:32.691163

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A gap between two answers longer than this is a pause, not work.
PAUSE_SECONDS = 300


def upgrade() -> None:
    op.add_column(
        "dd_executions",
        sa.Column("run_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "dd_executions", sa.Column("running_since", sa.DateTime(timezone=True), nullable=True)
    )
    if context.is_offline_mode():
        return
    op.execute(
        sa.text(
            "UPDATE dd_executions e SET run_seconds = g.seconds FROM ("
            " SELECT execution_id, CAST(SUM(gap) AS INTEGER) AS seconds FROM ("
            "  SELECT execution_id, EXTRACT(EPOCH FROM created_at - LAG(created_at)"
            "   OVER (PARTITION BY execution_id ORDER BY created_at)) AS gap"
            "  FROM dd_answers"
            " ) gaps WHERE gap <= :pause GROUP BY execution_id"
            ") g WHERE g.execution_id = e.id"
        ).bindparams(pause=PAUSE_SECONDS)
    )
    op.execute("UPDATE dd_executions SET running_since = now() WHERE status = 'in_progress'")


def downgrade() -> None:
    op.drop_column("dd_executions", "running_since")
    op.drop_column("dd_executions", "run_seconds")
