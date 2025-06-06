from datetime import datetime
import enum
from typing import Optional
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from virtualstack.db.base_class import Base


class InvitationStatus(str, enum.Enum):
    """Invitation status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invitation(Base):
    """User invitation model for inviting users to join a tenant."""

    __tablename__ = "invitations"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Foreign key to tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam.tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Foreign key to inviter (the user who created the invitation)
    inviter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)

    # Foreign key to user (set when the invitation is accepted)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=True)

    # Role to assign to the user upon acceptance
    # TODO: Implement TenantRole model and uncomment this foreign key and relationship
    # role_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_roles.id", ondelete="SET NULL"), nullable=True)
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    ) # Simplified column def, FK handled by relationship or Alembic?

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="invitations"
    )  # Use string for forward reference
    inviter: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[inviter_id], back_populates="sent_invitations"
    )  # Use string
    user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[user_id], back_populates="received_invitations"
    )  # Use string
    # role = relationship("TenantRole") # TODO: Uncomment when TenantRole is implemented

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
