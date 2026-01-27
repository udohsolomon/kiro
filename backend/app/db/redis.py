"""Redis connection and helper functions."""

from typing import Optional

import redis.asyncio as redis

from app.config import get_settings


settings = get_settings()

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_pool, _redis_client

    if _redis_client is None:
        # Railway's public Redis URL uses TCP proxy which requires SSL
        # Detect Railway by checking if URL contains 'railway' or proxy domain
        redis_url = settings.redis_url
        use_ssl = 'railway' in redis_url or 'rlwy.net' in redis_url
        
        _redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_pool, _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
