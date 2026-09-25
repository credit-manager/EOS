import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool

from alembic import context

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db import Base, engine as app_engine

# Import ALL models so Base.metadata knows about them
from backend.app.auth import models as _auth_models  # noqa: F401
from backend.app.metadata import models as _metadata_models  # noqa: F401
from backend.app.records import models as _records_models  # noqa: F401
from backend.app.financial import models as _financial_models  # noqa: F401
from backend.app.construction import models as _construction_models  # noqa: F401
from backend.app.workflow import models as _workflow_models  # noqa: F401
from backend.app.events import models as _events_models  # noqa: F401
from backend.app.rules import models as _rules_models  # noqa: F401
from backend.app.ai import models as _ai_models  # noqa: F401
from backend.app.ai.governance import models as _governance_models  # noqa: F401
from backend.app.documents import models as _documents_models  # noqa: F401
from backend.app.integrations import models as _integrations_models  # noqa: F401
from backend.app.globalization import models as _globalization_models  # noqa: F401
from backend.app.builder import models as _builder_models  # noqa: F401
from backend.app.marketplace import models as _marketplace_models  # noqa: F401
from backend.app.sdk import models as _sdk_models  # noqa: F401
from backend.app.retail import models as _retail_models  # noqa: F401
from backend.app.manufacturing import models as _manufacturing_models  # noqa: F401
from backend.app.notification import models as _notification_models  # noqa: F401
from backend.app.audit import models as _audit_models  # noqa: F401
from backend.app.policy import models as _policy_models  # noqa: F401
from backend.app.reporting import models as _reporting_models  # noqa: F401

config = context.config

# Override sqlalchemy.url from DATABASE_URL env var if set
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


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
    connectable = app_engine
    with connectable.connect() as connection:
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
