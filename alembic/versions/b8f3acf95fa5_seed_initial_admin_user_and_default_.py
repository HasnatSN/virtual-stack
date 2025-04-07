"""Seed initial admin user and default tenant

Revision ID: b8f3acf95fa5
Revises: 43ae6a20f723
Create Date: 2025-04-07 16:11:55.123456

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

from alembic import op

# Import password hashing function (adjust path if necessary)
from virtualstack.core.security import create_password_hash


# revision identifiers, used by Alembic.
revision: str = 'b8f3acf95fa5'
down_revision: Union[str, None] = '43ae6a20f723'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define table helpers for data insertion/deletion
# Note: Using helpers avoids needing full model imports in migrations
tenants_table = table(
    "tenants",
    column("id", postgresql.UUID(as_uuid=True)),
    column("name", sa.String),
    column("slug", sa.String),
    column("created_at", sa.DateTime),
    column("updated_at", sa.DateTime),
    column("is_active", sa.Boolean),
    schema="iam"
)

users_table = table(
    "users",
    column("id", postgresql.UUID(as_uuid=True)),
    column("email", sa.String),
    column("hashed_password", sa.String),
    column("is_superuser", sa.Boolean),
    column("is_active", sa.Boolean),
    column("created_at", sa.DateTime),
    column("updated_at", sa.DateTime),
    schema="iam"
)

tenant_roles_table = table(
    "tenant_roles",
    column("id", postgresql.UUID(as_uuid=True)),
    column("tenant_id", postgresql.UUID(as_uuid=True)),
    column("name", sa.String),
    column("description", sa.Text),
    column("is_system_role", sa.Boolean),
    column("created_at", sa.DateTime),
    column("updated_at", sa.DateTime),
    schema="iam"
)

user_tenant_roles_table = table(
    "user_tenant_roles",
    column("id", postgresql.UUID(as_uuid=True)),
    column("user_id", postgresql.UUID(as_uuid=True)),
    column("tenant_id", postgresql.UUID(as_uuid=True)),
    column("tenant_role_id", postgresql.UUID(as_uuid=True)),
    column("created_at", sa.DateTime),
    column("updated_at", sa.DateTime),
    schema="iam"
)

# --- Define Seed Data --- 
DEFAULT_TENANT_ID = str(uuid.uuid4())
DEFAULT_TENANT_SLUG = "default-tenant"
DEFAULT_ADMIN_ID = str(uuid.uuid4())
DEFAULT_ADMIN_EMAIL = "admin@example.com" # Match test script
DEFAULT_ADMIN_PASSWORD = "changeme" # Match test script
DEFAULT_ADMIN_ROLE_ID = str(uuid.uuid4()) # New constant for the role ID
DEFAULT_ADMIN_ROLE_NAME = "Admin"


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()

    # 1. Create Default Tenant
    op.bulk_insert(
        tenants_table,
        [
            {
                "id": DEFAULT_TENANT_ID,
                "name": "Default Tenant",
                "slug": DEFAULT_TENANT_SLUG,
                "created_at": now,
                "updated_at": now,
                "is_active": True,
            }
        ],
    )

    # 2. Create Default Admin Role for the Tenant
    op.bulk_insert(
        tenant_roles_table,
        [
            {
                "id": DEFAULT_ADMIN_ROLE_ID,
                "tenant_id": DEFAULT_TENANT_ID,
                "name": DEFAULT_ADMIN_ROLE_NAME,
                "description": "Default administrator role for the tenant",
                "is_system_role": False, # Or True if appropriate
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    # 3. Create Admin User
    hashed_password = create_password_hash(DEFAULT_ADMIN_PASSWORD)
    op.bulk_insert(
        users_table,
        [
            {
                "id": DEFAULT_ADMIN_ID,
                "email": DEFAULT_ADMIN_EMAIL,
                "hashed_password": hashed_password,
                "is_superuser": True, # Keep as superuser for now
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    # 4. Associate Admin User with Default Tenant and Default Admin Role
    op.bulk_insert(
        user_tenant_roles_table,
        [
            {
                "id": str(uuid.uuid4()),
                "user_id": DEFAULT_ADMIN_ID,
                "tenant_id": DEFAULT_TENANT_ID,
                "tenant_role_id": DEFAULT_ADMIN_ROLE_ID, # Use the created role ID
                "created_at": now,
                "updated_at": now
            }
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Delete in reverse order (association, user, role, tenant)
    # Safest to delete by known IDs

    op.execute(
        user_tenant_roles_table.delete().where(
            user_tenant_roles_table.c.user_id == DEFAULT_ADMIN_ID
        ).where(
            user_tenant_roles_table.c.tenant_id == DEFAULT_TENANT_ID
        )
    )

    op.execute(
        users_table.delete().where(users_table.c.id == DEFAULT_ADMIN_ID)
    )

    op.execute(
        tenant_roles_table.delete().where(tenant_roles_table.c.id == DEFAULT_ADMIN_ROLE_ID)
    )

    op.execute(
        tenants_table.delete().where(tenants_table.c.id == DEFAULT_TENANT_ID)
    ) 