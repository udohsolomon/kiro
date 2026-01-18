"""User schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric with underscores only")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserRegisterResponse(BaseModel):
    """Schema for user registration response."""

    user_id: uuid.UUID
    username: str
    message: str = "Verification email sent"
    api_key: Optional[str] = None  # Returned in debug mode when auto-verified


class UserVerifyRequest(BaseModel):
    """Schema for email verification request."""

    token: str


class UserVerifyResponse(BaseModel):
    """Schema for email verification response."""

    api_key: str
    starter_package_url: str = "/downloads/starter-package.zip"
    message: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    """Schema for Google login request."""
    token: str
    regenerate_key: bool = False  # If True, regenerates API key for existing users


class UserResponse(BaseModel):
    """Schema for user response (public info)."""

    id: uuid.UUID
    username: str
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithApiKey(BaseModel):
    """Schema for user with API key (after verification)."""

    id: uuid.UUID
    username: str
    email: str
    api_key_prefix: str
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Schema for user profile response (GET /auth/me)."""

    id: uuid.UUID
    username: str
    email: str
    api_key_prefix: str  # First 20 chars (kiro_xxx...) for display
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
