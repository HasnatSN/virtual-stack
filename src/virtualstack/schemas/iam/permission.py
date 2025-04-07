from virtualstack.schemas.base import BaseSchema
from typing import Optional
from uuid import UUID
from pydantic import ConfigDict


class PermissionBase(BaseSchema):
    name: str
    code: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(PermissionBase):
    name: Optional[str] = None # Allow partial updates
    code: Optional[str] = None # Allow partial updates
    description: Optional[str] = None # Allow partial updates


class Permission(PermissionBase):
    id: UUID

    # Pydantic V2 ORM mode
    model_config = ConfigDict(from_attributes=True)

# New schema for assigning a permission to a role
class PermissionAssign(BaseSchema):
    permission_id: UUID 