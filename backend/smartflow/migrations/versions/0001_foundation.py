"""Initial immutable schema for jobs, receipts, events and the provider simulator."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("command_key", sa.String(80), nullable=False, unique=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("scenario", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("error_code", sa.String(50)),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("save_attempts", sa.Integer(), nullable=False),
        sa.Column("observations", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.Float(), nullable=False),
        sa.Column("artifact", sa.String(160)),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "receipts",
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, unique=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("result", sa.Text()),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("at", sa.Float(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("code", sa.String(50)),
        sa.Column("details", sa.Text(), nullable=False),
    )
    op.create_index("ix_events_job_id", "events", ["job_id"])
    op.create_index("ix_events_trace_id", "events", ["trace_id"])
    op.create_table(
        "simulated_requests",
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("sends", sa.Integer(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Destructive downgrade is not supported; restore a verified backup instead")
