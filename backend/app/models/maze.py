"""Maze model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Maze(Base):
    """Maze model for storing maze definitions."""

    __tablename__ = "mazes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # tutorial, intermediate, challenge
    grid_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_y: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    exit_x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    exit_y: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Maze {self.name}>"
