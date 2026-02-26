import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None

def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        ssl=True,                        # ✅ Upstash requires TLS
        ssl_cert_reqs=None,              # ✅ skip cert verification
        socket_connect_timeout=10,       # ✅ don't hang forever
        socket_timeout=10,
        retry_on_timeout=True,
    )

def get_redis() -> aioredis.Redis:
    return redis_client
