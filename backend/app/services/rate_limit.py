"""Shared rate-limiting + de-duplication, Redis-backed with an in-memory fallback.

Why this exists: the per-process dicts used for rate limits and WhatsApp webhook
de-dup work for a single worker, but with 2+ workers/replicas each has its own
memory — so Meta's webhook retries can hit different workers and double-reply or
double-book. Backing these by Redis makes them shared across workers.

  • REDIS_URL set   → Redis backend (shared across workers)
  • REDIS_URL blank → in-memory backend (fine for one worker)
  • Redis configured but unreachable → automatically falls back to memory, never
    crashes a request.

Public API:
  rate_limit_allow(key, max_attempts, window_seconds) -> bool   (True = allowed)
  dedup_seen(key, ttl_seconds) -> bool                          (True = already seen)
"""
from __future__ import annotations

import logging
import threading
import time

from app.config import settings

logger = logging.getLogger(__name__)


# ── In-memory backend ───────────────────────────────────────────────────────────

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}
_seen: dict[str, float] = {}


def _mem_allow(key: str, max_attempts: int, window: int) -> bool:
    now = time.time()
    cutoff = now - window
    with _lock:
        times = [t for t in _hits.get(key, []) if t > cutoff]
        if len(times) >= max_attempts:
            _hits[key] = times
            return False
        times.append(now)
        _hits[key] = times
        return True


def _mem_seen(key: str, ttl: int) -> bool:
    now = time.time()
    with _lock:
        # opportunistic cleanup
        for k in [k for k, exp in _seen.items() if exp < now]:
            _seen.pop(k, None)
        if key in _seen and _seen[key] > now:
            return True
        _seen[key] = now + ttl
        return False


# ── Redis backend (lazy, with graceful degradation) ─────────────────────────────

_redis = None
_redis_failed = False


def _get_redis():
    global _redis, _redis_failed
    if _redis is not None or _redis_failed or not settings.REDIS_URL:
        return _redis
    try:
        import redis
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        client.ping()
        _redis = client
        logger.info("Rate-limit/de-dup using Redis")
    except Exception:
        _redis_failed = True
        logger.warning("REDIS_URL set but Redis unreachable — falling back to in-memory")
    return _redis


def rate_limit_allow(key: str, max_attempts: int, window_seconds: int) -> bool:
    r = _get_redis()
    if r is not None:
        try:
            rk = f"rl:{key}"
            count = r.incr(rk)
            if count == 1:
                r.expire(rk, window_seconds)
            return int(count) <= max_attempts
        except Exception:
            logger.warning("Redis rate_limit failed — using memory for this call")
    return _mem_allow(key, max_attempts, window_seconds)


def dedup_seen(key: str, ttl_seconds: int) -> bool:
    """Atomically check-and-mark. Returns True if the key was already seen."""
    r = _get_redis()
    if r is not None:
        try:
            # SET NX: succeeds only if the key didn't exist → first time we've seen it.
            first_time = r.set(f"seen:{key}", "1", nx=True, ex=ttl_seconds)
            return not bool(first_time)
        except Exception:
            logger.warning("Redis dedup failed — using memory for this call")
    return _mem_seen(key, ttl_seconds)
