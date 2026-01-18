"""Maze routes for listing and retrieving mazes."""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, case

from app.api.deps import DbSession
from app.models.maze import Maze
from app.schemas.maze import MazeListItem, MazeListResponse, MazeDetail

router = APIRouter(prefix="/maze", tags=["Mazes"])


@router.get(
    "",
    response_model=MazeListResponse,
)
async def list_mazes(
    db: DbSession,
    difficulty: Optional[str] = Query(
        None,
        description="Filter by difficulty (tutorial, intermediate, challenge)",
        pattern="^(tutorial|intermediate|challenge)$",
    ),
    active_only: bool = Query(True, description="Only return active mazes"),
) -> MazeListResponse:
    """List all available mazes.

    Returns a paginated list of mazes with basic metadata.
    Grid data is not included - use GET /v1/maze/{id} for full details.
    """
    # Build query
    query = select(Maze)

    if active_only:
        query = query.where(Maze.is_active == True)

    if difficulty:
        query = query.where(Maze.difficulty == difficulty)

    # Order by difficulty (tutorial first) then by name
    query = query.order_by(
        # Custom ordering: tutorial=1, intermediate=2, challenge=3
        case(
            (Maze.difficulty == "tutorial", 1),
            (Maze.difficulty == "intermediate", 2),
            (Maze.difficulty == "challenge", 3),
            else_=4,
        ),
        Maze.name,
    )

    # Execute query
    result = await db.execute(query)
    mazes = result.scalars().all()

    # Convert to response
    maze_items = [
        MazeListItem(
            id=maze.id,
            name=maze.name,
            difficulty=maze.difficulty,
            width=maze.width,
            height=maze.height,
            is_active=maze.is_active,
            created_at=maze.created_at,
        )
        for maze in mazes
    ]

    return MazeListResponse(
        mazes=maze_items,
        total=len(maze_items),
    )


@router.get(
    "/{maze_id}",
    response_model=MazeDetail,
)
async def get_maze(
    maze_id: uuid.UUID,
    db: DbSession,
) -> MazeDetail:
    """Get detailed information about a specific maze.

    Returns full maze details including grid data.
    """
    query = select(Maze).where(Maze.id == maze_id)
    result = await db.execute(query)
    maze = result.scalar_one_or_none()

    if not maze:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maze not found: {maze_id}",
        )

    return MazeDetail(
        id=maze.id,
        name=maze.name,
        difficulty=maze.difficulty,
        grid_data=maze.grid_data,
        width=maze.width,
        height=maze.height,
        start_x=maze.start_x,
        start_y=maze.start_y,
        exit_x=maze.exit_x,
        exit_y=maze.exit_y,
        is_active=maze.is_active,
        created_at=maze.created_at,
    )
