import time
import os
import threading
import logging
import redis

logger = logging.getLogger(__name__)

_redis_client = None
_redis_available = None

_memory_store: dict = {}
_memory_lock = threading.Lock()


def get_redis_client():
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                client = redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                _redis_client = client
                _redis_available = True
            except Exception as e:
                logger.warning(f"Redis indisponible pour le rate limiting ({e}). Fallback mémoire actif.")
                _redis_available = False
        else:
            _redis_available = False
    return _redis_client


def _memory_check_rate_limit(key, limit, window):
    """Sliding window rate limiter en mémoire — thread-safe via Lock."""
    now = time.time()
    with _memory_lock:
        attempts = _memory_store.get(key, [])
        attempts = [t for t in attempts if now - t < window]
        blocked = len(attempts) >= limit
        attempts.append(now)
        _memory_store[key] = attempts
    return blocked


def check_rate_limit(key_prefix, identifier, limit=5, window=60):
    """
    Vérifie si un identifiant (IP, username) dépasse la limite de tentatives.
    Utilise Redis (sliding window atomique) si disponible,
    sinon fallback mémoire thread-safe (actif même sans Redis).
    """
    client = get_redis_client()
    key = f"ratelimit:{key_prefix}:{identifier}"

    if client:
        try:
            pipe = client.pipeline()
            now = time.time()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            results = pipe.execute()
            return results[1] >= limit
        except Exception as e:
            logger.warning(f"Erreur Redis rate limit ({e}), bascule sur fallback mémoire.")

    return _memory_check_rate_limit(key, limit, window)


def record_failed_attempt(key_prefix, identifier, window=60):
    """Déjà géré par check_rate_limit (sliding window)."""
    pass
