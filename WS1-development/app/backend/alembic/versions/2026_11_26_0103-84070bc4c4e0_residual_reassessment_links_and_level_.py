"""residual reassessment links and level definitions

Links each residual reassessment to the completed treatment actions it followed (insert-only,
like the assessments themselves), and adds editable definitions for the five likelihood and
five impact levels to the settings row.

Revision ID: 84070bc4c4e0
Revises: a7c4e1d2b3f5
Create Date: 2026-11-26 01:03:10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "84070bc4c4e0"
down_revision = "a7c4e1d2b3f5"
branch_labels = None
depends_on = None

TABLE = "assessment_action"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("action_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["treatment_action.id"],
            name=op.f("fk_assessment_action_action_id_treatment_action"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["risk_assessment.id"],
            name=op.f("fk_assessment_action_assessment_id_risk_assessment"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("assessment_id", "action_id", name=op.f("pk_assessment_action")),
    )
    with op.batch_alter_table("app_setting", schema=None) as batch_op:
        batch_op.add_column(sa.Column("likelihood_definitions", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("impact_definitions", sa.JSON(), nullable=True))

    # Insert-only, like risk_assessment (the PostgreSQL function comes from the baseline).
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            f"CREATE TRIGGER trg_{TABLE}_insert_only BEFORE UPDATE OR DELETE ON {TABLE} "
            "FOR EACH ROW EXECUTE FUNCTION risktrack_block_modification()"
        )
    elif dialect == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER trg_{TABLE}_no_{operation.lower()} BEFORE {operation} ON {TABLE} "
                f"BEGIN SELECT RAISE(ABORT, 'table {TABLE} is insert-only: {operation} is not "
                "allowed'); END"
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS trg_{TABLE}_insert_only ON {TABLE}")
    elif dialect == "sqlite":
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{TABLE}_no_{operation}")
    with op.batch_alter_table("app_setting", schema=None) as batch_op:
        batch_op.drop_column("impact_definitions")
        batch_op.drop_column("likelihood_definitions")
    op.drop_table(TABLE)
