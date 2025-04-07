from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict # Import BaseModel directly

from virtualstack.schemas.base import BaseSchema, IDSchema, TimestampSchema
# Moved import here
from virtualstack.schemas.iam.permission import Permission as PermissionSchema


# --- Base Definitions ---
class RoleBase(BaseSchema):
    """Base properties shared by Role schemas."""
    name: str
    description: Optional[str] = None
    # tenant_id: Optional[UUID] = None  # Removed, roles are global/tenant-scoped implicitly via context
    # is_system_role: bool = False      # Removed, handled by service logic potentially


# --- Schemas for API Input ---
class RoleCreate(RoleBase):
    """Schema used for creating a new custom Role via the API."""
    permission_ids: Optional[List[UUID]] = [] # Allow assigning permissions on create


class RoleUpdate(BaseModel): # Use BaseModel for optional fields
    """Schema used for updating an existing custom Role via the API (partial updates)."""
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[UUID]] = None # Allow updating permissions


# Re-added RoleAssign schema for role assignment endpoint
class RoleAssign(BaseModel):
    """Input schema for assigning a role to a user."""
    role_id: UUID


# Removed RoleAssign schema as role assignment is handled by RoleUserAssignment schemas


# --- Schemas reflecting Database Structure (Internal) ---
# Removed RoleInDBBase as it's not directly used for API output in this structure


# --- Schemas for API Output ---
class Role(IDSchema, TimestampSchema, RoleBase): # Combine directly
    """Schema for returning Role data via the API."""
    # This inherits id, created_at, updated_at, name, description
    is_system_role: bool # Add back for output
    # permission_ids: List[UUID] # Return IDs instead of strings
    # TODO: Decide if we need full PermissionSchema objects here instead of just IDs
    # detailed_permissions: List[PermissionSchema] = []
    model_config = ConfigDict(from_attributes=True)


class RoleList(BaseModel): # Specific schema for list output
    """Schema for the list roles endpoint output."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_system_role: bool
    user_count: int # Add user count as per MVP spec

    model_config = ConfigDict(from_attributes=True)


class RoleDetail(Role): # Inherit Role and add detailed permissions
    """Schema for the get role details endpoint output."""
    # Removed import from here
    # from virtualstack.schemas.iam.permission import Permission as PermissionSchema
    permissions: List[PermissionSchema] = []


class RoleUserAssignmentInput(BaseModel):
    """Input schema for assigning/updating users for a role."""
    user_ids: List[UUID]

class RoleUserAssignmentOutput(BaseModel):
    """Output schema confirming user assignments for a role."""
    user_ids: List[UUID]

# Potentially other output schemas like RoleWithPermissions if needed later
# class RoleWithPermissions(Role):
#    detailed_permissions: List[PermissionSchema] = []

# --- Removed conflicting/duplicate definitions --- 
# Removed the Role definition that was placed too early.
# Removed RolePermissionCreate, RoleAssignment schemas that were not currently used and maybe outdated.
