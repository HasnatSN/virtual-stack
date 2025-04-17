"""Database initialization and seeding module."""
import logging
import re # Import regex for slugify
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.schemas.iam.tenant import TenantCreate
from virtualstack.schemas.iam.user import UserCreate
from virtualstack.schemas.iam.role import RoleCreate
from virtualstack.services.iam import tenant_service, user_service, role_service

logger = logging.getLogger(__name__)

# Track if we've already seeded in this process to prevent double-seeding with --reload
_HAS_SEEDED = False

# Simple slugify function
def slugify(value: str) -> str:
    """Converts string to lowercase, replaces spaces/underscores with hyphens."""
    value = re.sub(r'[\s_]+', '-', value.strip()).lower()
    # Optional: remove characters that are not alphanumeric or hyphen
    # value = re.sub(r'[^a-z0-9-]', '', value)
    return value

async def seed_initial_data(db: AsyncSession) -> dict:
    """Seeds initial data for the application (superuser, default tenant, etc.).
    
    Returns a dictionary with the created objects.
    """
    global _HAS_SEEDED
    
    # Skip if we've already seeded in this process (prevents double-seed with --reload)
    if _HAS_SEEDED:
        logger.info("[DEBUG SEED] Seed has already run in this process. Skipping.")
        return {}
        
    logger.info("[DEBUG SEED] Starting initial data seeding (DEBUG MODE - NO DB ACTIONS)")
    result = {}
    
    # --- Temporarily Comment Out DB Operations --- 
    # # Check if superuser already exists to avoid double-seeding even across processes
    # superuser = await user_service.get_by_email(db, email=settings.TEST_USER_EMAIL)
    # if superuser:
    #     logger.info(f"[DEBUG SEED] Superuser {settings.TEST_USER_EMAIL} already exists. Skipping DB seed actions.")
    #     result["superuser"] = superuser
    #     _HAS_SEEDED = True
    #     return result
    
    # # 1. Create default tenant if it doesn't exist
    # tenant = await tenant_service.get_by_name(db, name=settings.DEFAULT_TEST_TENANT_NAME)
    # if not tenant:
    #     logger.info(f"[DEBUG SEED] Creating default tenant: {settings.DEFAULT_TEST_TENANT_NAME}")
    #     tenant_in = TenantCreate(name=settings.DEFAULT_TEST_TENANT_NAME)
    #     tenant = await tenant_service.create(db, obj_in=tenant_in)
    #     logger.info(f"[DEBUG SEED] Default tenant created with ID: {tenant.id}")
    # else:
    #     logger.info(f"[DEBUG SEED] Default tenant {settings.DEFAULT_TEST_TENANT_NAME} already exists (ID: {tenant.id})")
    # result["tenant"] = tenant
    
    # # 2. Create superuser if it doesn't exist
    # if not superuser:
    #     logger.info(f"[DEBUG SEED] Creating superuser: {settings.TEST_USER_EMAIL}")
    #     user_in = UserCreate(
    #         email=settings.TEST_USER_EMAIL,
    #         password=settings.TEST_USER_PASSWORD,
    #         first_name="Super",
    #         last_name="User",
    #         is_superuser=True,
    #         is_active=True
    #     )
    #     # Ensure tenant exists for user creation
    #     if not tenant:
    #         logger.error("[DEBUG SEED] Cannot create superuser because default tenant doesn't exist!")
    #         _HAS_SEEDED = True # Mark as seeded to prevent retry
    #         return result # Exit early
    #     superuser = await user_service.create(db, obj_in=user_in, tenant_id=tenant.id)
    #     logger.info(f"[DEBUG SEED] Superuser created with ID: {superuser.id}")
    #     result["superuser"] = superuser

    # --- End Temporarily Commented Out Code --- 

    # Print status of session before returning to help debugging
    logger.debug(f"[DEBUG SEED] Session status (NO DB ACTIONS) - new: {len(db.new)}, dirty: {len(db.dirty)}, deleted: {len(db.deleted)}")
    
    # Mark as seeded
    _HAS_SEEDED = True
    logger.info("[DEBUG SEED] Finished initial data seeding (DEBUG MODE - NO DB ACTIONS)")
    return result

async def init_db() -> None:
    """Initialize the database, creating tables and indexes.
    
    Note: With Alembic, table creation should be handled by migrations.
    This function is kept for backwards compatibility.
    """
    logger.warning("init_db() is deprecated. Use Alembic migrations for schema management.")
    # Explicitly do nothing - all schema management should be through Alembic
    pass 