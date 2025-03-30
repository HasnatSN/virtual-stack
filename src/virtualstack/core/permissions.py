from typing import List, Optional, Dict, Union, Set
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.services.iam import user_service


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
    ROLE_ASSIGN = "role:assign"
    
    # Permission permissions (meta!)
    PERMISSION_READ = "permission:read"
    PERMISSION_ASSIGN = "permission:assign"


# Built-in roles with their permissions
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


async def get_user_permissions(
    db: AsyncSession, user_id: UUID, tenant_id: Optional[UUID] = None
) -> Set[Permission]:
    """
    Get permissions for a user, optionally scoped to a specific tenant.
    
    Args:
        db: Database session
        user_id: User ID
        tenant_id: Optional tenant ID to scope permissions
        
    Returns:
        Set of permissions
    """
    # This is a simplified implementation
    # In a production system, we would:
    # 1. Look up user's roles in the specified tenant (or global roles if no tenant)
    # 2. Fetch all permissions for those roles
    # 3. Return the union of all permissions
    
    # For now, return mock permissions based on hard-coded roles
    # Assuming superuser has admin role, others have user role
    user = await user_service.get(db, id=user_id)
    
    if not user:
        return set()
    
    if user.is_superuser:
        return set(Permission)  # All permissions
    
    # For now, return user role permissions
    return ROLE_PERMISSIONS["user"]


def has_permission(
    user_permissions: Set[Permission], required_permission: Permission
) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user_permissions: Set of user's permissions
        required_permission: Permission to check
        
    Returns:
        True if user has the permission, False otherwise
    """
    return required_permission in user_permissions


def has_any_permission(
    user_permissions: Set[Permission], required_permissions: List[Permission]
) -> bool:
    """
    Check if user has any of the specified permissions.
    
    Args:
        user_permissions: Set of user's permissions
        required_permissions: List of permissions to check
        
    Returns:
        True if user has any of the permissions, False otherwise
    """
    return any(perm in user_permissions for perm in required_permissions)


def has_all_permissions(
    user_permissions: Set[Permission], required_permissions: List[Permission]
) -> bool:
    """
    Check if user has all of the specified permissions.
    
    Args:
        user_permissions: Set of user's permissions
        required_permissions: List of permissions to check
        
    Returns:
        True if user has all of the permissions, False otherwise
    """
    return all(perm in user_permissions for perm in required_permissions) 