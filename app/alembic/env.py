import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import Base  # Ensure all models are imported for Alembic autogenerate
from app.settings import settings

# Ensure the project root is in sys.path for correct local module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    connectable = create_async_engine(settings.pylon_db_uri, poolclass=pool.NullPool)

    def do_run_migrations_sync(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # autogenerate
            # include_schemas=True,  # multiple schemas
            # version_table_schema=target_metadata.schema, # if alembic_version table is in a schema
        )

        with context.begin_transaction():
            context.run_migrations()

    async def async_migration_runner():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations_sync)
        await connectable.dispose()

    asyncio.run(async_migration_runner())


run_migrations_online()
