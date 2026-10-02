"""Draft storage, command receipts and content-free audit events."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "story_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_scope", sa.String(40), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("active_step", sa.Integer(), nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_story_drafts_owner_scope", "story_drafts", ["owner_scope"])
    op.create_table(
        "draft_commands",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("draft_id", sa.String(36), sa.ForeignKey("story_drafts.id"), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
    )
    op.create_index("ix_draft_commands_draft_id", "draft_commands", ["draft_id"])
    op.create_table(
        "draft_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("draft_id", sa.String(36), sa.ForeignKey("story_drafts.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("at", sa.Float(), nullable=False),
    )
    op.create_index("ix_draft_events_draft_id", "draft_events", ["draft_id"])


def downgrade():
    raise RuntimeError("Use a verified backup; destructive downgrade is not supported")
