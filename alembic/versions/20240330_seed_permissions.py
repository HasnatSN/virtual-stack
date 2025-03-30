"""Seed system permissions

Revision ID: 20240330_seed_permissions
Revises: 20240330_iam_tables
Create Date: 2024-03-30 16:10:00.000000

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20240330_seed_permissions'
down_revision: Union[str, None] = '20240330_iam_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define system permissions
SYSTEM_PERMISSIONS = [
    # Tenant permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View Tenants",
        "code": "tenant:read",
        "description": "Ability to view tenant information",
        "module": "tenant"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Create Tenant",
        "code": "tenant:create",
        "description": "Ability to create new tenants",
        "module": "tenant"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Update Tenant",
        "code": "tenant:update",
        "description": "Ability to update tenant information",
        "module": "tenant"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Delete Tenant",
        "code": "tenant:delete",
        "description": "Ability to delete tenants",
        "module": "tenant"
    },
    
    # User permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View Users",
        "code": "user:read",
        "description": "Ability to view user information",
        "module": "user"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Create User",
        "code": "user:create",
        "description": "Ability to create new users",
        "module": "user"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Update User",
        "code": "user:update",
        "description": "Ability to update user information",
        "module": "user"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Delete User",
        "code": "user:delete",
        "description": "Ability to delete users",
        "module": "user"
    },
    
    # Role permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View Roles",
        "code": "role:read",
        "description": "Ability to view role information",
        "module": "role"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Create Role",
        "code": "role:create",
        "description": "Ability to create new roles",
        "module": "role"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Update Role",
        "code": "role:update",
        "description": "Ability to update role information",
        "module": "role"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Delete Role",
        "code": "role:delete",
        "description": "Ability to delete roles",
        "module": "role"
    },
    
    # Permission permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View Permissions",
        "code": "permission:read",
        "description": "Ability to view permission information",
        "module": "permission"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Assign Permissions",
        "code": "permission:assign",
        "description": "Ability to assign permissions to roles",
        "module": "permission"
    },
    
    # VM permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View VMs",
        "code": "vm:read",
        "description": "Ability to view virtual machines",
        "module": "vm"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Create VM",
        "code": "vm:create",
        "description": "Ability to create new virtual machines",
        "module": "vm"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Update VM",
        "code": "vm:update",
        "description": "Ability to update virtual machines",
        "module": "vm"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Delete VM",
        "code": "vm:delete",
        "description": "Ability to delete virtual machines",
        "module": "vm"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Power VM",
        "code": "vm:power",
        "description": "Ability to power on/off virtual machines",
        "module": "vm"
    },
    
    # Template permissions
    {
        "id": str(uuid.uuid4()),
        "name": "View Templates",
        "code": "template:read",
        "description": "Ability to view templates",
        "module": "template"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Create Template",
        "code": "template:create",
        "description": "Ability to create new templates",
        "module": "template"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Update Template",
        "code": "template:update",
        "description": "Ability to update templates",
        "module": "template"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Delete Template",
        "code": "template:delete",
        "description": "Ability to delete templates",
        "module": "template"
    }
]


def upgrade() -> None:
    # Add created_at and updated_at
    now = datetime.utcnow()
    for permission in SYSTEM_PERMISSIONS:
        permission["created_at"] = now
        permission["updated_at"] = now
    
    # Insert permissions
    op.bulk_insert(
        sa.table(
            'permissions',
            sa.Column('id', postgresql.UUID(as_uuid=True)),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('updated_at', sa.DateTime()),
            sa.Column('name', sa.String(255)),
            sa.Column('code', sa.String(100)),
            sa.Column('description', sa.Text()),
            sa.Column('module', sa.String(100)),
            schema='iam'
        ),
        SYSTEM_PERMISSIONS
    )


def downgrade() -> None:
    # Delete permissions by code
    permission_codes = [p["code"] for p in SYSTEM_PERMISSIONS]
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM iam.permissions WHERE code IN :codes"
        ),
        {'codes': tuple(permission_codes)}
    ) 