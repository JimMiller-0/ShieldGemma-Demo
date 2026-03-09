"""Initial schema — safety_policies and analysis_logs

Revision ID: 001
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "safety_policies",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column(
            "predefined_policy_config",
            JSONB(),
            nullable=False,
            server_default=sa.text(
                """'{"dangerous_content": true, "harassment": true, "hate_speech": true, "sexually_explicit": true}'::jsonb"""
            ),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "analysis_logs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("text_input", sa.Text(), nullable=False),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("safety_policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("policy_name", sa.String(255), nullable=True),
        sa.Column("is_safe", sa.Boolean(), nullable=False),
        sa.Column("safety_categories", JSONB(), nullable=False),
        sa.Column("model_used", sa.String(255), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("inference_time_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("analysis_logs")
    op.drop_table("safety_policies")
