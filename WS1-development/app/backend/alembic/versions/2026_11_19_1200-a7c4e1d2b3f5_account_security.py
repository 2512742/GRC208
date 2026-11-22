"""account security: forced password change, password age, one-time recovery code

Revision ID: a7c4e1d2b3f5
Revises: fb9b3c71ce52
Create Date: 2026-11-19 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7c4e1d2b3f5"
down_revision = "fb9b3c71ce52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_account") as batch:
        batch.add_column(
            sa.Column(
                "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("recovery_code_hash", sa.String(length=255), nullable=True))
        batch.add_column(
            sa.Column("recovery_code_created_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("user_account") as batch:
        batch.drop_column("recovery_code_created_at")
        batch.drop_column("recovery_code_hash")
        batch.drop_column("password_changed_at")
        batch.drop_column("must_change_password")
