"""init schema

Revision ID: 20260317_000001
Revises: 
Create Date: 2026-03-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260317_000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_apps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_id", sa.String(length=255), nullable=False),
        sa.Column("api_hash_encrypted", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_apps_api_id", "telegram_apps", ["api_id"])

    op.create_table(
        "telegram_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_app_id", sa.Integer(), sa.ForeignKey("telegram_apps.id"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("bot_token_encrypted", sa.Text(), nullable=True),
        sa.Column("session_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("telegram_user_id", sa.String(length=128), nullable=True),
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("messages_sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runtime_node", sa.String(length=255), nullable=True),
        sa.Column("runtime_pid", sa.BigInteger(), nullable=True),
        sa.Column("runtime_session_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_accounts_session_name", "telegram_accounts", ["session_name"], unique=True)
    op.create_index("ix_telegram_accounts_telegram_app_id", "telegram_accounts", ["telegram_app_id"])

    op.create_table(
        "location_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_location_logs_user_id", "location_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_location_logs_user_id", table_name="location_logs")
    op.drop_table("location_logs")
    op.drop_index("ix_telegram_accounts_telegram_app_id", table_name="telegram_accounts")
    op.drop_index("ix_telegram_accounts_session_name", table_name="telegram_accounts")
    op.drop_table("telegram_accounts")
    op.drop_index("ix_telegram_apps_api_id", table_name="telegram_apps")
    op.drop_table("telegram_apps")
