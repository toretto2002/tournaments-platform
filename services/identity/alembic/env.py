"""Alembic env.py — versione ASYNC.

Usa un async engine (asyncpg) e legge DATABASE_URL dalla stessa fonte di
verita' dell'app a runtime (app.config.get_settings(), che risolve .env),
invece di duplicare la connection string in alembic.ini.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.db import Base

# Import dei modelli: registrano le loro Table su Base.metadata, necessario
# perche' target_metadata (sotto) sia completo per l'autogenerate.
from app.models import Outbox, RefreshToken, User, UserRole  # noqa: F401

# Oggetto Config di Alembic, da alembic.ini.
config = context.config

# Setup del logging da alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata usata dall'autogenerate per confrontare modelli <-> DB.
target_metadata = Base.metadata

# Sovrascrive sqlalchemy.url (lasciato vuoto in alembic.ini di proposito)
# con DATABASE_URL dell'app: stessa fonte di verita' usata a runtime.
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)


def run_migrations_offline() -> None:
    """Migration in modalita' 'offline': emette SQL senza connettersi al DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crea un async Engine e associa una connessione al context di Alembic."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Migration in modalita' 'online': esegue le migration sul DB reale."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
