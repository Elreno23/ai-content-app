"""baseline: tabla narrative (esquema consolidado post-refactor)

Revision ID: 0001_baseline_narrative
Revises:
Create Date: 2026-11-21

Replica exactamente el esquema existente en producción:
- narrative.id: Integer + secuencia (SERIAL), PK
- narrative.episode_number: Integer NOT NULL, índice único
- narrative.create_at: timestamptz NOT NULL, server_default now()
- narrative.payload: JSONB NOT NULL
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_baseline_narrative"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "narrative",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column(
            "create_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_narrative_id"), "narrative", ["id"], unique=False)
    op.create_index(
        op.f("ix_narrative_episode_number"),
        "narrative",
        ["episode_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_narrative_episode_number"), table_name="narrative")
    op.drop_index(op.f("ix_narrative_id"), table_name="narrative")
    op.drop_table("narrative")
