"""Submit routes for code submissions."""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.api.deps import DbSession, CurrentUser
from app.config import get_settings
from app.models.maze import Maze
from app.models.submission import Submission
from app.schemas.submission import (
    SubmissionCreateRequest,
    SubmissionResponse,
    SubmissionStatus,
    SubmissionListResponse,
)
from app.services.submission_service import get_submission_service

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(tags=["Submissions"])


@router.post(
    "/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(f"{settings.rate_limit_submissions}/minute")
async def submit_code(
    request: Request,
    submission_data: SubmissionCreateRequest,
    db: DbSession,
    user: CurrentUser,
) -> SubmissionResponse:
    """Submit code for maze solving.

    The code will be queued for async execution in a sandboxed environment.
    Use GET /v1/submission/{id} to check the status.
    """
    # Verify maze exists and is active
    query = select(Maze).where(Maze.id == submission_data.maze_id)
    result = await db.execute(query)
    maze = result.scalar_one_or_none()

    if not maze:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maze not found: {submission_data.maze_id}",
        )

    if not maze.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maze is not active",
        )

    # Create submission
    service = get_submission_service()
    submission = await service.create_submission(
        db=db,
        user_id=user.id,
        maze_id=submission_data.maze_id,
        code=submission_data.code,
    )

    return SubmissionResponse(
        id=submission.id,
        user_id=submission.user_id,
        maze_id=submission.maze_id,
        status=submission.status,
        score=submission.score,
        error_message=submission.error_message,
        created_at=submission.created_at,
        started_at=submission.started_at,
        completed_at=submission.completed_at,
    )


@router.get(
    "/submission/{submission_id}",
    response_model=SubmissionStatus,
)
async def get_submission(
    submission_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> SubmissionStatus:
    """Get submission status by ID.

    Returns the current status, score (if completed), and any error messages.
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission not found: {submission_id}",
        )

    # Verify ownership
    if submission.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this submission",
        )

    return SubmissionStatus(
        id=submission.id,
        status=submission.status,
        score=submission.score,
        error_message=submission.error_message,
        turns=submission.score,  # Score is turn count
        completed=submission.status == "completed",
        created_at=submission.created_at,
        started_at=submission.started_at,
        completed_at=submission.completed_at,
    )


@router.get(
    "/submissions",
    response_model=SubmissionListResponse,
)
async def list_submissions(
    db: DbSession,
    user: CurrentUser,
    maze_id: Optional[uuid.UUID] = Query(None, description="Filter by maze ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
) -> SubmissionListResponse:
    """List user's submissions.

    Returns submissions sorted by creation date (newest first).
    """
    service = get_submission_service()
    submissions = await service.get_user_submissions(
        db=db,
        user_id=user.id,
        maze_id=maze_id,
        limit=limit,
    )

    submission_responses = [
        SubmissionResponse(
            id=s.id,
            user_id=s.user_id,
            maze_id=s.maze_id,
            status=s.status,
            score=s.score,
            error_message=s.error_message,
            created_at=s.created_at,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in submissions
    ]

    return SubmissionListResponse(
        submissions=submission_responses,
        total=len(submission_responses),
    )
