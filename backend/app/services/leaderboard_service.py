"""Leaderboard service using Redis sorted sets."""

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from app.db.redis import get_redis


@dataclass
class LeaderboardEntry:
    """A single leaderboard entry."""

    user_id: str
    username: str
    maze_id: str
    score: int  # Lower is better (turn count)
    submitted_at: datetime
    rank: int = 0


class LeaderboardService:
    """Service for managing leaderboards using Redis sorted sets."""

    # Redis key patterns
    GLOBAL_LEADERBOARD_KEY = "leaderboard:global"
    MAZE_LEADERBOARD_KEY = "leaderboard:maze:{maze_id}"
    USER_SCORES_KEY = "user:scores:{user_id}"
    ENTRY_DATA_KEY = "leaderboard:entry:{entry_id}"

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._subscribers: list[asyncio.Queue] = []

    async def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def update_score(
        self,
        user_id: uuid.UUID,
        username: str,
        maze_id: uuid.UUID,
        score: int,
    ) -> tuple[bool, Optional[int]]:
        """
        Update leaderboard with a new score.

        Args:
            user_id: User's ID
            username: User's display name
            maze_id: Maze ID
            score: Turn count (lower is better)

        Returns:
            Tuple of (is_personal_best, new_rank) or (False, None) if not a best
        """
        r = await self._get_redis()

        # Create unique entry ID
        entry_id = f"{user_id}:{maze_id}"

        # Check if this is a personal best for this maze
        existing_entry = await r.hget(self.ENTRY_DATA_KEY.format(entry_id=entry_id), "score")

        if existing_entry is not None:
            existing_score = int(existing_entry)
            if score >= existing_score:
                # Not a personal best
                return False, None

        # Store entry data
        entry_data = {
            "user_id": str(user_id),
            "username": username,
            "maze_id": str(maze_id),
            "score": score,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        await r.hset(
            self.ENTRY_DATA_KEY.format(entry_id=entry_id),
            mapping=entry_data,
        )

        # Update global leaderboard (sorted by score, lower is better)
        await r.zadd(self.GLOBAL_LEADERBOARD_KEY, {entry_id: score})

        # Update maze-specific leaderboard
        await r.zadd(
            self.MAZE_LEADERBOARD_KEY.format(maze_id=str(maze_id)),
            {entry_id: score},
        )

        # Get new rank
        new_rank = await r.zrank(self.GLOBAL_LEADERBOARD_KEY, entry_id)

        # Broadcast update to subscribers
        await self._broadcast_update(entry_data, new_rank + 1 if new_rank is not None else 1)

        return True, new_rank + 1 if new_rank is not None else 1

    async def get_leaderboard(
        self,
        maze_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeaderboardEntry]:
        """
        Get leaderboard entries.

        Args:
            maze_id: Optional maze ID to filter by
            limit: Maximum entries to return
            offset: Offset for pagination

        Returns:
            List of leaderboard entries sorted by score (ascending)
        """
        r = await self._get_redis()

        # Choose which leaderboard to query
        if maze_id:
            key = self.MAZE_LEADERBOARD_KEY.format(maze_id=str(maze_id))
        else:
            key = self.GLOBAL_LEADERBOARD_KEY

        # Get entries with scores
        entries = await r.zrange(key, offset, offset + limit - 1, withscores=True)

        result = []
        for i, (entry_id, score) in enumerate(entries):
            # Get entry data
            entry_data = await r.hgetall(self.ENTRY_DATA_KEY.format(entry_id=entry_id))

            if entry_data:
                result.append(
                    LeaderboardEntry(
                        user_id=entry_data.get("user_id", ""),
                        username=entry_data.get("username", "Unknown"),
                        maze_id=entry_data.get("maze_id", ""),
                        score=int(score),
                        submitted_at=datetime.fromisoformat(
                            entry_data.get("submitted_at", datetime.now(timezone.utc).isoformat())
                        ),
                        rank=offset + i + 1,
                    )
                )

        return result

    async def get_user_rank(
        self,
        user_id: uuid.UUID,
        maze_id: Optional[uuid.UUID] = None,
    ) -> Optional[int]:
        """Get user's rank on the leaderboard."""
        r = await self._get_redis()

        if maze_id:
            key = self.MAZE_LEADERBOARD_KEY.format(maze_id=str(maze_id))
            entry_id = f"{user_id}:{maze_id}"
        else:
            # For global, we need to find any entry for this user
            key = self.GLOBAL_LEADERBOARD_KEY
            # This is a simplification - in reality we'd need to track user's best entry
            return None

        rank = await r.zrank(key, entry_id)
        return rank + 1 if rank is not None else None

    async def get_top_n(
        self,
        n: int = 10,
        maze_id: Optional[uuid.UUID] = None,
    ) -> list[LeaderboardEntry]:
        """Get top N entries from leaderboard."""
        return await self.get_leaderboard(maze_id=maze_id, limit=n, offset=0)

    # WebSocket subscription management
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to leaderboard updates."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from leaderboard updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def _broadcast_update(self, entry_data: dict, rank: int) -> None:
        """Broadcast leaderboard update to all subscribers."""
        message = {
            "type": "leaderboard_update",
            "data": {
                **entry_data,
                "rank": rank,
            },
        }

        # Send to all subscribers
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass  # Skip if queue is full


# Singleton instance
_leaderboard_service: Optional[LeaderboardService] = None


def get_leaderboard_service() -> LeaderboardService:
    """Get singleton leaderboard service."""
    global _leaderboard_service
    if _leaderboard_service is None:
        _leaderboard_service = LeaderboardService()
    return _leaderboard_service
