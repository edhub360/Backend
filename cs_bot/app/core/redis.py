import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None

def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        ssl=True,               # ✅ force TLS even though URL says redis://
        ssl_cert_reqs=None,     # ✅ skip cert verification (Upstash free tier)
    )

def get_redis() -> aioredis.Redis:
    return redis_client
