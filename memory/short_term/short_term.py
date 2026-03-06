"""cocoro-core — Short-Term Memory (Redis)
現在の会話・思考中データ。TTL付き。
"""
import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger("cocoro.memory.short")


class ShortTermMemory:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def set_context(self, session_id: str, key: str, data: dict, ttl: int = 3600):
        await self.redis.setex(f"stm:{session_id}:{key}", ttl, json.dumps(data, default=str))

    async def get_context(self, session_id: str, key: str) -> dict | None:
        raw = await self.redis.get(f"stm:{session_id}:{key}")
        return json.loads(raw) if raw else None

    async def add_message(self, session_id: str, role: str, content: str):
        msg = json.dumps({"role": role, "content": content})
        key = f"stm:{session_id}:messages"
        await self.redis.rpush(key, msg)
        await self.redis.expire(key, 3600)

    async def get_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        raw = await self.redis.lrange(f"stm:{session_id}:messages", -limit, -1)
        return [json.loads(m) for m in raw]

    async def clear_session(self, session_id: str):
        keys = []
        async for k in self.redis.scan_iter(f"stm:{session_id}:*"):
            keys.append(k)
        if keys:
            await self.redis.delete(*keys)
