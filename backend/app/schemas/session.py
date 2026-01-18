"""Session schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    """Schema for creating a new session."""

    maze_id: uuid.UUID


class SessionPosition(BaseModel):
    """Schema for position in a session."""

    x: int
    y: int


class SessionResponse(BaseModel):
    """Schema for session response."""

    id: uuid.UUID
    user_id: uuid.UUID
    maze_id: uuid.UUID
    current_position: SessionPosition
    turn_count: int
    is_stuck: bool
    status: str  # active, completed, abandoned
    created_at: datetime

    class Config:
        from_attributes = True


class SessionState(BaseModel):
    """Schema for session state (used in get session)."""

    id: uuid.UUID
    maze_id: uuid.UUID
    current_position: SessionPosition
    turn_count: int
    is_stuck: bool
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MoveRequest(BaseModel):
    """Schema for move request."""

    direction: str = Field(..., pattern="^(north|south|east|west)$")


class MoveResponse(BaseModel):
    """Schema for move response."""

    status: str  # moved, blocked, mud, stuck, completed
    position: SessionPosition
    turns: int
    message: Optional[str] = None


class LookResponse(BaseModel):
    """Schema for look response."""

    north: str
    south: str
    east: str
    west: str
    current: str
