import json
from app.core.redis import get_redis
from app.core.config import settings
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

def _serialize(messages: list[BaseMessage]) -> str:
    return json.dumps([
        {"type": m.type, "content": m.content}
        for m in messages
    ])

def _deserialize(data: str) -> list[BaseMessage]:
    raw = json.loads(data)
    result = []
    for item in raw:
        if item["type"] == "human":
            result.append(HumanMessage(content=item["content"]))
        elif item["type"] == "ai":
            result.append(AIMessage(content=item["content"]))
    return result

async def get_history(session_id: str) -> list[BaseMessage]:
    redis = get_redis()
    data = await redis.get(f"chat:{session_id}")
    if not data:
        return []
    return _deserialize(data)

async def save_history(session_id: str, messages: list[BaseMessage]):
    redis = get_redis()
    await redis.setex(
        f"chat:{session_id}",
        settings.SESSION_TTL_SECONDS,
        _serialize(messages),
    )

async def delete_history(session_id: str):
    redis = get_redis()
    await redis.delete(f"chat:{session_id}")
