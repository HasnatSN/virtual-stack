import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from virtualstack.db.base_class import Base


class InvitationStatus(str, enum.Enum):
    """Invitation status enum."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invitation(Base):
    """
    User invitation model for inviting users to join a tenant.
    """
    __tablename__ = "invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    
    # Foreign key to tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Foreign key to inviter (the user who created the invitation)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Foreign key to user (set when the invitation is accepted)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Role to assign to the user upon acceptance
    role_id = Column(UUID(as_uuid=True), ForeignKey("tenant_roles.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="sent_invitations")
    user = relationship("User", foreign_keys=[user_id], back_populates="received_invitations")
    role = relationship("TenantRole")
    
    @property
    def is_expired(self) -> bool:
        """Check if the invitation is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self) -> bool:
        """Check if the invitation is pending."""
        return self.status == InvitationStatus.PENDING and not self.is_expired
    
    def __repr__(self) -> str:
        return f"<Invitation {self.email} to {self.tenant.name} ({self.status})>" 