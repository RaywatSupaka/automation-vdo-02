"""Managed draft assets and scoped browser pairing; no provider dispatch."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "draft_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("draft_id", sa.String(36), sa.ForeignKey("story_drafts.id"), nullable=False),
        sa.Column("command_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("field", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
    )
    op.create_index("ix_draft_assets_draft_id", "draft_assets", ["draft_id"])
    op.create_table(
        "browser_pairings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("extension_id", sa.String(32), nullable=False),
        sa.Column("nonce_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=True),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("last_seen", sa.Float(), nullable=False),
    )

    op.create_table(
        "browser_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pair_id", sa.String(36), sa.ForeignKey("browser_pairings.id"), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("at", sa.Float(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Restore a verified backup instead")
