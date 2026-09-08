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


def _deferred_fk_record(constraint: ForeignKeyConstraint, source_table: str, source_schema: str | None):
    """Capture FK metadata before Alembic/SQLAlchemy binds the constraint.

    Constraints supplied to ``op.create_table`` are not guaranteed to be bound
    to a Table object at interception time. Accessing ``constraint.table`` or
    ``element.parent`` at that point can therefore fail. ``column_keys`` keeps
    the local column names available without requiring a bound Table, while
    ``target_fullname`` retains the canonical remote column specification.
    """
    local_columns = list(constraint.column_keys)
    remote_specs = [element.target_fullname for element in constraint.elements]
    return {
        "name": constraint.name,
        "source_table": source_table,
        "source_schema": source_schema,
        "local_columns": local_columns,
        "remote_specs": remote_specs,
        "onupdate": constraint.onupdate,
        "ondelete": constraint.ondelete,
        "deferrable": constraint.deferrable,
        "initially": constraint.initially,
    }


def _parse_remote_spec(spec: str, default_schema: str | None):
    parts = spec.split(".")
    if len(parts) == 2:
        return default_schema, parts[0], parts[1]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError(f"Unsupported foreign-key target specification: {spec!r}")


def _create_deferred_foreign_key(record) -> None:
    source_table = record["source_table"]
    source_schema = record["source_schema"]
    remote = [_parse_remote_spec(spec, source_schema) for spec in record["remote_specs"]]
    referent_schema = remote[0][0]
    referent_table = remote[0][1]
    remote_columns = [item[2] for item in remote]

    if any(item[0] != referent_schema or item[1] != referent_table for item in remote):
        return

    inspector = sa_inspect(op.get_bind())
    if not inspector.has_table(source_table, schema=source_schema):
        return
    if not inspector.has_table(referent_table, schema=referent_schema):
        return

    existing = inspector.get_foreign_keys(source_table, schema=source_schema)
    if any(item.get("name") == record["name"] for item in existing):
        return

    actual_columns = {
        item["name"] for item in inspector.get_columns(source_table, schema=source_schema)
    }
    referent_columns = {
        item["name"]
        for item in inspector.get_columns(referent_table, schema=referent_schema)
    }
    if not set(record["local_columns"]).issubset(actual_columns):
        return
    if not set(remote_columns).issubset(referent_columns):
        return

    op.create_foreign_key(
        record["name"],
        source_table,
        referent_table,
        record["local_columns"],
        remote_columns,
        source_schema=source_schema,
        referent_schema=referent_schema,
        onupdate=record["onupdate"],
        ondelete=record["ondelete"],
        deferrable=record["deferrable"],
        initially=record["initially"],
    )


def _index_columns(args, kwargs):
    """Normalize Alembic's single-sequence index-column argument."""
    if len(args) > 2:
        raw = args[2]
    else:
        raw = kwargs.get("columns", ())
    if isinstance(raw, (list, tuple)):
        return list(raw)
    if raw is None:
        return []
    return [raw]


def upgrade() -> None:
    baseline = _load_baseline()
    deferred = []

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
        deferred.extend(
            _deferred_fk_record(item, table_name, source_schema)
            for item in foreign_keys
        )

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
        columns = _index_columns(args, kwargs)
        schema = kwargs.get("schema")
        if not table_name:
            return original_create_index(*args, **kwargs)

        inspector = sa_inspect(op.get_bind())
        if not inspector.has_table(table_name, schema=schema):
            return None

        actual_columns = {
            item["name"] for item in inspector.get_columns(table_name, schema=schema)
        }
        string_columns = {column for column in columns if isinstance(column, str)}
        if not string_columns.issubset(actual_columns):
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

    for record in deferred:
        _create_deferred_foreign_key(record)


def downgrade() -> None:
    # Intentionally irreversible: the historical baseline upgrade body is
    # destructive cleanup for a populated database and must never be used as
    # an automatic rollback of the repaired canonical schema.
    pass
