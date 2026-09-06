"""restore the complete canonical baseline schema

Revision ID: 20260906_restore_full_canonical_schema
Revises: 20260906_restore_metadata_core

The historical 87aba7990b4d baseline was generated from an already-populated
production database and its upgrade/downgrade bodies were reversed.  Its
upgrade therefore contains cleanup operations while its downgrade contains
the canonical CREATE TABLE sequence.

Until that historical revision can be safely rewritten without changing the
identity of an already-published migration, this migration executes the
canonical create sequence from that baseline on a clean database.  The
Alembic environment makes CREATE TABLE and related operations idempotent so
this also repairs databases that already contain a subset of the schema.
"""

from __future__ import annotations

import importlib

from alembic import op

revision = "20260906_restore_full_canonical_schema"
down_revision = "20260906_restore_metadata_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    baseline = importlib.import_module(
        "alembic.versions.87aba7990b4d_initial_schema"
    )
    baseline.downgrade()


def downgrade() -> None:
    # The historical baseline's upgrade body is destructive cleanup for a
    # populated database.  This compatibility revision is intentionally
    # irreversible rather than risking destructive rollback of a live schema.
    pass
