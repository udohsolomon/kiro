"""Tests for session management endpoints."""

import pytest
import uuid
from datetime import datetime, timezone

from app.models.maze import Maze
from app.models.user import User
from app.models.session import Session
from app.services import auth_service


# Sample maze for testing
SIMPLE_MAZE = """XXXXX
XS..X
X.X.X
X..EX
XXXXX"""


TEST_API_KEY = "kiro_abcdef123456789012345678901234567890abcdef12345678901234567890"


@pytest.fixture
async def test_user(test_session):
    """Create a verified test user with API key."""
    # Use hash_password for API key hash (same bcrypt hashing)
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash=auth_service.hash_password("TestPass123!"),
        api_key_hash=auth_service.hash_password(TEST_API_KEY),
        api_key_prefix=TEST_API_KEY[:20],  # First 20 chars
        verified=True,
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
async def test_maze(test_session):
    """Create a test maze."""
    maze = Maze(
        id=uuid.uuid4(),
        name="Test Maze",
        difficulty="tutorial",
        grid_data=SIMPLE_MAZE,
        width=5,
        height=5,
        start_x=1,
        start_y=1,
        exit_x=3,
        exit_y=3,
        is_active=True,
    )
    test_session.add(maze)
    await test_session.commit()
    return maze


@pytest.mark.asyncio
async def test_create_session(client, test_session, test_user, test_maze):
    """Test POST /v1/session endpoint to create a session (T-05.1 verification)."""
    # Test 1: Create session with valid API key and maze
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["user_id"] == str(test_user.id)
    assert data["maze_id"] == str(test_maze.id)
    assert "current_position" in data
    assert data["current_position"]["x"] == 1  # Start X
    assert data["current_position"]["y"] == 1  # Start Y
    assert data["turn_count"] == 0
    assert data["is_stuck"] is False
    assert data["status"] == "active"

    # Test 2: Create session without API key should fail
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
    )
    assert response.status_code == 401

    # Test 3: Create session with non-existent maze should fail
    non_existent_maze_id = uuid.uuid4()
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(non_existent_maze_id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_tracking(client, test_session, test_user, test_maze):
    """Test that session properly tracks position and turn count (T-05.2 verification)."""
    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_data = response.json()
    session_id = session_data["id"]

    # Initial state check
    assert session_data["current_position"]["x"] == 1
    assert session_data["current_position"]["y"] == 1
    assert session_data["turn_count"] == 0

    # Make a move
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "east"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    move_data = response.json()

    # Check that move was tracked
    assert move_data["turns"] == 1
    assert move_data["position"]["x"] == 2  # Moved east
    assert move_data["position"]["y"] == 1

    # Verify session state persisted
    response = await client.get(
        f"/v1/session/{session_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    state_data = response.json()
    assert state_data["turn_count"] == 1
    assert state_data["current_position"]["x"] == 2
    assert state_data["current_position"]["y"] == 1


@pytest.mark.asyncio
async def test_get_session(client, test_session, test_user, test_maze):
    """Test GET /v1/session/{id} endpoint (T-05.3 verification)."""
    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Test 1: Get session by ID
    response = await client.get(
        f"/v1/session/{session_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["id"] == session_id
    assert data["maze_id"] == str(test_maze.id)
    assert "current_position" in data
    assert "turn_count" in data
    assert "is_stuck" in data
    assert "status" in data
    assert "created_at" in data

    # Test 2: Get non-existent session
    non_existent_id = uuid.uuid4()
    response = await client.get(
        f"/v1/session/{non_existent_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 404

    # Test 3: Get session without API key
    response = await client.get(f"/v1/session/{session_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_move(client, test_session, test_user, test_maze):
    """Test POST /v1/session/{id}/move endpoint (T-06.1 verification)."""
    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Test 1: Valid move east
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "east"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "moved"
    assert data["position"]["x"] == 2
    assert data["position"]["y"] == 1
    assert data["turns"] == 1

    # Test 2: Invalid direction should fail
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "up"},  # Invalid - should be north
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_look(client, test_session, test_user, test_maze):
    """Test POST /v1/session/{id}/look endpoint (T-06.2 verification)."""
    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]
    initial_turn_count = response.json()["turn_count"]

    # Test 1: Look should return surrounding cells
    response = await client.post(
        f"/v1/session/{session_id}/look",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Starting at (1,1), should see:
    # North (1,0) = X (wall)
    # South (1,2) = . (open)
    # East (2,1) = . (open)
    # West (0,1) = X (wall)
    assert data["north"] == "X"
    assert data["south"] == "."
    assert data["east"] == "."
    assert data["west"] == "X"

    # Test 2: Look should NOT increment turn count (it's FREE)
    response = await client.get(
        f"/v1/session/{session_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    assert response.json()["turn_count"] == initial_turn_count


@pytest.mark.asyncio
async def test_wall_collision(client, test_session, test_user, test_maze):
    """Test wall collision handling (T-06.3 verification)."""
    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(test_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Try to move into a wall (north from start position)
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "north"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be blocked
    assert data["status"] == "blocked"
    # Position should not change
    assert data["position"]["x"] == 1
    assert data["position"]["y"] == 1
    # Turn should still be consumed
    assert data["turns"] == 1


@pytest.mark.asyncio
async def test_mud_tiles(client, test_session, test_user):
    """Test mud tile handling (T-06.3 verification)."""
    # Create a maze with mud
    mud_maze = Maze(
        id=uuid.uuid4(),
        name="Mud Maze",
        difficulty="tutorial",
        grid_data="""XXXXX
XS#.X
X...X
X..EX
XXXXX""",
        width=5,
        height=5,
        start_x=1,
        start_y=1,
        exit_x=3,
        exit_y=3,
        is_active=True,
    )
    test_session.add(mud_maze)
    await test_session.commit()

    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(mud_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Move into mud (east from start)
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "east"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Should step in mud
    assert data["status"] == "mud"
    assert data["position"]["x"] == 2
    assert data["position"]["y"] == 1
    assert "mud" in data["message"].lower()

    # Next move should be stuck
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "east"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be stuck (movement skipped)
    assert data["status"] == "stuck"
    # Position should NOT change (still at mud position)
    assert data["position"]["x"] == 2
    assert data["position"]["y"] == 1


@pytest.mark.asyncio
async def test_maze_completion(client, test_session, test_user):
    """Test maze completion detection (T-06.4 verification)."""
    # Create a simple maze where exit is easily reachable
    simple_maze = Maze(
        id=uuid.uuid4(),
        name="Simple Exit Maze",
        difficulty="tutorial",
        grid_data="""XXX
XSE
XXX""",
        width=3,
        height=3,
        start_x=1,
        start_y=1,
        exit_x=2,
        exit_y=1,
        is_active=True,
    )
    test_session.add(simple_maze)
    await test_session.commit()

    # Create a session
    response = await client.post(
        "/v1/session",
        json={"maze_id": str(simple_maze.id)},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Move east to reach exit
    response = await client.post(
        f"/v1/session/{session_id}/move",
        json={"direction": "east"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be completed
    assert data["status"] == "completed"
    assert data["position"]["x"] == 2
    assert data["position"]["y"] == 1
    assert "congratulations" in data["message"].lower() or "escaped" in data["message"].lower()

    # Verify session is marked as completed
    response = await client.get(
        f"/v1/session/{session_id}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
