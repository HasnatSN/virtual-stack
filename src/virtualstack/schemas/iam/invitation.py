from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, UUID4, EmailStr, Field, validator

from virtualstack.models.iam.invitation import InvitationStatus
from virtualstack.schemas.base import TimestampMixin


class InvitationBase(BaseModel):
    """Base schema for invitation data."""
    email: EmailStr = Field(..., description="Email address of the invitee")
    expires_in_days: Optional[int] = Field(7, description="Number of days until the invitation expires")


class InvitationCreate(InvitationBase):
    """Schema for creating a new invitation."""
    tenant_id: UUID4 = Field(..., description="ID of the tenant to invite to")
    role_id: Optional[UUID4] = Field(None, description="Role ID to assign on acceptance")


class InvitationUpdate(BaseModel):
    """Schema for updating an invitation."""
    status: Optional[InvitationStatus] = Field(None, description="New status for the invitation")


class InvitationVerify(BaseModel):
    """Schema for verifying an invitation token."""
    token: str = Field(..., description="Invitation token to verify")


class InvitationAccept(BaseModel):
    """Schema for accepting an invitation."""
    token: str = Field(..., description="Invitation token to accept")
    password: str = Field(..., description="Password for the new user")
    first_name: Optional[str] = Field(None, description="First name of the new user")
    last_name: Optional[str] = Field(None, description="Last name of the new user")
    
    @validator('password')
    def password_strength(cls, v):
        """Validate that the password is strong enough."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class InvitationInDBBase(TimestampMixin):
    """Base schema for invitations in the database."""
    id: UUID4
    email: EmailStr
    status: InvitationStatus
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    tenant_id: UUID4
    inviter_id: Optional[UUID4] = None
    user_id: Optional[UUID4] = None
    role_id: Optional[UUID4] = None

    class Config:
        from_attributes = True


class Invitation(InvitationInDBBase):
    """Schema for invitation API responses."""
    tenant_name: Optional[str] = None
    inviter_email: Optional[str] = None
    is_expired: bool = False
    is_pending: bool = True


class InvitationWithToken(Invitation):
    """Schema that includes the invitation token (only for creation responses)."""
    token: str = Field(..., description="Invitation token (only available on creation)")
    invitation_link: str = Field(..., description="Full invitation link to send to the invitee") 