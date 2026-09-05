"""Restore the tenant-scoped number sequence table used by accounting.

Revision ID: 20260905_number_sequences
Revises: 20260905_restore_sales_cycle
"""
from alembic import op
import sqlalchemy as sa


revision = "20260905_number_sequences"
down_revision = "20260905_restore_sales_cycle"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "number_sequences" in inspector.get_table_names():
        return

    op.create_table(
        "number_sequences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=32), nullable=False),
        sa.Column("current_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("increment_by", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("padding", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_number_sequences_tenant_name"),
    )
    op.create_index(
        "ix_number_sequences_tenant_id",
        "number_sequences",
        ["tenant_id"],
    )

    # Defense in depth: callers still supply tenant_id in every accounting
    # query, while PostgreSQL prevents accidental cross-tenant access.
    op.execute("ALTER TABLE number_sequences ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE number_sequences FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY number_sequences_tenant_isolation ON number_sequences "
        "USING (tenant_id = current_setting('app.tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "number_sequences" not in inspector.get_table_names():
        return
    op.execute("DROP POLICY IF EXISTS number_sequences_tenant_isolation ON number_sequences")
    op.drop_index("ix_number_sequences_tenant_id", table_name="number_sequences")
    op.drop_table("number_sequences")
