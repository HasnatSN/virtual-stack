import uuid
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema for all Pydantic models."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class IDSchema(BaseSchema):
    """Schema with UUID id field."""
    id: uuid.UUID = Field(..., description="Unique identifier")


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# For backward compatibility with old schemas
TimestampMixin = TimestampSchema


class SoftDeleteSchema(BaseSchema):
    """Schema with soft delete field."""
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")


# Define a generic type variable for use in page responses
T = TypeVar("T")


class PageResponse(BaseSchema, Generic[T]):
    """Paginated response schema."""
    items: list[T]
    total: int
    page: int
    page_size: int
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size
