from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login requests."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Schema for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type")


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: Optional[str] = Field(None, description="Subject (user ID)")
    exp: Optional[int] = Field(None, description="Expiration timestamp")
