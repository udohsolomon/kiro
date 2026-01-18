"""Session routes for managing maze game sessions."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, CurrentUser
from app.models.maze import Maze
from app.models.session import Session
from app.schemas.session import (
    SessionCreateRequest,
    SessionResponse,
    SessionPosition,
    SessionState,
    MoveRequest,
    MoveResponse,
    LookResponse,
)
from app.core.maze_engine import MazeEngine, Direction

router = APIRouter(prefix="/session", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: SessionCreateRequest,
    db: DbSession,
    user: CurrentUser,
) -> SessionResponse:
    """Create a new maze session.

    Starts a new session for the authenticated user on the specified maze.
    The user's position starts at the maze's start position (S).
    """
    # Get the maze
    query = select(Maze).where(Maze.id == request.maze_id)
    result = await db.execute(query)
    maze = result.scalar_one_or_none()

    if not maze:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maze not found: {request.maze_id}",
        )

    if not maze.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maze is not active",
        )

    # Create session starting at maze's start position
    session = Session(
        user_id=user.id,
        maze_id=maze.id,
        current_x=maze.start_x,
        current_y=maze.start_y,
        turn_count=0,
        is_stuck=False,
        status="active",
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        maze_id=session.maze_id,
        current_position=SessionPosition(x=session.current_x, y=session.current_y),
        turn_count=session.turn_count,
        is_stuck=session.is_stuck,
        status=session.status,
        created_at=session.created_at,
    )


@router.get(
    "/{session_id}",
    response_model=SessionState,
)
async def get_session(
    session_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> SessionState:
    """Get session state by ID.

    Returns the current state of the session including position and turn count.
    Only the owner of the session can access it.
    """
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Verify ownership
    if session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return SessionState(
        id=session.id,
        maze_id=session.maze_id,
        current_position=SessionPosition(x=session.current_x, y=session.current_y),
        turn_count=session.turn_count,
        is_stuck=session.is_stuck,
        status=session.status,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.post(
    "/{session_id}/move",
    response_model=MoveResponse,
)
async def move(
    session_id: uuid.UUID,
    request: MoveRequest,
    db: DbSession,
    user: CurrentUser,
) -> MoveResponse:
    """Move in a direction. COSTS 1 TURN.

    Attempts to move the player in the specified direction.
    Returns the result of the move including new position.
    """
    # Get session
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Verify ownership
    if session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Check if session is still active
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not active (status: {session.status})",
        )

    # Get maze
    query = select(Maze).where(Maze.id == session.maze_id)
    result = await db.execute(query)
    maze = result.scalar_one_or_none()

    if not maze:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Maze not found for session",
        )

    # Create maze engine and load session state
    engine = MazeEngine(maze.grid_data)
    engine_session = engine.create_session(str(session.id))

    # Sync engine state with database state
    engine_session.position.x = session.current_x
    engine_session.position.y = session.current_y
    engine_session.turn_count = session.turn_count
    engine_session.is_stuck = session.is_stuck

    # Execute move
    direction = Direction(request.direction)
    move_result = engine.move(str(session.id), direction)

    # Update session in database
    session.current_x = move_result.position.x
    session.current_y = move_result.position.y
    session.turn_count = move_result.turns
    session.is_stuck = engine_session.is_stuck

    if move_result.status == "completed":
        session.status = "completed"
        from datetime import datetime, timezone

        session.completed_at = datetime.now(timezone.utc)

    await db.commit()

    return MoveResponse(
        status=move_result.status,
        position=SessionPosition(x=move_result.position.x, y=move_result.position.y),
        turns=move_result.turns,
        message=move_result.message,
    )


@router.post(
    "/{session_id}/look",
    response_model=LookResponse,
)
async def look(
    session_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> LookResponse:
    """Look at surrounding cells. FREE - does not cost a turn.

    Returns the cell types in all four directions and the current cell.
    """
    # Get session
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Verify ownership
    if session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Check if session is still active
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not active (status: {session.status})",
        )

    # Get maze
    query = select(Maze).where(Maze.id == session.maze_id)
    result = await db.execute(query)
    maze = result.scalar_one_or_none()

    if not maze:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Maze not found for session",
        )

    # Create maze engine and get surroundings
    engine = MazeEngine(maze.grid_data)
    engine_session = engine.create_session(str(session.id))

    # Sync engine state
    engine_session.position.x = session.current_x
    engine_session.position.y = session.current_y

    look_result = engine.look(str(session.id))

    return LookResponse(
        north=look_result.north,
        south=look_result.south,
        east=look_result.east,
        west=look_result.west,
        current=look_result.current,
    )
