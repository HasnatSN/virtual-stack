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
from virtualstack.services.iam_service import (
    create_permission,
    create_tenant,
    create_user,
    get_permission_by_key,
    get_user_by_email,
)


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
    "is_platform_admin": True,
    "status": UserStatus.ACTIVE,
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
        # Check if permission already exists
        existing = await get_permission_by_key(db, permission_data["key"])

        if existing:
            logger.info(f"Permission '{permission_data['key']}' already exists, skipping.")
            continue

        # Create permission
        await create_permission(
            db,
            key=permission_data["key"],
            name=permission_data["name"],
            description=permission_data["description"],
        )
        logger.info(f"Created permission: {permission_data['key']}")


async def seed_admin_user(db: AsyncSession) -> None:
    """Seed default admin user."""
    logger.info("Seeding admin user...")

    # Check if admin user already exists
    existing = await get_user_by_email(db, DEFAULT_ADMIN["email"])

    if existing:
        logger.info(f"Admin user '{DEFAULT_ADMIN['email']}' already exists, skipping.")
        return

    # Create admin user
    user = await create_user(
        db,
        email=DEFAULT_ADMIN["email"],
        password=DEFAULT_ADMIN["password"],
        first_name=DEFAULT_ADMIN["first_name"],
        last_name=DEFAULT_ADMIN["last_name"],
        is_platform_admin=DEFAULT_ADMIN["is_platform_admin"],
        status=DEFAULT_ADMIN["status"],
    )
    logger.info(f"Created admin user: {user.email}")


async def seed_default_tenant(db: AsyncSession) -> None:
    """Seed default tenant."""
    logger.info("Seeding default tenant...")

    # Create default tenant
    tenant = await create_tenant(
        db,
        name=DEFAULT_TENANT["name"],
        description=DEFAULT_TENANT["description"],
    )
    logger.info(f"Created default tenant: {tenant.name}")


async def seed_all() -> None:
    """Seed all initial data."""
    logger.info("Starting data seeding...")

    # Initialize database
    await init_db()

    # Get database session
    async for db in get_db():
        try:
            # Seed permissions
            await seed_permissions(db)

            # Seed admin user
            await seed_admin_user(db)

            # Seed default tenant
            await seed_default_tenant(db)

            logger.info("Data seeding completed successfully.")
        except Exception as e:
            logger.exception(f"Error seeding data: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_all())
