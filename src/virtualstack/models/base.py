import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_mixin

@declarative_mixin
class TimestampMixin:
    """Mixin to add created_at and updated_at columns to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )


@declarative_mixin
class UUIDMixin:
    """Mixin to add UUID primary key to models."""
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        index=True, 
        default=uuid.uuid4
    )


@declarative_mixin
class SoftDeleteMixin:
    """Mixin to add soft delete functionality to models."""
    deleted_at = Column(DateTime, nullable=True)
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert model to dictionary."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
