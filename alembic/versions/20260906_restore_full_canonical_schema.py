"""Restore the complete canonical schema from the historical baseline.

The historical 87aba7990b4d revision has its schema creation and teardown
bodies reversed.  Its ``downgrade`` body contains the canonical create
sequence, but also contains destructive drop/alter operations intended for a
previously populated schema.  This repair migration reuses only its create
operations and turns all destructive compatibility operations into no-ops.

The migration is additive and idempotent: compatibility migrations may have
already restored a subset of the canonical tables and indexes. Existing
objects are preserved and only missing objects are added.
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
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    source_table = constraint.table.name
    source_schema = constraint.table.schema
    referent_table = constraint.referred_table.name
    referent_schema = constraint.referred_table.schema

    table_names = set(inspector.get_table_names(schema=source_schema))
    referent_names = set(inspector.get_table_names(schema=referent_schema))
    if source_table not in table_names or referent_table not in referent_names:
        return

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
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = set(inspector.get_table_names())
    deferred_indexes: list[tuple[object, tuple, dict]] = []

    original_create_table = op.create_table
    original_create_index = op.create_index
    original_drop_index = op.drop_index
    original_drop_table = op.drop_table
    original_alter_column = op.alter_column

    def create_table_without_fks(*args, **kwargs):
        table_name = args[0]
        schema = kwargs.get("schema")
        foreign_keys = [item for item in args if isinstance(item, ForeignKeyConstraint)]
        deferred.extend(foreign_keys)

        if table_name in existing_tables:
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
        if not table_name:
            return original_create_index(index, *args, **kwargs)

        current_tables = set(sa_inspect(op.get_bind()).get_table_names(schema=schema))
        if table_name not in current_tables:
            deferred_indexes.append((index, args, kwargs))
            return None

        existing_indexes = sa_inspect(op.get_bind()).get_indexes(table_name, schema=schema)
        if index_name and any(item.get("name") == index_name for item in existing_indexes):
            return None
        return original_create_index(index, *args, **kwargs)

    # The historical body contains DROP/ALTER operations because the original
    # migration was generated with its direction inverted. Never allow those
    # operations to mutate an existing production-compatible schema here.
    def ignore_destructive_operation(*args, **kwargs):
        return None

    op.create_table = create_table_without_fks
    op.create_index = create_index_if_missing
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

    # Some canonical indexes are emitted before their tables by the historical
    # reversed body. Replay those indexes now that the full table set exists.
    for index, args, kwargs in deferred_indexes:
        table_name = args[0] if args else kwargs.get("table_name")
        schema = kwargs.get("schema")
        current_tables = set(sa_inspect(op.get_bind()).get_table_names(schema=schema))
        if table_name not in current_tables:
            continue
        index_name = index if isinstance(index, str) else getattr(index, "name", None)
        existing_indexes = sa_inspect(op.get_bind()).get_indexes(table_name, schema=schema)
        if index_name and any(item.get("name") == index_name for item in existing_indexes):
            continue
        original_create_index(index, *args, **kwargs)

    for constraint in deferred:
        _create_deferred_foreign_key(constraint)


def downgrade() -> None:
    # The historical baseline is not safe to use as an automatic rollback.
    pass
