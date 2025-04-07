from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import UUID4, BaseModel, EmailStr, Field, validator, field_validator, ConfigDict

from virtualstack.models.iam.invitation import InvitationStatus
from virtualstack.schemas.base import TimestampMixin


# Enum for invitation status
class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InvitationBase(BaseModel):
    """Base schema for invitation data."""

    email: EmailStr = Field(..., description="Email address of the invitee")
    tenant_id: UUID4 = Field(..., description="Tenant ID the invitation is for")
    role_id: Optional[UUID4] = Field(None, description="Role ID to assign upon acceptance")
    expires_in_days: Optional[int] = Field(
        7, description="Number of days until the invitation expires"
    )


class InvitationCreate(InvitationBase):
    """Schema for creating a new invitation."""

    tenant_id: UUID4 = Field(..., description="ID of the tenant to invite to")


class InvitationUpdate(BaseModel):
    """Schema for updating an invitation."""

    role_id: Optional[UUID] = Field(None, description="Role to assign to the user on acceptance")
    expires_in_days: Optional[int] = Field(
        None, description="Number of days until the invitation expires"
    )


class InvitationVerify(BaseModel):
    """Schema for verifying an invitation token."""

    token: str = Field(..., description="Invitation token to verify")


class InvitationAccept(BaseModel):
    """Schema for accepting an invitation."""

    token: str = Field(..., description="Invitation token to accept")
    password: str = Field(..., description="Password for the new user")
    first_name: Optional[str] = Field(None, description="First name of the new user")
    last_name: Optional[str] = Field(None, description="Last name of the new user")

    @field_validator("password")
    def password_strength(v):
        """Validate that the password is strong enough."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class InvitationInDBBase(TimestampMixin):
    """Base schema for invitations in the database."""

    id: UUID
    email: EmailStr
    status: InvitationStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    tenant_id: UUID
    inviter_id: UUID
    user_id: Optional[UUID] = None
    accepted_at: Optional[datetime] = None
    role_id: Optional[UUID] = None

    # Use ConfigDict for Pydantic V2 compatibility
    model_config = ConfigDict(from_attributes=True)


class InvitationResponse(InvitationInDBBase):
    """Schema for invitation API responses."""


class InvitationCreateResponse(InvitationResponse):
    """Schema for the response after creating an invitation, including the token."""
    token: str = Field(..., description="The generated invitation token (only shown on creation)")


class InvitationDetailResponse(InvitationResponse):
    """Schema for detailed invitation API responses."""

    tenant_name: Optional[str] = None
    inviter_email: Optional[str] = None
    is_expired: bool = False
    is_pending: bool = True


class InvitationTokenResponse(BaseModel):
    """Schema for invitation token verification response."""

    valid: bool = Field(..., description="Whether the token is valid")
    email: Optional[str] = Field(None, description="Email associated with the invitation")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID associated with the invitation")
    tenant_name: Optional[str] = Field(
        None, description="Tenant name associated with the invitation"
    )
    inviter_email: Optional[str] = Field(None, description="Email of the inviter")
    expires_at: Optional[datetime] = Field(None, description="When the invitation expires")
    role_id: Optional[UUID] = Field(None, description="Role ID to assign on acceptance")
    token: Optional[str] = Field(None, description="The original token (for convenience)")


class InvitationSendResponse(BaseModel):
    """Schema for response when sending an invitation."""

    id: UUID = Field(..., description="Invitation ID")
    email: EmailStr = Field(..., description="Email address of the invitee")
    invitation_link: str = Field(..., description="URL for accepting the invitation")
    expires_at: datetime = Field(..., description="When the invitation expires")
