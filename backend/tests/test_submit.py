"""Tests for submission endpoints."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.models.user import User
from app.models.maze import Maze
from app.models.submission import Submission
from app.services import auth_service
from app.services.submission_service import (
    SubmissionService,
    SubmissionQueue,
    get_submission_queue,
)


# Test API key
TEST_API_KEY = "kiro_abcdef123456789012345678901234567890abcdef12345678901234567890"


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user."""
    user = User(
        email="submit@test.com",
        username="submituser",
        password_hash=auth_service.hash_password("testpassword123"),
        api_key_hash=auth_service.hash_password(TEST_API_KEY),
        api_key_prefix=TEST_API_KEY[:20],
        verified=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def test_maze(test_session: AsyncSession):
    """Create a test maze."""
    maze = Maze(
        name="Submit Test Maze",
        difficulty="tutorial",
        grid_data="S.E",
        width=3,
        height=1,
        start_x=0,
        start_y=0,
        exit_x=2,
        exit_y=0,
        is_active=True,
    )
    test_session.add(maze)
    await test_session.commit()
    await test_session.refresh(maze)
    return maze


@pytest.fixture
def auth_headers():
    """Return authentication headers."""
    return {"X-API-Key": TEST_API_KEY}


@asynccontextmanager
async def override_db(test_session):
    """Context manager to override database dependency."""
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_code(test_session: AsyncSession, test_user: User, test_maze: Maze, auth_headers: dict):
    """Test POST /v1/submit endpoint."""
    async with override_db(test_session):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/submit",
                json={
                    "maze_id": str(test_maze.id),
                    "code": "# Simple test code\nmove('east')\nmove('east')",
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()

            assert "id" in data
            assert data["user_id"] == str(test_user.id)
            assert data["maze_id"] == str(test_maze.id)
            assert data["status"] == "pending"
            assert data["score"] is None


@pytest.mark.asyncio
async def test_submission_queue():
    """Test submission queue functionality."""
    queue = SubmissionQueue()

    # Test empty queue
    assert queue.pending_count == 0
    assert queue.processing_count == 0

    # Enqueue submissions
    sub_id_1 = uuid.uuid4()
    sub_id_2 = uuid.uuid4()

    await queue.enqueue(sub_id_1)
    await queue.enqueue(sub_id_2)

    assert queue.pending_count == 2

    # Dequeue
    dequeued = await queue.dequeue()
    assert dequeued == sub_id_1
    assert queue.pending_count == 1
    assert queue.processing_count == 1

    # Complete
    queue.complete(sub_id_1)
    assert queue.processing_count == 0


@pytest.mark.asyncio
async def test_code_execution(test_session: AsyncSession, test_user: User, test_maze: Maze):
    """Test code execution in sandbox."""
    service = SubmissionService()

    # Create a submission
    submission = await service.create_submission(
        db=test_session,
        user_id=test_user.id,
        maze_id=test_maze.id,
        code="# Test code\nresult = look()\nprint(result)",
    )

    assert submission.status == "pending"
    assert submission.id is not None

    # Mock sandbox execution
    with patch.object(service.sandbox, "execute_code") as mock_execute:
        with patch.object(service.sandbox, "ensure_network_exists", return_value=True):
            mock_execute.return_value = MagicMock(
                success=True,
                completed=True,
                turns=2,
                output="Maze completed!",
                error=None,
                timed_out=False,
            )

            # Process the submission
            result = await service.process_submission(
                db=test_session,
                submission_id=submission.id,
                api_base_url="http://api:8000",
            )

            assert result.status == "completed"
            assert result.score == 2


@pytest.mark.asyncio
async def test_get_submission(test_session: AsyncSession, test_user: User, test_maze: Maze, auth_headers: dict):
    """Test GET /v1/submission/{id} endpoint."""
    # Create a submission first
    submission = Submission(
        user_id=test_user.id,
        maze_id=test_maze.id,
        code_path="/tmp/test.py",
        status="completed",
        score=42,
    )
    test_session.add(submission)
    await test_session.commit()
    await test_session.refresh(submission)

    async with override_db(test_session):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/v1/submission/{submission.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert data["id"] == str(submission.id)
            assert data["status"] == "completed"
            assert data["score"] == 42
            assert data["turns"] == 42
            assert data["completed"] is True


@pytest.mark.asyncio
async def test_submit_invalid_maze(test_session: AsyncSession, test_user: User, auth_headers: dict):
    """Test submit with non-existent maze."""
    async with override_db(test_session):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/submit",
                json={
                    "maze_id": str(uuid.uuid4()),
                    "code": "move('north')",
                },
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_submission_unauthorized(test_session: AsyncSession, test_user: User, test_maze: Maze, auth_headers: dict):
    """Test that users cannot access others' submissions."""
    # Create submission for a different user
    other_user = User(
        email="other@test.com",
        username="otheruser",
        password_hash=auth_service.hash_password("password"),
        api_key_hash=auth_service.hash_password("kiro_other12345678901234567890123456789012345678901234567890"),
        api_key_prefix="kiro_other1234567890",
        verified=True,
    )
    test_session.add(other_user)
    await test_session.commit()
    await test_session.refresh(other_user)

    submission = Submission(
        user_id=other_user.id,
        maze_id=test_maze.id,
        code_path="/tmp/other.py",
        status="pending",
    )
    test_session.add(submission)
    await test_session.commit()
    await test_session.refresh(submission)

    async with override_db(test_session):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/v1/submission/{submission.id}",
                headers=auth_headers,
            )

            assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_submissions(test_session: AsyncSession, test_user: User, test_maze: Maze, auth_headers: dict):
    """Test GET /v1/submissions endpoint."""
    # Create multiple submissions
    for i in range(3):
        submission = Submission(
            user_id=test_user.id,
            maze_id=test_maze.id,
            code_path=f"/tmp/test_{i}.py",
            status="completed" if i % 2 == 0 else "pending",
            score=i * 10 if i % 2 == 0 else None,
        )
        test_session.add(submission)

    await test_session.commit()

    async with override_db(test_session):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/v1/submissions",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert "submissions" in data
            assert data["total"] >= 3
