from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models."""

    # Generate __tablename__ automatically based on class name
    @declared_attr
    def __tablename__(self) -> str:
        return self.__name__.lower()

# Import all models here to ensure they are registered with the Base.metadata
# This is crucial for create_all or iterating metadata to work correctly.
from virtualstack.models.iam import api_key, invitation, permission, role, tenant, user, user_tenant_role, role_permissions
# TODO: If other model directories exist (e.g., compute, billing), import them here too.
