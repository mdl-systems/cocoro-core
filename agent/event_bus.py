"""cocoro-core — Event Bus (Redis Pub/Sub)
Agent間の非同期イベント通信。
パターン: イベント発火 → 購読者に通知
"""
import json
import asyncio
import logging
import redis.asyncio as aioredis
from typing import Callable

logger = logging.getLogger("cocoro.eventbus")


class EventBus:
    """Redis Pub/Sub ベースのイベントバス"""

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self._handlers: dict[str, list[Callable]] = {}
        self._listener_task = None

    async def publish(self, event: str, data: dict):
        """イベントを発火"""
        payload = json.dumps({"event": event, "data": data}, default=str)
        channel = f"cocoro:event:{event}"
        await self.redis.publish(channel, payload)
        logger.info(f"Event published: {event}")

    def subscribe(self, event: str, handler: Callable):
        """イベントハンドラを登録"""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        logger.info(f"Handler registered: {event} → {handler.__name__}")

    async def start_listener(self):
        """全登録チャンネルのリスナーを開始"""
        if not self._handlers:
            return

        pubsub = self.redis.pubsub()
        channels = [f"cocoro:event:{e}" for e in self._handlers.keys()]
        await pubsub.subscribe(*channels)
        logger.info(f"Event listener started: {list(self._handlers.keys())}")

        self._listener_task = asyncio.create_task(self._listen(pubsub))

    async def _listen(self, pubsub):
        """メッセージをリッスンしてハンドラを呼び出す"""
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    event = payload["event"]
                    data = payload["data"]
                    handlers = self._handlers.get(event, [])
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                        except Exception as e:
                            logger.error(f"Handler error ({event}): {e}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid event message: {e}")
        except asyncio.CancelledError:
            await pubsub.unsubscribe()

    async def stop(self):
        """リスナーを停止"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
