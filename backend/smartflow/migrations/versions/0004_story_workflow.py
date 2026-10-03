"""Immutable draft snapshots and leased browser operations."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "story_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), unique=True, nullable=False),
        sa.Column("draft_id", sa.String(36), sa.ForeignKey("story_drafts.id"), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
    )
    op.create_table(
        "browser_sessions",
        sa.Column("pair_id", sa.String(36), sa.ForeignKey("browser_pairings.id"), primary_key=True),
        sa.Column("connection_id", sa.String(36), nullable=False),
        sa.Column("last_seen", sa.Float(), nullable=False),
    )
    op.create_table(
        "story_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), unique=True, nullable=False),
        sa.Column("revision_id", sa.String(36), sa.ForeignKey("story_revisions.id"), nullable=False),
        sa.Column("pair_id", sa.String(36), sa.ForeignKey("browser_pairings.id"), nullable=True),
        sa.Column("connection_id", sa.String(36), nullable=True),
        sa.Column("lease_epoch", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.Float(), nullable=False),
        sa.Column("deadline", sa.Float(), nullable=False),
    )
    op.create_table(
        "operation_receipts",
        sa.Column("operation_id", sa.String(36), sa.ForeignKey("story_operations.id"), primary_key=True),
        sa.Column("request_id", sa.String(36), unique=True, nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Restore a verified backup instead")
