import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the backend app to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db import Base

# Import ALL models so Base.metadata knows about them
from app.auth import models as auth_models  # noqa: F401
from app.notification import models as notif_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.audit import models as audit_models  # noqa: F401
from app.billing import models as billing_models  # noqa: F401
from app.builder import models as builder_models  # noqa: F401
from app.construction import models as construction_models  # noqa: F401
from app.documents import models as document_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.financial import models as financial_models  # noqa: F401
from app.feature_flags import models as feature_flag_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
