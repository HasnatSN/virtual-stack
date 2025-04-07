import uuid

from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as pgUUID

from virtualstack.db.base_class import Base

# This table defines a direct association between a Tenant and a global Role.
# It could be used to determine which global roles are *available* or *active*
# within a specific tenant, distinct from which users have which roles in that tenant
# (which is handled by user_tenant_roles_table).
# If roles could be configured differently per tenant, this would likely be a
# full model class instead of just an association table.

tenant_roles_table = Table(
    "tenant_roles",
    Base.metadata,
    Column("tenant_id", pgUUID(as_uuid=True), ForeignKey("iam.tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", pgUUID(as_uuid=True), ForeignKey("iam.roles.id", ondelete="CASCADE"), primary_key=True),
    # Ensure a role is only associated once per tenant
    UniqueConstraint("tenant_id", "role_id", name="uq_tenant_role"),
    schema="iam" # Ensure table is created in the 'iam' schema
) 