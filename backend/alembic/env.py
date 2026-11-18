"""Alembic environment: where the migrations find the database and the models.

The URL comes from the database settings only (DATABASE_URL or POSTGRES_*), so
a migration runs without the application's other secrets. The target schema is
SQLModel.metadata, filled by importing every model.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers every table in SQLModel.metadata)
from app.core.database_settings import DatabaseSettings, load_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# "%" must be doubled for configparser (a password may contain one).
config.set_main_option(
    "sqlalchemy.url", load_settings(DatabaseSettings).sqlalchemy_database_url.replace("%", "%%")
)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Write the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run the migrations against the database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
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
