"""Restore the complete canonical schema from the historical baseline.

The published 87aba7990b4d revision has its upgrade/downgrade bodies reversed.
Its downgrade body is therefore the canonical CREATE TABLE sequence. This
compatibility migration executes that sequence without changing the identity
of the already-published revision.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

revision = "20260906_restore_full_canonical_schema"
down_revision = "20260906_restore_metadata_core"
branch_labels = None
depends_on = None


def _load_baseline():
    path = Path(__file__).with_name("87aba7990b4d_initial_schema.py")
    spec = importlib.util.spec_from_file_location("eos_initial_schema_baseline", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load canonical baseline: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    baseline = _load_baseline()
    baseline.downgrade()


def downgrade() -> None:
    # Intentionally irreversible: the historical baseline upgrade body is
    # destructive cleanup for a populated database and must never be used as
    # an automatic rollback of the repaired canonical schema.
    pass
