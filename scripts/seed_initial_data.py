#!/usr/bin/env python3
"""Script to seed initial data for VirtualStack.
This includes:
- Default permissions
- Default admin user
- Default tenant.
"""

import asyncio
import logging
from pathlib import Path
import sys


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.db import get_db, init_db
from virtualstack.models.iam.user import UserStatus
# Update imports to use the specific service modules
from virtualstack.services.iam.permission import permission_service
from virtualstack.services.iam.tenant import tenant_service
from virtualstack.services.iam.user import user_service
from virtualstack.schemas.iam.user import UserCreate
from virtualstack.schemas.iam.tenant import TenantCreate
from virtualstack.schemas.iam.permission import PermissionCreate


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define default permissions
DEFAULT_PERMISSIONS = [
    # IAM permissions
    {
        "key": "tenant.user.invite",
        "name": "Invite Users",
        "description": "Can invite users to the tenant",
    },
    {
        "key": "tenant.user.manage",
        "name": "Manage Users",
        "description": "Can manage users in the tenant",
    },
    {
        "key": "tenant.role.manage",
        "name": "Manage Roles",
        "description": "Can manage roles in the tenant",
    },
    # VM permissions
    {"key": "vm.read", "name": "View VMs", "description": "Can view VMs"},
    {"key": "vm.create", "name": "Create VMs", "description": "Can create VMs"},
    {"key": "vm.delete", "name": "Delete VMs", "description": "Can delete VMs"},
    {"key": "vm.power.manage", "name": "Power VMs", "description": "Can start/stop/restart VMs"},
    {
        "key": "vm.template.upload",
        "name": "Upload Templates",
        "description": "Can upload VM templates",
    },
    {
        "key": "vm.template.manage",
        "name": "Manage Templates",
        "description": "Can manage VM templates",
    },
    # Support permissions
    {
        "key": "support.ticket.create",
        "name": "Create Tickets",
        "description": "Can create support tickets",
    },
    {
        "key": "support.ticket.view",
        "name": "View Tickets",
        "description": "Can view support tickets",
    },
    # Billing permissions
    {"key": "billing.view", "name": "View Billing", "description": "Can view billing information"},
]

# Default admin user
DEFAULT_ADMIN = {
    "email": "admin@example.com",
    "password": "Password123!",
    "first_name": "Platform",
    "last_name": "Admin",
    "is_superuser": True,  # Updated from is_platform_admin
    "is_active": True,     # Updated from status
}

# Default tenant
DEFAULT_TENANT = {
    "name": "Default Tenant",
    "description": "Default tenant for demonstration purposes",
}


async def seed_permissions(db: AsyncSession) -> None:
    """Seed default permissions."""
    logger.info("Seeding permissions...")

    for permission_data in DEFAULT_PERMISSIONS:
        # Check if permission already exists by code instead of key
        existing = await permission_service.get_by_code(db, code=permission_data["key"])

        if existing:
            logger.info(f"Permission '{permission_data['key']}' already exists, skipping.")
            continue

        # Create permission using permission_service
        permission_in = PermissionCreate(
            name=permission_data["name"],
            code=permission_data["key"],  # Use key as code
            description=permission_data["description"],
            module=permission_data["key"].split(".")[0]  # Extract module from the key
        )
        await permission_service.create(db, obj_in=permission_in)
        logger.info(f"Created permission: {permission_data['key']}")


async def seed_admin_user(db: AsyncSession) -> None:
    """Seed default admin user."""
    logger.info("Seeding admin user...")

    # Check if admin user already exists
    existing = await user_service.get_by_email(db, email=DEFAULT_ADMIN["email"])

    if existing:
        logger.info(f"Admin user '{DEFAULT_ADMIN['email']}' already exists, skipping.")
        return

    # First, ensure we have a tenant for the admin user
    tenant = await tenant_service.get_by_name(db, name=DEFAULT_TENANT["name"])
    if not tenant:
        logger.info("Creating default tenant first...")
        tenant = await seed_default_tenant(db)
    
    # Create admin user using user_service
    user_in = UserCreate(
        email=DEFAULT_ADMIN["email"],
        password=DEFAULT_ADMIN["password"],
        first_name=DEFAULT_ADMIN["first_name"],
        last_name=DEFAULT_ADMIN["last_name"],
        is_superuser=DEFAULT_ADMIN["is_superuser"],
        is_active=DEFAULT_ADMIN["is_active"]
    )
    user = await user_service.create(db, obj_in=user_in, tenant_id=tenant.id)
    logger.info(f"Created admin user: {user.email}")
    return user


async def seed_default_tenant(db: AsyncSession) -> None:
    """Seed default tenant."""
    logger.info("Seeding default tenant...")

    # Check if tenant already exists
    existing = await tenant_service.get_by_name(db, name=DEFAULT_TENANT["name"])
    if existing:
        logger.info(f"Tenant '{DEFAULT_TENANT['name']}' already exists, skipping.")
        return existing

    # Create default tenant using tenant_service
    tenant_in = TenantCreate(
        name=DEFAULT_TENANT["name"],
        description=DEFAULT_TENANT["description"]
    )
    tenant = await tenant_service.create(db, obj_in=tenant_in)
    logger.info(f"Created default tenant: {tenant.name}")
    return tenant


async def seed_all() -> None:
    """Seed all initial data."""
    logger.info("Starting data seeding...")

    # Initialize database
    await init_db()

    # Get database session
    async for db in get_db():
        try:
            # Create the tenant first
            tenant = await seed_default_tenant(db)
            
            # Seed permissions
            await seed_permissions(db)

            # Seed admin user (needs tenant ID)
            await seed_admin_user(db)

            await db.commit()  # Ensure changes are committed
            logger.info("Data seeding completed successfully.")
            return  # Exit after first session
            
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error seeding data: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_all())
