import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the project root is in sys.path for correct local module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pylon_service.db import Base  # Ensure all models are imported for Alembic autogenerate
from pylon_service.settings import settings

# Setup logging for this script
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("alembic.env")


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    logger.info("Alembic env.py: run_migrations_online() called.")
    connectable = create_async_engine(settings.pylon_db_uri, poolclass=pool.NullPool)
    logger.info(f"Alembic env.py: Created async engine for DB: {settings.pylon_db_uri}")

    def do_run_migrations_sync(connection):
        logger.info("Alembic env.py: do_run_migrations_sync() called.")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        logger.info("Alembic env.py: Context configured.")

        with context.begin_transaction():
            logger.info("Alembic env.py: Beginning transaction.")
            context.run_migrations()
            logger.info("Alembic env.py: context.run_migrations() finished.")
        logger.info("Alembic env.py: Transaction finished.")

    async def async_migration_runner():
        logger.info("Alembic env.py: async_migration_runner() started.")
        async with connectable.connect() as connection:
            logger.info("Alembic env.py: Acquired DB connection.")
            await connection.run_sync(do_run_migrations_sync)
            logger.info("Alembic env.py: run_sync(do_run_migrations_sync) finished.")
        await connectable.dispose()
        logger.info("Alembic env.py: DB connection disposed.")

    try:
        logger.info("Alembic env.py: Running async_migration_runner...")
        asyncio.run(async_migration_runner())
        logger.info("Alembic env.py: async_migration_runner finished successfully.")
    except Exception as e:
        logger.error(f"Alembic env.py: An error occurred during migrations: {e}", exc_info=True)
        raise


run_migrations_online()
