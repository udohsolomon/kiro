"""Submission schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubmissionCreateRequest(BaseModel):
    """Schema for creating a new submission."""

    maze_id: uuid.UUID
    code: str = Field(..., min_length=1, max_length=100000)


class SubmissionResponse(BaseModel):
    """Schema for submission response."""

    id: uuid.UUID
    user_id: uuid.UUID
    maze_id: uuid.UUID
    status: str
    score: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubmissionStatus(BaseModel):
    """Schema for submission status check."""

    id: uuid.UUID
    status: str
    score: Optional[int] = None
    error_message: Optional[str] = None
    turns: Optional[int] = None
    completed: bool = False
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """Schema for listing submissions."""

    submissions: list[SubmissionResponse]
    total: int
