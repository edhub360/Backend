import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None

def init_redis():
    global redis_client
    # ✅ Convert redis:// → rediss:// for TLS (Upstash requires this)
    redis_url = settings.REDIS_URL.replace("redis://", "rediss://")
    redis_client = aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
        retry_on_timeout=True,
    )

def get_redis() -> aioredis.Redis:
    return redis_client
