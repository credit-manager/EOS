"""Restore the complete canonical schema from the historical baseline.

The published 87aba7990b4d revision has its upgrade/downgrade bodies reversed.
Its downgrade body is therefore the canonical CREATE TABLE sequence. The
canonical sequence was generated in reverse dependency order, so foreign-key
constraints are deferred until every table exists.

Some preceding repair migrations already restore a subset of those canonical
tables, sometimes with a compatible but narrower column shape. This migration
is therefore additive and schema-aware: it creates only missing tables, adds
only missing foreign keys, and restores indexes only when their referenced
columns actually exist.
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
    actual_columns = {
        item["name"] for item in inspector.get_columns(source_table, schema=source_schema)
    }
    referent_columns = {
        item["name"]
        for item in inspector.get_columns(referent_table, schema=referent_schema)
    }
    if not set(local_columns).issubset(actual_columns):
        return
    if not set(remote_columns).issubset(referent_columns):
        return

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

    original_create_table = op.create_table
    original_create_index = op.create_index

    def create_table_without_fks(*args, **kwargs):
        if not args or not isinstance(args[0], str):
            return original_create_table(*args, **kwargs)

        table_name = args[0]
        source_schema = kwargs.get("schema")
        foreign_keys = [
            item for item in args[1:] if isinstance(item, ForeignKeyConstraint)
        ]
        deferred.extend(foreign_keys)

        inspector = sa_inspect(op.get_bind())
        if inspector.has_table(table_name, schema=source_schema):
            return None

        filtered_args = tuple(
            item for item in args if not isinstance(item, ForeignKeyConstraint)
        )
        return original_create_table(*filtered_args, **kwargs)

    def create_index_if_schema_compatible(*args, **kwargs):
        if not args or not isinstance(args[0], str):
            return original_create_index(*args, **kwargs)

        index_name = args[0]
        table_name = args[1] if len(args) > 1 else kwargs.get("table_name")
        columns = list(args[2:]) if len(args) > 2 else list(kwargs.get("columns", ()))
        schema = kwargs.get("schema")
        if not table_name:
            return original_create_index(*args, **kwargs)

        inspector = sa_inspect(op.get_bind())
        if not inspector.has_table(table_name, schema=schema):
            return None

        actual_columns = {
            item["name"] for item in inspector.get_columns(table_name, schema=schema)
        }
        if not set(columns).issubset(actual_columns):
            return None

        existing_indexes = inspector.get_indexes(table_name, schema=schema)
        if any(item.get("name") == index_name for item in existing_indexes):
            return None

        return original_create_index(*args, **kwargs)

    op.create_table = create_table_without_fks
    op.create_index = create_index_if_schema_compatible
    try:
        baseline.downgrade()
    finally:
        op.create_table = original_create_table
        op.create_index = original_create_index

    # All newly required tables now exist, so the foreign-key graph can be
    # restored safely even though the historical baseline emits tables in
    # reverse dependency order.
    for constraint in deferred:
        source_table = constraint.table.name
        source_schema = constraint.table.schema
        inspector = sa_inspect(op.get_bind())
        if not inspector.has_table(source_table, schema=source_schema):
            continue
        referent = constraint.referred_table
        if not inspector.has_table(
            referent.name, schema=referent.schema
        ):
            continue
        _create_deferred_foreign_key(constraint)


def downgrade() -> None:
    # Intentionally irreversible: the historical baseline upgrade body is
    # destructive cleanup for a populated database and must never be used as
    # an automatic rollback of the repaired canonical schema.
    pass
