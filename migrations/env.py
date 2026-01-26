
"""Alembic environment configuration.

This env.py avoids passing a URL containing percent-encoded characters (e.g. %40)
through Python's configparser via Alembic Config.set_main_option(), which can
raise interpolation errors. Instead, it reads the SQLALCHEMY_DATABASE_URI from
the Flask app config and passes it directly to SQLAlchemy/Alembic.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Add repository root to sys.path so imports work when Alembic runs
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

# Alembic Config object, which provides access to values within alembic.ini
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build Flask app and read database URL from the same config used by the app.
app = create_app()
with app.app_context():
    DATABASE_URL: str | None = app.config.get("SQLALCHEMY_DATABASE_URI")

# Fallback to alembic.ini only if Flask didn't provide a URL.
if not DATABASE_URL:
    DATABASE_URL = config.get_main_option("sqlalchemy.url")

# Target metadata for 'autogenerate' support
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In offline mode we configure Alembic with just the URL.
    """
    url = DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is not configured for Alembic migrations")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In online mode we create an Engine and associate a connection with Alembic.
    """
    url = DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is not configured for Alembic migrations")

    connectable = create_engine(url, poolclass=NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()