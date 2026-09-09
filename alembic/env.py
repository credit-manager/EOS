from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, inspect as sa_inspect
from alembic import context, op
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

config = context.config

# The historical baseline was generated from a populated EOS database. It
# contains cleanup/alter operations for tables that do not exist on a clean
# installation, followed later by the CREATE TABLE statements for the
# canonical schema. Keep that migration intact, but make references to
# pre-existing-only objects conditional on their actual presence.
_original_ops = {
    name: getattr(op, name)
    for name in (
        "add_column",
        "drop_column",
        "alter_column",
        "create_index",
        "drop_index",
        "drop_table",
        "drop_constraint",
        "create_foreign_key",
        "create_primary_key",
        "create_check_constraint",
        "create_unique_constraint",
        "create_exclude_constraint",
        "create_table",
    )
}

_known_tables = None


def _table_exists(table_name, schema=None):
    global _known_tables
    if context.is_offline_mode():
        return True
    if _known_tables is None:
        _known_tables = set(sa_inspect(op.get_bind()).get_table_names(schema=schema))
    return table_name in _known_tables


def _mark_created(table_name):
    if _known_tables is not None:
        _known_tables.add(table_name)


def _mark_dropped(table_name):
    if _known_tables is not None:
        _known_tables.discard(table_name)


def _table_name_from_args(args, kw, position=0):
    if len(args) > position:
        return args[position], kw.get("schema")
    return kw.get("table_name"), kw.get("schema")


def _guard_table_operation(name, table_position):
    original = _original_ops[name]

    def guarded(*args, **kw):
        table_name, schema = _table_name_from_args(args, kw, table_position)
        if table_name and not _table_exists(table_name, schema):
            return None
        return original(*args, **kw)

    return guarded


# Operations whose target table may legitimately be absent on a fresh DB.
op.add_column = _guard_table_operation("add_column", 0)
op.drop_column = _guard_table_operation("drop_column", 0)
op.alter_column = _guard_table_operation("alter_column", 0)
op.drop_constraint = _guard_table_operation("drop_constraint", 1)
op.create_primary_key = _guard_table_operation("create_primary_key", 1)
op.create_check_constraint = _guard_table_operation("create_check_constraint", 1)
op.create_unique_constraint = _guard_table_operation("create_unique_constraint", 1)
op.create_exclude_constraint = _guard_table_operation("create_exclude_constraint", 1)
op.create_index = _guard_table_operation("create_index", 1)

_original_drop_index = _original_ops["drop_index"]


def _safe_drop_index(index_name, table_name=None, schema=None, **kw):
    # Index cleanup is safe when either the table or index is already absent.
    if table_name and not _table_exists(table_name, schema):
        return None
    kw.setdefault("if_exists", True)
    return _original_drop_index(index_name, table_name, schema=schema, **kw)


op.drop_index = _safe_drop_index

_original_drop_table = _original_ops["drop_table"]


def _safe_drop_table(table_name, schema=None, **kw):
    if not _table_exists(table_name, schema):
        return None
    result = _original_drop_table(table_name, schema=schema, **kw)
    _mark_dropped(table_name)
    return result


op.drop_table = _safe_drop_table

_original_create_table = _original_ops["create_table"]


def _safe_create_table(*args, **kw):
    table_name, schema = _table_name_from_args(args, kw, 0)
    if table_name and _table_exists(table_name, schema):
        return None
    result = _original_create_table(*args, **kw)
    if table_name:
        _mark_created(table_name)
    return result


op.create_table = _safe_create_table

_original_create_fk = _original_ops["create_foreign_key"]


def _safe_create_fk(*args, **kw):
    source = args[1] if len(args) > 1 else kw.get("source_table")
    referent = args[2] if len(args) > 2 else kw.get("referent_table")
    schema = kw.get("source_schema") or kw.get("schema")
    referent_schema = kw.get("referent_schema") or schema
    if source and not _table_exists(source, schema):
        return None
    if referent and not _table_exists(referent, referent_schema):
        return None
    return _original_create_fk(*args, **kw)


op.create_foreign_key = _safe_create_fk


def _ensure_alembic_version_table(connection):
    """Keep Alembic's version column wide enough for EOS revision IDs."""
    connection.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(255) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
        """
    )
    connection.exec_driver_sql(
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
    )
    # SQLAlchemy 2.x autobegins a transaction for the DDL above. Commit it
    # before Alembic starts its own migration transaction; otherwise the
    # compatibility DDL (and the migration transaction nested after it) can
    # be rolled back when the connection closes on a fresh database.
    connection.commit()


db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models to ensure they are registered with Base.metadata
try:
    from models import Base
    import models  # noqa: F401
    try:
        from core import builder_engine, ai_composer, metadata_engine  # noqa: F401
    except ImportError:
        pass
    target_metadata = Base.metadata
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_alembic_version_table(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
