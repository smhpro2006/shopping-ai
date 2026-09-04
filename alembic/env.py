from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Pull DATABASE_URL and Base from the app — this is the single source of truth
# for both the migration engine and the autogenerate metadata scan.
from backend.app.core.config import DATABASE_URL
from backend.app.core.database import Base  # noqa: F401 — side-effect: registers all models

# Import every model so Base.metadata is fully populated before autogenerate runs.
import backend.app.models.product     # noqa: F401
import backend.app.models.retailer    # noqa: F401
import backend.app.models.offer       # noqa: F401
import backend.app.models.user        # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the URL from alembic.ini with the one from app settings.
# This means alembic always uses the same DATABASE_URL as the running app,
# whether that's SQLite locally or Postgres on Railway.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
