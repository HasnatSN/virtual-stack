from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from virtualstack.db.base_class import Base
from virtualstack.schemas.iam.api_key import APIKeyScope


class APIKey(Base):
    """API Key model for authenticating client applications or services."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(8), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL means no expiration
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign key to user who created the API key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Foreign key to tenant if key is tenant-scoped (NULL for global keys)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    # Timestamps
    # Use client-side default and ensure timezone awareness
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="api_keys")
    tenant = relationship("Tenant", back_populates="api_keys")

    # Add the scope column
    scope = Column(
        Enum(APIKeyScope, name="api_key_scope", create_type=False),
        nullable=False,
        default=APIKeyScope.TENANT,
        server_default=APIKeyScope.TENANT.value,
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.name} ({self.key_prefix}...)>"
