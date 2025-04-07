from enum import Enum
from typing import Optional, List
from uuid import UUID

# Removed service imports to break cycle
# from sqlalchemy.ext.asyncio import AsyncSession
# from virtualstack.services.iam import role_service, user_service


class Permission(str, Enum):
    """Enumeration of system permissions."""

    # User permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Tenant permissions
    TENANT_READ = "tenant:read"
    TENANT_CREATE = "tenant:create"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"

    # API Key permissions
    API_KEY_READ = "api_key:read"
    API_KEY_CREATE = "api_key:create"
    API_KEY_UPDATE = "api_key:update"
    API_KEY_DELETE = "api_key:delete"

    # Compute permissions
    VM_READ = "vm:read"
    VM_CREATE = "vm:create"
    VM_UPDATE = "vm:update"
    VM_DELETE = "vm:delete"
    VM_START = "vm:start"
    VM_STOP = "vm:stop"
    VM_RESTART = "vm:restart"

    # Role permissions
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    # Permission to assign/remove roles TO users within a tenant
    ROLE_ASSIGN_USERS = "role:assign_users"
    # TODO: Revisit ROLE_ASSIGN - is it for assigning roles to users, or assigning permissions to roles?
    ROLE_ASSIGN = "role:assign" # Keep for now, potentially remove/rename later

    # Permission permissions (meta!)
    PERMISSION_READ = "permission:read"
    # Permission to assign/remove permissions FROM roles
    PERMISSION_ASSIGN = "permission:assign"

    # Tenant Role Management
    TENANT_MANAGE_ROLES = "tenant:manage_roles"
    TENANT_VIEW_ROLES = "tenant:view_roles"
    TENANT_MANAGE_ROLE_PERMISSIONS = "tenant:manage_role_permissions"

    # Tenant User Management
    TENANT_VIEW_USERS = "tenant:view_users"

    # Invitation Management (Example)
    TENANT_MANAGE_INVITATIONS = "tenant:manage_invitations"


# Built-in roles with their permissions
# This dictionary definition itself doesn't require service imports
ROLE_PERMISSIONS = {
    "admin": set(Permission),  # Admin has all permissions
    "tenant_admin": {
        # User permissions within tenant
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        # Tenant permissions (can read and update own tenant)
        Permission.TENANT_READ,
        Permission.TENANT_UPDATE,
        # API Key permissions
        Permission.API_KEY_READ,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_UPDATE,
        Permission.API_KEY_DELETE,
        # Compute permissions
        Permission.VM_READ,
        Permission.VM_CREATE,
        Permission.VM_UPDATE,
        Permission.VM_DELETE,
        Permission.VM_START,
        Permission.VM_STOP,
        Permission.VM_RESTART,
        # Role permissions within tenant
        Permission.ROLE_READ,
        Permission.ROLE_CREATE,
        Permission.ROLE_UPDATE,
        Permission.ROLE_DELETE,
        Permission.ROLE_ASSIGN,
        # Permission permissions
        Permission.PERMISSION_READ,
        Permission.PERMISSION_ASSIGN,
    },
    "user": {
        # User permissions (self only)
        Permission.USER_READ,
        Permission.USER_UPDATE,
        # Tenant permissions (read only)
        Permission.TENANT_READ,
        # API Key permissions (own keys only)
        Permission.API_KEY_READ,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_UPDATE,
        Permission.API_KEY_DELETE,
        # Compute permissions
        Permission.VM_READ,
        Permission.VM_CREATE,
        Permission.VM_UPDATE,
        Permission.VM_DELETE,
        Permission.VM_START,
        Permission.VM_STOP,
        Permission.VM_RESTART,
    },
    "viewer": {
        # User permissions (self only)
        Permission.USER_READ,
        # Tenant permissions (read only)
        Permission.TENANT_READ,
        # API Key permissions (own keys only)
        Permission.API_KEY_READ,
        # Compute permissions (read only)
        Permission.VM_READ,
    },
}


# --- Helper functions removed/commented out to break import cycle --- 
# --- These need to be moved to appropriate service files or a utils module --- 

# async def get_user_permissions(
#     db: AsyncSession, user_id: UUID, tenant_id: Optional[UUID] = None
# ) -> set[Permission]:
#     """Get permissions for a user, optionally scoped to a specific tenant."""
#     # Requires user_service, role_service
#     # ... implementation ...
#     pass
#
# def has_permission(user_permissions: set[Permission], required_permission: Permission) -> bool:
#     """Check if user has a specific permission."""
#     return required_permission in user_permissions
#
# def has_any_permission(
#     user_permissions: set[Permission], required_permissions: list[Permission]
# ) -> bool:
#     """Check if user has any of the specified permissions."""
#     return any(perm in user_permissions for perm in required_permissions)
#
# def has_all_permissions(
#     user_permissions: set[Permission], required_permissions: list[Permission]
# ) -> bool:
#     """Check if user has all of the specified permissions."""
#     return all(perm in user_permissions for perm in required_permissions)
