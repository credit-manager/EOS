"""Restore the canonical baseline schema without destructive compatibility work.

The historical ``87aba7990b4d`` revision contains its canonical create body in
``downgrade``.  This repair migration replays that body while making creation
idempotent and refusing to mutate existing tables.  Existing compatibility
migrations can therefore coexist with the historical baseline.
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
    inspector = sa_inspect(op.get_bind())
    source_table = constraint.table.name
    source_schema = constraint.table.schema
    referent_table = constraint.referred_table.name
    referent_schema = constraint.referred_table.schema

    if source_table not in inspector.get_table_names(schema=source_schema):
        return
    if referent_table not in inspector.get_table_names(schema=referent_schema):
        return

    source_columns = {c["name"] for c in inspector.get_columns(source_table, schema=source_schema)}
    referent_columns = {c["name"] for c in inspector.get_columns(referent_table, schema=referent_schema)}
    local_columns = [element.parent.name for element in constraint.elements]
    remote_columns = [element.column.name for element in constraint.elements]
    if not set(local_columns).issubset(source_columns):
        return
    if not set(remote_columns).issubset(referent_columns):
        return

    existing = inspector.get_foreign_keys(source_table, schema=source_schema)
    if constraint.name and any(item.get("name") == constraint.name for item in existing):
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
    deferred_fks: list[ForeignKeyConstraint] = []
    deferred_indexes: list[tuple[object, tuple, dict]] = []

    original_create_table = op.create_table
    original_create_index = op.create_index
    original_drop_index = op.drop_index
    original_drop_table = op.drop_table
    original_alter_column = op.alter_column

    def create_table_without_fks(*args, **kwargs):
        table_name = args[0]
        foreign_keys = [item for item in args if isinstance(item, ForeignKeyConstraint)]
        deferred_fks.extend(foreign_keys)

        inspector = sa_inspect(op.get_bind())
        if table_name in inspector.get_table_names(schema=kwargs.get("schema")):
            return None

        filtered_args = tuple(item for item in args if not isinstance(item, ForeignKeyConstraint))
        return original_create_table(*filtered_args, **kwargs)

    def create_index_if_safe(index, *args, **kwargs):
        table_name = args[0] if args else kwargs.get("table_name")
        schema = kwargs.get("schema")
        if not table_name:
            return original_create_index(index, *args, **kwargs)

        inspector = sa_inspect(op.get_bind())
        if table_name not in inspector.get_table_names(schema=schema):
            deferred_indexes.append((index, args, kwargs))
            return None

        index_name = index if isinstance(index, str) else getattr(index, "name", None)
        existing = inspector.get_indexes(table_name, schema=schema)
        if index_name and any(item.get("name") == index_name for item in existing):
            return None

        # A historical index can target a column that a prior compatibility
        # migration intentionally created under a different canonical shape.
        # Never issue DDL against such a table: preserve the existing contract
        # and let the dedicated compatibility migration own its evolution.
        index_columns = getattr(index, "columns", None)
        if index_columns is not None:
            required = {column.name for column in index_columns}
            actual = {column["name"] for column in inspector.get_columns(table_name, schema=schema)}
            if not required.issubset(actual):
                return None
        return original_create_index(index, *args, **kwargs)

    def ignore_destructive_operation(*args, **kwargs):
        return None

    op.create_table = create_table_without_fks
    op.create_index = create_index_if_safe
    op.drop_index = ignore_destructive_operation
    op.drop_table = ignore_destructive_operation
    op.alter_column = ignore_destructive_operation
    try:
        baseline.downgrade()
    finally:
        op.create_table = original_create_table
        op.create_index = original_create_index
        op.drop_index = original_drop_index
        op.drop_table = original_drop_table
        op.alter_column = original_alter_column

    # Revisit indexes that were emitted before their tables existed.  The same
    # safety checks apply, including the actual-column check above.
    for index, args, kwargs in deferred_indexes:
        table_name = args[0] if args else kwargs.get("table_name")
        schema = kwargs.get("schema")
        inspector = sa_inspect(op.get_bind())
        if table_name not in inspector.get_table_names(schema=schema):
            continue
        index_name = index if isinstance(index, str) else getattr(index, "name", None)
        if index_name and any(item.get("name") == index_name for item in inspector.get_indexes(table_name, schema=schema)):
            continue
        index_columns = getattr(index, "columns", None)
        if index_columns is not None:
            required = {column.name for column in index_columns}
            actual = {column["name"] for column in inspector.get_columns(table_name, schema=schema)}
            if not required.issubset(actual):
                continue
        original_create_index(index, *args, **kwargs)

    for constraint in deferred_fks:
        _create_deferred_foreign_key(constraint)


def downgrade() -> None:
    # Automatic downgrade is intentionally disabled: the historical baseline
    # contains destructive operations that are unsafe for production rollback.
    pass
