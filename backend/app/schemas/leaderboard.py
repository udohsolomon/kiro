"""Leaderboard schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LeaderboardEntryResponse(BaseModel):
    """Schema for a leaderboard entry."""

    user_id: str
    username: str
    maze_id: str
    score: int
    rank: int
    submitted_at: datetime

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response."""

    entries: list[LeaderboardEntryResponse]
    total: int
    maze_id: Optional[str] = None


class LeaderboardUpdateMessage(BaseModel):
    """Schema for WebSocket leaderboard update message."""

    type: str = "leaderboard_update"
    data: LeaderboardEntryResponse
