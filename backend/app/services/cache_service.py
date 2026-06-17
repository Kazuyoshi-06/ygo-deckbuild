import logging

import redis.asyncio as redis
from fastapi import Request

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_PREFIX = "ygo:cache:"
DEFAULT_TTL = 300  # 5 minutes

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _key_for_request(request: Request) -> str:
    return f"{CACHE_PREFIX}{request.url.path}?{request.url.query}"


async def get_cached(request: Request) -> str | None:
    """Best-effort cache read. Returns None on a miss or if Redis is unreachable."""
    try:
        return await _get_client().get(_key_for_request(request))
    except Exception:
        logger.warning("Cache read failed, falling back to a live query", exc_info=True)
        return None


async def set_cached(request: Request, body: str, ttl: int = DEFAULT_TTL) -> None:
    """Best-effort cache write. Silently no-ops if Redis is unreachable."""
    try:
        await _get_client().set(_key_for_request(request), body, ex=ttl)
    except Exception:
        logger.warning("Cache write failed, continuing without caching this response", exc_info=True)


async def invalidate_all() -> None:
    """Clear every cached endpoint response. Called after a deck import changes the data these endpoints summarize."""
    try:
        client = _get_client()
        keys = [key async for key in client.scan_iter(match=f"{CACHE_PREFIX}*")]
        if keys:
            await client.delete(*keys)
    except Exception:
        logger.warning("Cache invalidation failed", exc_info=True)
