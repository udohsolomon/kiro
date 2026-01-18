"""Submission service for processing code submissions."""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.submission import Submission
from app.models.maze import Maze
from app.services.sandbox_service import get_sandbox_service, SandboxResult


class SubmissionQueue:
    """In-memory queue for submission processing."""

    def __init__(self):
        self._queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        self._processing: set[uuid.UUID] = set()

    async def enqueue(self, submission_id: uuid.UUID) -> None:
        """Add submission to queue."""
        await self._queue.put(submission_id)

    async def dequeue(self) -> uuid.UUID:
        """Get next submission from queue."""
        submission_id = await self._queue.get()
        self._processing.add(submission_id)
        return submission_id

    def complete(self, submission_id: uuid.UUID) -> None:
        """Mark submission as done processing."""
        self._processing.discard(submission_id)
        self._queue.task_done()

    @property
    def pending_count(self) -> int:
        """Number of pending submissions."""
        return self._queue.qsize()

    @property
    def processing_count(self) -> int:
        """Number of submissions being processed."""
        return len(self._processing)


# Global queue instance
_submission_queue: Optional[SubmissionQueue] = None


def get_submission_queue() -> SubmissionQueue:
    """Get singleton submission queue."""
    global _submission_queue
    if _submission_queue is None:
        _submission_queue = SubmissionQueue()
    return _submission_queue


class SubmissionService:
    """Service for managing code submissions."""

    def __init__(self):
        self.settings = get_settings()
        self.sandbox = get_sandbox_service()
        self.queue = get_submission_queue()
        self.code_storage_path = Path("/tmp/submissions")
        self.code_storage_path.mkdir(parents=True, exist_ok=True)

    async def create_submission(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        maze_id: uuid.UUID,
        code: str,
    ) -> Submission:
        """
        Create a new submission and queue it for processing.

        Args:
            db: Database session
            user_id: User ID
            maze_id: Maze ID
            code: Python code to execute

        Returns:
            Created submission
        """
        # Save code to file
        submission_id = uuid.uuid4()
        code_path = self.code_storage_path / f"{submission_id}.py"
        code_path.write_text(code)

        # Create submission record
        submission = Submission(
            id=submission_id,
            user_id=user_id,
            maze_id=maze_id,
            code_path=str(code_path),
            status="pending",
        )

        db.add(submission)
        await db.commit()
        await db.refresh(submission)

        # Add to processing queue
        await self.queue.enqueue(submission_id)

        return submission

    async def get_submission(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
    ) -> Optional[Submission]:
        """Get submission by ID."""
        query = select(Submission).where(Submission.id == submission_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def process_submission(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        api_base_url: str,
    ) -> Submission:
        """
        Process a submission by executing code in sandbox.

        Args:
            db: Database session
            submission_id: Submission ID to process
            api_base_url: Base URL of the API for maze interactions

        Returns:
            Updated submission
        """
        # Get submission
        submission = await self.get_submission(db, submission_id)
        if not submission:
            raise ValueError(f"Submission not found: {submission_id}")

        # Update status to running
        submission.status = "running"
        submission.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # Get maze info
            query = select(Maze).where(Maze.id == submission.maze_id)
            result = await db.execute(query)
            maze = result.scalar_one_or_none()

            if not maze:
                submission.status = "failed"
                submission.error_message = "Maze not found"
                submission.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return submission

            # Read user code
            code_path = Path(submission.code_path)
            if not code_path.exists():
                submission.status = "failed"
                submission.error_message = "Code file not found"
                submission.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return submission

            user_code = code_path.read_text()

            # Create a session for sandbox execution
            from app.models.session import Session

            session = Session(
                user_id=submission.user_id,
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

            # Ensure sandbox network exists
            await self.sandbox.ensure_network_exists()

            # Execute in sandbox
            sandbox_result = await self.sandbox.execute_code(
                code=user_code,
                session_id=str(session.id),
                api_url=api_base_url,
            )

            # Update submission based on result
            if sandbox_result.timed_out:
                submission.status = "timeout"
                submission.error_message = "Execution timed out"
            elif sandbox_result.success and sandbox_result.completed:
                submission.status = "completed"
                submission.score = sandbox_result.turns
            elif sandbox_result.success:
                submission.status = "failed"
                submission.error_message = "Maze not completed"
            else:
                submission.status = "failed"
                submission.error_message = sandbox_result.error or "Execution failed"

            submission.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(submission)

            return submission

        except Exception as e:
            submission.status = "failed"
            submission.error_message = str(e)
            submission.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return submission

    async def get_user_submissions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        maze_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> list[Submission]:
        """Get submissions for a user."""
        query = select(Submission).where(Submission.user_id == user_id)

        if maze_id:
            query = query.where(Submission.maze_id == maze_id)

        query = query.order_by(Submission.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton instance
_submission_service: Optional[SubmissionService] = None


def get_submission_service() -> SubmissionService:
    """Get singleton submission service."""
    global _submission_service
    if _submission_service is None:
        _submission_service = SubmissionService()
    return _submission_service


async def submission_worker(db_session_factory, api_base_url: str) -> None:
    """
    Background worker that processes submissions from the queue.

    Args:
        db_session_factory: Async session factory
        api_base_url: Base URL for API calls
    """
    service = get_submission_service()
    queue = get_submission_queue()

    while True:
        try:
            # Get next submission
            submission_id = await queue.dequeue()

            # Process it
            async with db_session_factory() as db:
                await service.process_submission(db, submission_id, api_base_url)

            queue.complete(submission_id)

        except asyncio.CancelledError:
            break
        except Exception as e:
            # Log error but continue processing
            print(f"Error processing submission: {e}")
            queue.complete(submission_id)
