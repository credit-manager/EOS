"""add foreign key constraints on tenant_id columns.

Revision ID: a1b2c3d4e5f6
Revises: 213106a27f4c
Create Date: 2026-09-12 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '213106a27f4c'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("metadata_entities") as batch_op:
        batch_op.create_foreign_key(
            "fk_metadata_entities_tenant_id",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.create_foreign_key(
            "fk_audit_events_tenant_id",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("records") as batch_op:
        batch_op.create_foreign_key(
            "fk_records_tenant_id",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("records") as batch_op:
        batch_op.drop_constraint("fk_records_tenant_id", type_="foreignkey")

    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.drop_constraint("fk_audit_events_tenant_id", type_="foreignkey")

    with op.batch_alter_table("metadata_entities") as batch_op:
        batch_op.drop_constraint("fk_metadata_entities_tenant_id", type_="foreignkey")
