"""Restore missing canonical schema objects without rewriting newer tables.

The historical baseline contains a reversed migration body. Its downgrade
contains the canonical CREATE sequence, but its SQLAlchemy FK objects may not
be fully bound while the table is being replayed. This repair migration
captures only stable DDL metadata and applies it after all tables exist.
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


def _capture_foreign_key(constraint: ForeignKeyConstraint) -> tuple | None:
    """Capture FK metadata without dereferencing unbound SQLAlchemy columns."""
    local_columns: list[str] = []
    remote_columns: list[str] = []
    for element in constraint.elements:
        parent = getattr(element, "parent", None)
        target_fullname = getattr(element, "_colspec", None)
        if parent is None or not target_fullname:
            return None
        local_columns.append(parent.name)
        remote_name = str(target_fullname).rsplit(".", 1)[-1]
        remote_columns.append(remote_name)

    referred_table = getattr(constraint, "referred_table", None)
    source_table = getattr(constraint, "table", None)
    if source_table is None or referred_table is None:
        return None

    return (
        constraint.name,
        source_table.name,
        source_table.schema,
        referred_table.name,
        referred_table.schema,
        tuple(local_columns),
        tuple(remote_columns),
        constraint.onupdate,
        constraint.ondelete,
        constraint.deferrable,
        constraint.initially,
    )


def _create_deferred_foreign_key(original_create_foreign_key, metadata: tuple) -> None:
    (
        constraint_name, source_table, source_schema, referent_table,
        referent_schema, local_columns, remote_columns, onupdate, ondelete,
        deferrable, initially,
    ) = metadata
    inspector = sa_inspect(op.get_bind())
    if source_table not in set(inspector.get_table_names(schema=source_schema)):
        return
    if referent_table not in set(inspector.get_table_names(schema=referent_schema)):
        return

    if not set(local_columns).issubset(_existing_columns(inspector, source_table, source_schema)):
        return
    if not set(remote_columns).issubset(_existing_columns(inspector, referent_table, referent_schema)):
        return
    if any(item.get("name") == constraint_name for item in inspector.get_foreign_keys(source_table, schema=source_schema)):
        return

    original_create_foreign_key(
        constraint_name, source_table, referent_table,
        list(local_columns), list(remote_columns),
        source_schema=source_schema, referent_schema=referent_schema,
        onupdate=onupdate, ondelete=ondelete,
        deferrable=deferrable, initially=initially,
    )


def _index_columns(index, args: tuple, kwargs: dict) -> set[str]:
    columns = getattr(index, "columns", None)
    if columns is not None:
        try:
            return {column.name for column in columns}
        except (AttributeError, TypeError):
            pass
    if len(args) > 1 and isinstance(args[1], (list, tuple)):
        return {getattr(column, "name", str(column)) for column in args[1]}
    if isinstance(kwargs.get("columns"), (list, tuple)):
        return {getattr(column, "name", str(column)) for column in kwargs["columns"]}
    return set()


def _safe_create_index(original_create_index, index, args: tuple, kwargs: dict, deferred_indexes: list) -> None:
    table_name = args[0] if args else kwargs.get("table_name")
    schema = kwargs.get("schema")
    if not table_name:
        original_create_index(index, *args, **kwargs)
        return
    inspector = sa_inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names(schema=schema)):
        deferred_indexes.append((index, args, kwargs))
        return
    index_name = index if isinstance(index, str) else getattr(index, "name", None)
    if index_name and any(item.get("name") == index_name for item in inspector.get_indexes(table_name, schema=schema)):
        return
    required = _index_columns(index, args, kwargs)
    if required and not required.issubset(_existing_columns(inspector, table_name, schema)):
        return
    original_create_index(index, *args, **kwargs)


def upgrade() -> None:
    baseline = _load_baseline()
    deferred_indexes: list[tuple[object, tuple, dict]] = []
    deferred_fks: list[tuple] = []
    original_create_table = op.create_table
    original_create_index = op.create_index
    original_create_foreign_key = op.create_foreign_key
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
                metadata = _capture_foreign_key(item)
                if metadata is not None:
                    deferred_fks.append(metadata)
        filtered_args = tuple(item for item in args if not isinstance(item, ForeignKeyConstraint))
        return original_create_table(*filtered_args, **kwargs)

    op.create_table = create_table_without_fks
    op.create_index = lambda index, *args, **kwargs: _safe_create_index(original_create_index, index, args, kwargs, deferred_indexes)
    op.create_foreign_key = lambda *args, **kwargs: None
    op.drop_index = lambda *args, **kwargs: None
    op.drop_table = lambda *args, **kwargs: None
    op.alter_column = lambda *args, **kwargs: None
    try:
        baseline.downgrade()
    finally:
        op.create_table = original_create_table
        op.create_index = original_create_index
        op.create_foreign_key = original_create_foreign_key
        op.drop_index = original_drop_index
        op.drop_table = original_drop_table
        op.alter_column = original_alter_column

    for index, args, kwargs in deferred_indexes:
        _safe_create_index(original_create_index, index, args, kwargs, [])
    for metadata in deferred_fks:
        _create_deferred_foreign_key(original_create_foreign_key, metadata)


def downgrade() -> None:
    # Production rollback is restore-based; never replay the destructive legacy baseline.
    pass
