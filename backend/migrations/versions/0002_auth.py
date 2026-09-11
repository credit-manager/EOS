"""add authentication and tenant membership"""
import sqlalchemy as sa

from alembic import op

revision = "0002_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_membership"),
    )
    op.create_index(op.f("ix_tenant_memberships_tenant_id"), "tenant_memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_memberships_user_id"), "tenant_memberships", ["user_id"], unique=False)

    with op.batch_alter_table("audit_events", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("actor_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_audit_events_actor_id", "users", ["actor_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index(op.f("ix_audit_events_actor_id"), ["actor_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("audit_events", recreate="auto") as batch_op:
        batch_op.drop_index(op.f("ix_audit_events_actor_id"))
        batch_op.drop_constraint("fk_audit_events_actor_id", type_="foreignkey")
        batch_op.drop_column("actor_id")
    op.drop_index(op.f("ix_tenant_memberships_user_id"), table_name="tenant_memberships")
    op.drop_index(op.f("ix_tenant_memberships_tenant_id"), table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_table("tenants")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
