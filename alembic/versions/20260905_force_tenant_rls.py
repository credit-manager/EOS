"""Force RLS on enterprise hardening tables whose policies are strict tenant boundaries.

Legacy tables retain the application-layer tenant filters plus normal RLS policy.
Forcing RLS on every legacy table would make existing migrations/tests that create
shared or system metadata fail because their database owner would become subject
to tenant checks. Production legacy isolation is therefore still expected to run
with a non-owner application database role.
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


def upgrade():
    for table in _HARDENED_TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE public."{table}" FORCE ROW LEVEL SECURITY')


def downgrade():
    for table in _HARDENED_TABLES:
        op.execute(f'ALTER TABLE public."{table}" NO FORCE ROW LEVEL SECURITY')
