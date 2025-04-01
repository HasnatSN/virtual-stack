from typing import Optional

from pydantic import UUID4, BaseModel, Field

from virtualstack.schemas.base import TimestampMixin


class RoleBase(BaseModel):
    """Base schema for role data."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_system_role: bool = Field(False, description="Whether this is a system predefined role")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""

    tenant_id: UUID4 = Field(..., description="Tenant ID this role belongs to")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: Optional[str] = Field(None, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: Optional[bool] = Field(None, description="Whether the role is active")


class RoleInDBBase(RoleBase, TimestampMixin):
    """Base schema for roles in the database."""

    id: UUID4
    tenant_id: UUID4
    is_active: bool = True

    class Config:
        from_attributes = True


class Role(RoleInDBBase):
    """Schema for role API responses."""


class RoleWithPermissions(Role):
    """Schema for role with its permissions."""

    permissions: list[str] = Field([], description="List of permission names")


class RolePermissionCreate(BaseModel):
    """Schema for adding a permission to a role."""

    permission_id: UUID4 = Field(..., description="Permission ID to add to the role")


class RoleAssignment(BaseModel):
    """Schema for assigning a role to a user."""

    user_id: UUID4 = Field(..., description="User ID to assign the role to")
    role_id: UUID4 = Field(..., description="Role ID to assign")
    tenant_id: UUID4 = Field(..., description="Tenant ID for the role assignment")
