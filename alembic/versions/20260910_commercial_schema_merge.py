"""Merge the historical API-core schema branch into the commercial release head.

This merge is intentionally empty. Its purpose is to reconcile databases that
were upgraded through either migration lineage while preserving migration
provenance and making ``alembic upgrade head`` unambiguous.
"""
revision = "20260910_commercial_schema_merge"
down_revision = ("20260910_refresh_mfa_state", "20260905_restore_api_core_tables")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
