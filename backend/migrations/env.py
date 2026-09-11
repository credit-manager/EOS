from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from backend.app.audit.models import AuditEvent
from backend.app.auth.models import AuthSession, Tenant, TenantMembership, User
from backend.app.config import get_settings
from backend.app.db import Base
from backend.app.financial.models import Account, JournalEntry, JournalLine
from backend.app.metadata.models import MetadataEntity
from backend.app.records.models import Record
from backend.app.workflow.models import ApprovalTask, WorkflowDefinition, WorkflowInstance

config = context.config
settings = get_settings()
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_model_registry = (
    Account,
    ApprovalTask,
    AuditEvent,
    AuthSession,
    JournalEntry,
    JournalLine,
    MetadataEntity,
    Record,
    Tenant,
    TenantMembership,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)


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
