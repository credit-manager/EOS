import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.audit.models import AuditEvent
from backend.app.auth.models import AuthSession, Tenant, TenantMembership, User
from backend.app.config import get_settings
from backend.app.construction.models import (
    BOQ,
    BOQItem,
    Contract,
    Procurement,
    ProcurementLine,
    ProgressClaim,
    ProgressClaimLine,
    Project,
)
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
    BOQ,
    BOQItem,
    Contract,
    JournalEntry,
    JournalLine,
    MetadataEntity,
    Procurement,
    ProcurementLine,
    ProgressClaim,
    ProgressClaimLine,
    Project,
    Record,
    Tenant,
    TenantMembership,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)


def _get_db_url() -> str:
    # Priority: command-line arg (-x db_url=...) > env var (DATABASE_URL) > alembic.ini > settings default
    cmd_line_url = config.get_main_option("db_url")
    if cmd_line_url:
        return cmd_line_url
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url
    return settings.database_url


def run_migrations_offline() -> None:
    url = _get_db_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    url = _get_db_url()
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
