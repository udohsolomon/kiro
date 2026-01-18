"""Maze schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MazeBase(BaseModel):
    """Base maze schema with common fields."""

    name: str
    difficulty: str = Field(..., pattern="^(tutorial|intermediate|challenge)$")
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class MazeListItem(MazeBase):
    """Schema for maze list item (without grid data)."""

    id: uuid.UUID
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class MazeDetail(MazeBase):
    """Schema for detailed maze response with grid data."""

    id: uuid.UUID
    grid_data: str
    start_x: int
    start_y: int
    exit_x: int
    exit_y: int
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class MazeListResponse(BaseModel):
    """Schema for maze list response."""

    mazes: list[MazeListItem]
    total: int


class MazeCreateRequest(BaseModel):
    """Schema for creating a new maze."""

    name: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., pattern="^(tutorial|intermediate|challenge)$")
    grid_data: str = Field(..., min_length=5)


class MazePosition(BaseModel):
    """Schema for a position in the maze."""

    x: int
    y: int
