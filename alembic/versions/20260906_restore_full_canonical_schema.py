"""Restore missing canonical schema objects without rewriting newer tables.

The historical baseline is known to contain a reversed migration body.  Its
``downgrade`` contains the canonical CREATE sequence, but that sequence can
also contain indexes/foreign keys for columns whose tables were later given a
newer shape.  This repair migration therefore treats the baseline as a source
of *optional* missing objects only: existing tables are never replaced and
DDL is emitted only when its referenced columns/objects actually exist.
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


def _existing_columns(inspector, table_name: str, schema: str | None) -> set[str]:
    return {item["name"] for item in inspector.get_columns(table_name, schema=schema)}


def _create_deferred_foreign_key(constraint: ForeignKeyConstraint) -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    source_table = constraint.table.name
    source_schema = constraint.table.schema
    referent_table = constraint.referred_table.name
    referent_schema = constraint.referred_table.schema

    if source_table not in set(inspector.get_table_names(schema=source_schema)):
        return
    if referent_table not in set(inspector.get_table_names(schema=referent_schema)):
        return

    source_columns = _existing_columns(inspector, source_table, source_schema)
    referent_columns = _existing_columns(inspector, referent_table, referent_schema)
    local_columns = [element.parent.name for element in constraint.elements]
    remote_columns = [element.column.name for element in constraint.elements]
    if not set(local_columns).issubset(source_columns):
        return
    if not set(remote_columns).issubset(referent_columns):
        return

    existing = inspector.get_foreign_keys(source_table, schema=source_schema)
    if any(item.get("name") == constraint.name for item in existing):
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


def _index_columns(index, args: tuple, kwargs: dict) -> set[str]:
    columns = getattr(index, "columns", None)
    if columns is not None:
        try:
            return {column.name for column in columns}
        except (AttributeError, TypeError):
            pass

    # Alembic's generated calls normally use:
    #   op.create_index(name, table_name, ["column", ...], ...)
    # so the column list is args[1] when the index name is a string.
    if len(args) > 1 and isinstance(args[1], (list, tuple)):
        return {getattr(column, "name", str(column)) for column in args[1]}
    if "columns" in kwargs and isinstance(kwargs["columns"], (list, tuple)):
        return {getattr(column, "name", str(column)) for column in kwargs["columns"]}
    return set()


def _safe_create_index(original_create_index, index, args: tuple, kwargs: dict, deferred_indexes: list) -> None:
    table_name = args[0] if args else kwargs.get("table_name")
    schema = kwargs.get("schema")
    if not table_name:
        original_create_index(index, *args, **kwargs)
        return

    inspector = sa_inspect(op.get_bind())
    tables = set(inspector.get_table_names(schema=schema))
    if table_name not in tables:
        deferred_indexes.append((index, args, kwargs))
        return

    index_name = index if isinstance(index, str) else getattr(index, "name", None)
    if index_name and any(
        item.get("name") == index_name
        for item in inspector.get_indexes(table_name, schema=schema)
    ):
        return

    required = _index_columns(index, args, kwargs)
    if required and not required.issubset(_existing_columns(inspector, table_name, schema)):
        # The table exists but its newer canonical shape intentionally does
        # not expose this historical index's columns. Do not mutate it here.
        return

    original_create_index(index, *args, **kwargs)


def upgrade() -> None:
    baseline = _load_baseline()
    deferred_indexes: list[tuple[object, tuple, dict]] = []
    deferred_fks: list[ForeignKeyConstraint] = []

    original_create_table = op.create_table
    original_create_index = op.create_index
    original_drop_index = op.drop_index
    original_drop_table = op.drop_table
    original_alter_column = op.alter_column

    def create_table_without_fks(*args, **kwargs):
        table_name = args[0]
        schema = kwargs.get("schema")
        inspector = sa_inspect(op.get_bind())
        if table_name in set(inspector.get_table_names(schema=schema)):
            return None

        for item in args:
            if isinstance(item, ForeignKeyConstraint):
                deferred_fks.append(item)
        filtered_args = tuple(item for item in args if not isinstance(item, ForeignKeyConstraint))
        return original_create_table(*filtered_args, **kwargs)

    def create_index_if_safe(index, *args, **kwargs):
        _safe_create_index(original_create_index, index, args, kwargs, deferred_indexes)

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

    for index, args, kwargs in deferred_indexes:
        _safe_create_index(original_create_index, index, args, kwargs, [])

    for constraint in deferred_fks:
        _create_deferred_foreign_key(constraint)


def downgrade() -> None:
    # The historical baseline contains destructive operations and is not a
    # safe automatic rollback target. Production rollback is restore-based.
    pass
