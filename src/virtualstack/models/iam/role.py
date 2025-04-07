from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from virtualstack.db.base_class import Base


class Role(Base):
    """Role model representing a set of permissions in the system."""

    __tablename__ = "roles"
    __table_args__ = {"schema": "iam"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Add tenant_id field - can be NULL for global roles
    tenant_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("iam.tenants.id", ondelete="CASCADE"), 
        nullable=True,
        index=True
    )
    
    # Track if this role is a system-defined role
    is_system_role = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Define relationships
    tenant = relationship("Tenant", back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.name} ({self.id})>"
