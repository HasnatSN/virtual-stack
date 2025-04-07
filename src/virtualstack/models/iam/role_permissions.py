import uuid

from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID

from virtualstack.db.base_class import Base

# This table defines the association between global Roles and Permissions.
# It dictates which permissions are granted by assigning a specific role.

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", pgUUID(as_uuid=True), ForeignKey("iam.roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", pgUUID(as_uuid=True), ForeignKey("iam.permissions.id", ondelete="CASCADE"), primary_key=True),
    # Ensure a permission is only associated once per role
    UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    schema="iam" # Ensure table is created in the 'iam' schema
) 