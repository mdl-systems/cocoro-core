"""cocoro-core — Task Queue (Redis-based)
非同期タスクキュー。Redis Listを使用。
タスクをキューに投入→バックグラウンドWorkerが取り出して実行。
"""
import json
import asyncio
import logging
import uuid
import redis.asyncio as aioredis

logger = logging.getLogger("cocoro.taskqueue")


class TaskQueue:
    """Redis-based 非同期タスクキュー"""

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self.queue_key = "cocoro:task_queue"
        self.results_prefix = "cocoro:task_result:"
        self._running = False

    async def enqueue(self, task_type: str, payload: dict,
                      priority: int = 5) -> str:
        """タスクをキューに投入"""
        task_id = str(uuid.uuid4())
        job = json.dumps({
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
            "priority": priority,
            "status": "queued",
        })
        # 優先度が高い(1)ほど先に処理 → lpush、通常はrpush
        if priority <= 3:
            await self.redis.lpush(self.queue_key, job)
        else:
            await self.redis.rpush(self.queue_key, job)

        logger.info(f"Enqueued: {task_type} ({task_id[:8]}) priority={priority}")
        return task_id

    async def dequeue(self, timeout: int = 5) -> dict | None:
        """キューからタスクを取り出し（ブロッキング）"""
        result = await self.redis.blpop(self.queue_key, timeout=timeout)
        if result:
            _, raw = result
            return json.loads(raw)
        return None

    async def set_result(self, task_id: str, result: dict, ttl: int = 3600):
        """タスク結果を保存"""
        await self.redis.setex(
            f"{self.results_prefix}{task_id}",
            ttl,
            json.dumps(result, default=str),
        )

    async def get_result(self, task_id: str) -> dict | None:
        """タスク結果を取得"""
        raw = await self.redis.get(f"{self.results_prefix}{task_id}")
        return json.loads(raw) if raw else None

    async def queue_length(self) -> int:
        """キュー内のタスク数"""
        return await self.redis.llen(self.queue_key)
