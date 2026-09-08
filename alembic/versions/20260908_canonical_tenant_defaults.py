"""Provide safe defaults for canonical tenant identity bootstrap rows.

The legacy canonical ``tenants`` table requires ``industry`` and ``email``
while the current control-plane registration flow does not populate those
legacy fields. Accounting only needs the canonical identity row to satisfy
its foreign keys, so the database should supply deterministic non-null
values instead of making Accounting guess or weaken constraints.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260908_canonical_tenant_defaults"
down_revision = "20260906_restore_full_canonical_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tenants"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("tenants")}
    if "industry" in columns:
        op.alter_column(
            "tenants",
            "industry",
            existing_type=sa.VARCHAR(length=50),
            existing_nullable=False,
            server_default=sa.text("'general'"),
        )
    if "email" in columns:
        op.alter_column(
            "tenants",
            "email",
            existing_type=sa.VARCHAR(length=255),
            existing_nullable=False,
            server_default=sa.text("'system@eos.local'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tenants"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("tenants")}
    if "industry" in columns:
        op.alter_column(
            "tenants",
            "industry",
            existing_type=sa.VARCHAR(length=50),
            existing_nullable=False,
            server_default=None,
        )
    if "email" in columns:
        op.alter_column(
            "tenants",
            "email",
            existing_type=sa.VARCHAR(length=255),
            existing_nullable=False,
            server_default=None,
        )
