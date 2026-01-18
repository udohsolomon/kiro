"""Leaderboard routes for viewing and WebSocket updates."""

import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from app.schemas.leaderboard import (
    LeaderboardEntryResponse,
    LeaderboardResponse,
)
from app.services.leaderboard_service import get_leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get(
    "",
    response_model=LeaderboardResponse,
)
async def get_leaderboard(
    maze_id: Optional[uuid.UUID] = Query(None, description="Filter by maze ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> LeaderboardResponse:
    """Get leaderboard entries.

    Returns leaderboard sorted by score (lower turn count is better).
    Can be filtered by maze ID for maze-specific leaderboards.
    """
    service = get_leaderboard_service()
    entries = await service.get_leaderboard(
        maze_id=maze_id,
        limit=limit,
        offset=offset,
    )

    entry_responses = [
        LeaderboardEntryResponse(
            user_id=e.user_id,
            username=e.username,
            maze_id=e.maze_id,
            score=e.score,
            rank=e.rank,
            submitted_at=e.submitted_at,
        )
        for e in entries
    ]

    return LeaderboardResponse(
        entries=entry_responses,
        total=len(entry_responses),
        maze_id=str(maze_id) if maze_id else None,
    )


@router.get(
    "/top",
    response_model=LeaderboardResponse,
)
async def get_top_scores(
    maze_id: Optional[uuid.UUID] = Query(None, description="Filter by maze ID"),
    n: int = Query(10, ge=1, le=100, description="Number of top entries"),
) -> LeaderboardResponse:
    """Get top N scores from the leaderboard."""
    service = get_leaderboard_service()
    entries = await service.get_top_n(n=n, maze_id=maze_id)

    entry_responses = [
        LeaderboardEntryResponse(
            user_id=e.user_id,
            username=e.username,
            maze_id=e.maze_id,
            score=e.score,
            rank=e.rank,
            submitted_at=e.submitted_at,
        )
        for e in entries
    ]

    return LeaderboardResponse(
        entries=entry_responses,
        total=len(entry_responses),
        maze_id=str(maze_id) if maze_id else None,
    )


@router.websocket("/ws")
async def leaderboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time leaderboard updates.

    Clients receive updates whenever a new high score is submitted.
    Messages are JSON with format:
    {
        "type": "leaderboard_update",
        "data": {
            "user_id": "...",
            "username": "...",
            "maze_id": "...",
            "score": 100,
            "rank": 1,
            "submitted_at": "2024-01-01T00:00:00Z"
        }
    }
    """
    await websocket.accept()

    service = get_leaderboard_service()
    queue = service.subscribe()

    try:
        while True:
            # Wait for updates
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        service.unsubscribe(queue)
