"""Restore the complete canonical schema from the historical baseline.

The published 87aba7990b4d revision has its upgrade/downgrade bodies reversed.
Its downgrade body is therefore the canonical CREATE TABLE sequence. The
canonical sequence was generated in reverse dependency order, so foreign-key
constraints are deferred until every table exists.

This repair migration is deliberately additive: earlier compatibility
migrations may already have restored a subset of the canonical tables and
indexes. Existing objects are preserved rather than recreated.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic import op
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.schema import ForeignKeyConstraint

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


def _create_deferred_foreign_key(constraint: ForeignKeyConstraint) -> None:
    table = constraint.table
    source_table = table.name
    source_schema = table.schema
    referent = constraint.referred_table
    referent_table = referent.name
    referent_schema = referent.schema

    inspector = sa_inspect(op.get_bind())
    existing = inspector.get_foreign_keys(source_table, schema=source_schema)
    if any(item.get("name") == constraint.name for item in existing):
        return

    local_columns = [element.parent.name for element in constraint.elements]
    remote_columns = [element.column.name for element in constraint.elements]

    op.create_foreign_key(
        constraint.name,
        source_table,
        referent_table,
        local_columns,
        remote_columns,
        source_schema=source_schema,
        referent_schema=referent_schema,
        onupdate=constraint.onupdate,
        ondelete=constraint.ondelete,
        deferrable=constraint.deferrable,
        initially=constraint.initially,
        use_alter=constraint.use_alter,
    )


def upgrade() -> None:
    baseline = _load_baseline()
    deferred: list[ForeignKeyConstraint] = []
    inspector = sa_inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    original_create_table = op.create_table
    original_create_index = op.create_index

    def create_table_without_fks(*args, **kwargs):
        table_name = args[0]
        schema = kwargs.get("schema")
        foreign_keys = [item for item in args if isinstance(item, ForeignKeyConstraint)]
        deferred.extend(foreign_keys)

        if table_name in existing_tables:
            # Compatibility migrations may have already restored this table.
            # Keep the existing definition and only reconcile missing FKs.
            return None

        filtered_args = tuple(
            item for item in args if not isinstance(item, ForeignKeyConstraint)
        )
        result = original_create_table(*filtered_args, **kwargs)
        if schema is None:
            existing_tables.add(table_name)
        return result

    def create_index_if_missing(index, *args, **kwargs):
        index_name = index if isinstance(index, str) else getattr(index, "name", None)
        table_name = args[0] if args else kwargs.get("table_name")
        schema = kwargs.get("schema")
        if index_name and table_name:
            existing_indexes = inspector.get_indexes(table_name, schema=schema)
            if any(item.get("name") == index_name for item in existing_indexes):
                return None
        return original_create_index(index, *args, **kwargs)

    op.create_table = create_table_without_fks
    op.create_index = create_index_if_missing
    try:
        baseline.downgrade()
    finally:
        op.create_table = original_create_table
        op.create_index = original_create_index

    # All tables now exist, so the foreign-key graph can be restored safely
    # even though the historical baseline emitted CREATE TABLE statements in
    # reverse dependency order. Existing FKs are skipped.
    for constraint in deferred:
        _create_deferred_foreign_key(constraint)


def downgrade() -> None:
    # Intentionally irreversible: the historical baseline upgrade body is
    # destructive cleanup for a populated database and must never be used as
    # an automatic rollback of the repaired canonical schema.
    pass
