"""Merge the accounting-integrity and RLS release branches.

Revision ID: 20260909_merge_release_heads
Revises: 20260906_accounting_integrity, rls_activate_001
Create Date: 2026-09-09

This is an empty graph-only merge. Existing published revisions are preserved;
the merge restores a single deterministic Alembic head for deployments.
"""

from alembic import op

revision = "20260909_merge_release_heads"
down_revision = ("20260906_accounting_integrity", "rls_activate_001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
