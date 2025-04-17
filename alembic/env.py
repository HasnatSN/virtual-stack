import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool, MetaData, text
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

# # Import models needed for Alembic to detect changes - REMOVED
# # Only import models that actually exist
# # It's crucial models are imported BEFORE Base.metadata is accessed below
# from virtualstack.models.iam import Tenant, User, Role, Permission, APIKey, Invitation, UserTenantRole  # noqa


# Define target_metadata using Base.metadata
target_metadata = Base.metadata
# Set the schema for target_metadata if it's not already set on Base
# This ensures Alembic knows where to look for tables defined without an explicit schema
# If your Base or models already define __table_args__ = {"schema": "iam"}, this might be redundant
# but it provides a fallback.
# target_metadata.schema = "iam" # Removed this - rely on include_object and version_table_schema

# Import models AFTER defining target_metadata if they contribute to it
# It's crucial models are imported BEFORE Base.metadata is used if they aren't automatically loaded
# Example (adjust based on your actual model locations):
# from virtualstack.models.iam import Tenant, User, Role, Permission, APIKey, Invitation, UserTenantRole  # noqa


# Define include_object to filter for the 'iam' schema
def include_object(object, name, type_, reflected, compare_to):
    """
    Include only objects within the 'iam' schema.
    Also include the alembic_version table regardless of its schema if needed,
    though version_table_schema='iam' should handle it.
    """
    if type_ == "schema" and name != "iam":
        print(f"DEBUG [alembic.env.py] Excluding schema: {name}")
        return False
    if type_ == "table":
        # Check if the table's schema is explicitly set and not 'iam'
        if hasattr(object, 'schema') and object.schema != "iam":
            print(f"DEBUG [alembic.env.py] Excluding table {name} with schema: {object.schema}")
            return False
        # If the table has no explicit schema, it might inherit from MetaData.
        # We rely on version_table_schema and the target_metadata association for implicit schema tables.
        # Allow tables with no schema defined or schema='iam'
        # Let alembic decide based on target_metadata association
        # print(f"DEBUG [alembic.env.py] Including table: {name} (schema: {getattr(object, 'schema', 'None')})")

    # Allow sequences, indexes, etc., associated with the 'iam' schema implicitly
    return True


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config # Define config earlier if needed globally

# Setup logging here if needed based on config
if config.config_file_name is not None:
     try:
         fileConfig(config.config_file_name)
     except Exception as e:
         print(f"Warning: Could not configure logging from {config.config_file_name}: {e}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # config = context.config # Already defined globally
    # Setup logging inside if preferred

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True, # Process schemas
        include_object=include_object, # Apply schema filtering
        version_table_schema="iam", # Explicitly set alembic_version schema
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Callback function to run migrations."""
    # config = context.config # Already defined globally
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True, # Process schemas
        include_object=include_object, # Apply schema filtering
        compare_type=True, # Enable type comparison
        version_table_schema="iam", # Explicitly set alembic_version schema
        # Ensure transactional_ddl=False if needed, default True is usually ok for Postgres
    )

    # Run migrations within the transaction managed by the caller (run_migrations_online)
    print("INFO [alembic.env.py/do_run_migrations] Running context.run_migrations()")
    context.run_migrations()
    print("INFO [alembic.env.py/do_run_migrations] Finished context.run_migrations()")


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    Uses VIRTUALSTACK_TEST_DB_URL environment variable if set,
    otherwise falls back to alembic.ini configuration.
    """
    # config = context.config # Already defined globally

    # Check for test DB URL environment variable
    test_db_url = os.getenv("VIRTUALSTACK_TEST_DB_URL")
    engine_config = config.get_section(config.config_ini_section)

    if test_db_url:
        print(f"INFO [alembic.env.py] Using test database URL from env var: {test_db_url}")
        # Use the test database URL provided via environment variable
        # Ensure we only pass the URL, not the whole original config section
        engine_config = {"sqlalchemy.url": test_db_url}
        # Remove pool settings if conflicting, use NullPool for tests
        engine_config.pop('sqlalchemy.poolclass', None)
        engine_config.pop('sqlalchemy.pool_size', None)
        # Add other necessary options if required, e.g., isolation level

        connectable = AsyncEngine(
            engine_from_config(
                engine_config, # Pass modified config
                prefix="sqlalchemy.",
                poolclass=pool.NullPool, # Use NullPool for tests
                future=True, # Required for SQLAlchemy 2.0 style
            )
        )
    else:
        # Use the configuration from alembic.ini (default behavior)
        print(f"INFO [alembic.env.py] Using database URL from alembic.ini: {engine_config.get('sqlalchemy.url')}")
        connectable = AsyncEngine(
            engine_from_config(
                engine_config, # Use original config from ini
                prefix="sqlalchemy.",
                poolclass=pool.NullPool, # Prefer NullPool even for non-test runs via script? Or keep original pool from ini? Let's keep NullPool for simplicity here.
                future=True, # Required for SQLAlchemy 2.0 style
            )
        )

    # Connect to the database
    async with connectable.connect() as connection:
        # Ensure the 'iam' schema exists before creating the version table
        print("INFO [alembic.env.py] Ensuring schema 'iam' exists before migrations...")
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS iam"))
        print("INFO [alembic.env.py] Schema 'iam' ensured")
        # Run the migrations within the connection's sync context
        print("INFO [alembic.env.py] Running migrations via connection.run_sync(do_run_migrations)...")
        await connection.run_sync(do_run_migrations)
        print("INFO [alembic.env.py] Finished connection.run_sync(do_run_migrations).")

    # Dispose of the engine
    print("INFO [alembic.env.py] Disposing connectable engine.")
    await connectable.dispose()
    print("INFO [alembic.env.py] Engine disposed.")


if context.is_offline_mode():
    print("INFO [alembic.env.py] Running migrations offline.")
    run_migrations_offline()
else:
    # This block is reached when running 'alembic upgrade head' directly from CLI.
    # It's NOT typically reached when calling alembic.command.upgrade programmatically,
    # as the command handles the setup and calls the necessary functions internally.
    # However, to be safe, ensure it calls the async function correctly if invoked this way.
    print("INFO [alembic.env.py] Running migrations online (likely CLI invocation).")
    # Check if an event loop is running, needed for direct script execution scenario
    try:
        loop = asyncio.get_running_loop()
        # If a loop is running (e.g., within pytest-asyncio), schedule the task
        # This might still cause issues if the calling context doesn't await properly.
        # Consider if just calling run_migrations_online() directly is better here,
        # assuming the direct CLI execution provides its own loop management.
        # Let's stick to the standard asyncio.run for direct script execution.
        # If run via `alembic upgrade head`, alembic handles the async call.
        asyncio.run(run_migrations_online())
    except RuntimeError: # No running event loop
        # If no loop is running (typical for direct `python alembic/env.py` execution, though not standard)
        asyncio.run(run_migrations_online())

# The programmatic call via alembic.command.upgrade(...) in conftest.py will
# use the configuration passed to it (including the potential connection or URL)
# and invoke the appropriate migration functions (like do_run_migrations)
# within its own managed context, potentially bypassing the run_migrations_online() above
# if a connection is directly provided or inferred differently by the command API.
# The modifications to run_migrations_online ensure that *if* it's called
# (e.g., as a fallback or by direct CLI), it respects the test environment variable.
# The crucial part for programmatic execution is how `alembic.command.upgrade` uses `do_run_migrations`.
