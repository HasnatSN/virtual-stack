from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from virtualstack.db.base_class import Base


class User(Base):
    """User model representing a user in the system."""

    __tablename__ = "users"
    __table_args__ = {"schema": "iam"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sent_invitations = relationship(
        "Invitation", back_populates="inviter", foreign_keys="Invitation.inviter_id"
    )
    received_invitations = relationship(
        "Invitation", back_populates="user", foreign_keys="Invitation.user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.id})>"
