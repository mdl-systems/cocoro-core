"""cocoro-core — Webhook通知
Discord/Slack等への通知を送信する。
"""
import os
import logging
import httpx

logger = logging.getLogger("cocoro.webhook")


class WebhookNotifier:
    """Webhook通知クライアント"""

    def __init__(self):
        self.url = os.getenv("WEBHOOK_URL", "")
        self.enabled = bool(self.url)
        if self.enabled:
            logger.info(f"Webhook enabled: {self.url[:40]}...")

    async def notify(self, event: str, data: dict) -> bool:
        """イベント通知を送信"""
        if not self.enabled:
            return False

        payload = self._build_payload(event, data)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.url, json=payload)
                resp.raise_for_status()
                logger.info(f"Webhook sent: {event}")
                return True
        except Exception as e:
            logger.error(f"Webhook failed: {event}: {e}")
            return False

    def _build_payload(self, event: str, data: dict) -> dict:
        """Discord Webhook形式のペイロードを構築"""
        emoji = {
            "consolidation": "🧠",
            "decision": "⚖️",
            "learning": "📚",
            "error": "❌",
            "growth": "🌱",
        }.get(event, "📢")

        title = f"{emoji} cocoro-core: {event}"
        description = data.get("summary", str(data)[:500])

        # Discord embed形式
        return {
            "embeds": [{
                "title": title,
                "description": description,
                "color": 0x00D4AA if event != "error" else 0xFF4444,
                "fields": [
                    {"name": k, "value": str(v)[:200], "inline": True}
                    for k, v in data.items()
                    if k != "summary" and v
                ][:5],
            }]
        }

    async def notify_consolidation(self, result: dict):
        """記憶定着の結果を通知"""
        summary = result.get("growth_summary", "完了")
        learnings = result.get("learnings", [])
        await self.notify("consolidation", {
            "summary": f"記憶定着完了: {summary}",
            "学習数": len(learnings),
            "詳細": summary,
        })

    async def notify_error(self, error_type: str, message: str):
        """エラー通知"""
        await self.notify("error", {
            "summary": f"エラー発生: {error_type}",
            "エラー種別": error_type,
            "メッセージ": message,
        })
