"""Force RLS on enterprise hardening tables when they exist.

Some supported fresh-database profiles do not materialize every optional
enterprise table in the historical migration chain. The hardening migration
must therefore be additive and idempotent with respect to table presence.
"""
from alembic import op

revision = "20260905_force_tenant_rls"
down_revision = "20260905_refresh_tokens"
branch_labels = None
depends_on = None

_HARDENED_TABLES = (
    "dbp_idempotency_keys",
    "dbp_outbox_events",
    "dbp_fiscal_periods",
    "dbp_accounting_dimensions",
    "dbp_exchange_rates",
)


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            __import__("sqlalchemy").text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table)"
            ),
            {"table": table},
        ).scalar()
    )


def upgrade():
    for table in _HARDENED_TABLES:
        if _table_exists(table):
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE public."{table}" FORCE ROW LEVEL SECURITY')


def downgrade():
    for table in _HARDENED_TABLES:
        if _table_exists(table):
            op.execute(f'ALTER TABLE public."{table}" NO FORCE ROW LEVEL SECURITY')
