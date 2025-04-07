import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from virtualstack.db.base_class import Base


# Define the association table explicitly for Many-to-Many relationships
# This table links Users, Roles, and Tenants
user_tenant_roles_table = Table(
    "user_tenant_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("iam.users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("iam.roles.id", ondelete="CASCADE"), primary_key=True),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("iam.tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    # Add a unique constraint to ensure a user doesn't have the same role twice in the same tenant
    UniqueConstraint("user_id", "role_id", "tenant_id", name="uq_user_role_tenant"),
    # Explicitly define the schema for the association table itself
    schema="iam"
)

# Define an ORM class mapped to the association table
# This allows querying the association directly using ORM features
class UserTenantRole(Base):
    __table__ = user_tenant_roles_table
    # Define relationships if needed for direct access from this model
    # user = relationship("User", back_populates="tenant_roles") # Example
    # role = relationship("Role", back_populates="user_assignments") # Example
    # tenant = relationship("Tenant", back_populates="user_assignments") # Example
    # TODO: Define these relationships appropriately in User, Role, Tenant models as well

# TODO: Update User, Role, and Tenant models to include relationships using this table/class.

# TODO: While the table above defines the M2M link, we might later need a dedicated
# UserTenantRole class if we want to add extra attributes to the *relationship* itself
# (e.g., assigned_by_user_id, assignment_date separate from created_at).
# For now, the table is sufficient for linking existing User, Role, and Tenant models.

# TODO: Update User, Role, and Tenant models to include relationships using this table, e.g.:
# In User model:
# roles = relationship("Role", secondary=user_tenant_roles_table, back_populates="users")
# (Need to decide precise relationship structure based on query needs) 