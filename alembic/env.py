import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context


# Ensure the src directory is in the Python path
# This allows Alembic to find the virtualstack module
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

# Import the Base model
# Use relative import path if Base is now accessible
# Import MetaData
from sqlalchemy import MetaData

from virtualstack.db.base import Base

# Import models needed for Alembic to detect changes
# Only import models that actually exist
from virtualstack.models import Permission, Tenant, User  # noqa: F401

# Import the specific model we added a column to, to ensure it's loaded
from virtualstack.models.iam.api_key import APIKey  # noqa: F401


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Use Base.metadata initially to load models, then create a new MetaData specific to the schema
# target_metadata = Base.metadata
# Explicitly target the 'iam' schema
target_metadata = MetaData(schema="iam")

# Manually assign tables from Base.metadata that belong to the 'iam' schema
for table in Base.metadata.tables.values():
    if table.schema == "iam":
        table.tometadata(target_metadata)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Add schema name for autogenerate
def include_object(object, name, type_, reflected, compare_to):
    return not (type_ == "table" and object.schema != "iam")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,  # Ensure schema is considered
        # include_object=include_object # Ensure only iam schema is considered
        version_table_schema="public",  # Explicitly set alembic_version schema
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,  # Ensure schema is considered
        # include_object=include_object # Ensure only iam schema is considered
        version_table_schema="public",  # Explicitly set alembic_version schema
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        # Explicitly configure context within online mode for autogenerate
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,  # Ensure schema is considered
            # include_object=include_object # Ensure only iam schema is considered
            compare_type=True,  # Enable type comparison
            version_table_schema="public",  # Explicitly set alembic_version schema
        )

        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
