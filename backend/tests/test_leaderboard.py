"""Tests for leaderboard endpoints and services."""

import asyncio
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.leaderboard_service import (
    LeaderboardService,
    LeaderboardEntry,
    get_leaderboard_service,
)


@pytest.mark.asyncio
async def test_get_leaderboard():
    """Test GET /v1/leaderboard endpoint."""
    # Mock Redis operations
    mock_redis = AsyncMock()
    mock_redis.zrange = AsyncMock(return_value=[
        ("user1:maze1", 100),
        ("user2:maze1", 150),
        ("user3:maze1", 200),
    ])
    mock_redis.hgetall = AsyncMock(side_effect=[
        {
            "user_id": str(uuid.uuid4()),
            "username": "player1",
            "maze_id": str(uuid.uuid4()),
            "score": "100",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "user_id": str(uuid.uuid4()),
            "username": "player2",
            "maze_id": str(uuid.uuid4()),
            "score": "150",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "user_id": str(uuid.uuid4()),
            "username": "player3",
            "maze_id": str(uuid.uuid4()),
            "score": "200",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
    ])

    with patch("app.services.leaderboard_service.get_redis", return_value=mock_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/leaderboard")

            assert response.status_code == 200
            data = response.json()

            assert "entries" in data
            assert "total" in data
            assert len(data["entries"]) == 3
            assert data["entries"][0]["rank"] == 1
            assert data["entries"][1]["rank"] == 2
            assert data["entries"][2]["rank"] == 3


@pytest.mark.asyncio
async def test_redis_storage():
    """Test that leaderboard data is stored in Redis sorted sets."""
    # Create a mock Redis client
    mock_redis = AsyncMock()
    mock_redis.hget = AsyncMock(return_value=None)  # No existing score
    mock_redis.hset = AsyncMock()
    mock_redis.zadd = AsyncMock()
    mock_redis.zrank = AsyncMock(return_value=0)  # Rank 1 (0-indexed)

    service = LeaderboardService()
    service._redis = mock_redis

    user_id = uuid.uuid4()
    maze_id = uuid.uuid4()

    # Update score
    is_best, rank = await service.update_score(
        user_id=user_id,
        username="testplayer",
        maze_id=maze_id,
        score=100,
    )

    assert is_best is True
    assert rank == 1

    # Verify Redis operations were called
    mock_redis.hset.assert_called()
    assert mock_redis.zadd.call_count >= 1

    # Verify global leaderboard was updated
    zadd_calls = mock_redis.zadd.call_args_list
    global_call = [c for c in zadd_calls if "global" in str(c)]
    assert len(global_call) > 0


@pytest.mark.asyncio
async def test_leaderboard_update():
    """Test that leaderboard is updated on successful submission."""
    # Create a mock Redis client
    mock_redis = AsyncMock()
    mock_redis.hget = AsyncMock(side_effect=[None, "100"])  # First call: no existing, second: existing
    mock_redis.hset = AsyncMock()
    mock_redis.zadd = AsyncMock()
    mock_redis.zrank = AsyncMock(return_value=0)

    service = LeaderboardService()
    service._redis = mock_redis

    user_id = uuid.uuid4()
    maze_id = uuid.uuid4()

    # First submission - should update
    is_best, rank = await service.update_score(
        user_id=user_id,
        username="testplayer",
        maze_id=maze_id,
        score=100,
    )
    assert is_best is True
    assert rank == 1

    # Second submission with worse score - should NOT update
    is_best, rank = await service.update_score(
        user_id=user_id,
        username="testplayer",
        maze_id=maze_id,
        score=150,  # Worse score
    )
    assert is_best is False
    assert rank is None


@pytest.mark.asyncio
async def test_websocket():
    """Test WebSocket connection for real-time updates."""
    service = get_leaderboard_service()

    # Subscribe to updates
    queue = service.subscribe()

    try:
        # Verify queue was added to subscribers
        assert queue in service._subscribers

        # Simulate an update broadcast
        test_message = {
            "type": "leaderboard_update",
            "data": {
                "user_id": str(uuid.uuid4()),
                "username": "testplayer",
                "maze_id": str(uuid.uuid4()),
                "score": 100,
                "rank": 1,
            },
        }
        queue.put_nowait(test_message)

        # Verify message was received
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received == test_message

    finally:
        # Unsubscribe
        service.unsubscribe(queue)
        assert queue not in service._subscribers


@pytest.mark.asyncio
async def test_broadcast():
    """Test that updates are broadcast to all subscribers."""
    service = LeaderboardService()

    # Create mock Redis
    mock_redis = AsyncMock()
    mock_redis.hget = AsyncMock(return_value=None)
    mock_redis.hset = AsyncMock()
    mock_redis.zadd = AsyncMock()
    mock_redis.zrank = AsyncMock(return_value=0)
    service._redis = mock_redis

    # Subscribe multiple clients
    queue1 = service.subscribe()
    queue2 = service.subscribe()
    queue3 = service.subscribe()

    try:
        # Update score (this should broadcast to all subscribers)
        await service.update_score(
            user_id=uuid.uuid4(),
            username="broadcaster",
            maze_id=uuid.uuid4(),
            score=50,
        )

        # All queues should have received the update
        for queue in [queue1, queue2, queue3]:
            assert not queue.empty()
            message = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert message["type"] == "leaderboard_update"
            assert message["data"]["username"] == "broadcaster"
            assert message["data"]["score"] == 50

    finally:
        service.unsubscribe(queue1)
        service.unsubscribe(queue2)
        service.unsubscribe(queue3)


class TestLeaderboardService:
    """Additional tests for the leaderboard service."""

    @pytest.mark.asyncio
    async def test_get_top_n(self):
        """Test getting top N entries."""
        mock_redis = AsyncMock()
        mock_redis.zrange = AsyncMock(return_value=[
            ("user1:maze1", 50),
            ("user2:maze1", 75),
        ])
        mock_redis.hgetall = AsyncMock(side_effect=[
            {
                "user_id": "user1",
                "username": "top1",
                "maze_id": "maze1",
                "score": "50",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": "user2",
                "username": "top2",
                "maze_id": "maze1",
                "score": "75",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
        ])

        service = LeaderboardService()
        service._redis = mock_redis

        entries = await service.get_top_n(n=2)

        assert len(entries) == 2
        assert entries[0].username == "top1"
        assert entries[0].rank == 1
        assert entries[1].username == "top2"
        assert entries[1].rank == 2

    @pytest.mark.asyncio
    async def test_maze_specific_leaderboard(self):
        """Test maze-specific leaderboard filtering."""
        mock_redis = AsyncMock()
        maze_id = uuid.uuid4()
        mock_redis.zrange = AsyncMock(return_value=[
            (f"user1:{maze_id}", 100),
        ])
        mock_redis.hgetall = AsyncMock(return_value={
            "user_id": "user1",
            "username": "mazerunner",
            "maze_id": str(maze_id),
            "score": "100",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        })

        service = LeaderboardService()
        service._redis = mock_redis

        entries = await service.get_leaderboard(maze_id=maze_id)

        assert len(entries) == 1
        assert entries[0].maze_id == str(maze_id)

        # Verify correct Redis key was used
        mock_redis.zrange.assert_called_once()
        call_args = mock_redis.zrange.call_args[0][0]
        assert str(maze_id) in call_args

    @pytest.mark.asyncio
    async def test_personal_best_only_updates_on_improvement(self):
        """Test that score only updates when it improves."""
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.zadd = AsyncMock()
        mock_redis.zrank = AsyncMock(return_value=0)

        service = LeaderboardService()
        service._redis = mock_redis

        user_id = uuid.uuid4()
        maze_id = uuid.uuid4()

        # First submission
        mock_redis.hget = AsyncMock(return_value=None)
        is_best, _ = await service.update_score(user_id, "player", maze_id, 100)
        assert is_best is True

        # Better submission
        mock_redis.hget = AsyncMock(return_value="100")
        is_best, _ = await service.update_score(user_id, "player", maze_id, 80)
        assert is_best is True

        # Equal submission
        mock_redis.hget = AsyncMock(return_value="80")
        is_best, _ = await service.update_score(user_id, "player", maze_id, 80)
        assert is_best is False

        # Worse submission
        is_best, _ = await service.update_score(user_id, "player", maze_id, 90)
        assert is_best is False
