from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.audit.models import AuditEvent
from backend.app.auth.models import Tenant, TenantMembership, User
from backend.app.config import get_settings
from backend.app.db import Base
from backend.app.metadata.models import MetadataEntity
from backend.app.records.models import Record

config = context.config
settings = get_settings()
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_model_registry = (AuditEvent, MetadataEntity, Record, Tenant, TenantMembership, User)


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = settings.database_url
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
