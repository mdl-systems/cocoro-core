"""cocoro-core — Discord / LINE Bot Integration (D-3)
外部メッセージングプラットフォームとの連携ブリッジ。
Webhook ベースの非同期連携で、受信→人格応答→返信の流れを実現。
"""
import os
import logging
import hashlib
import hmac
import httpx

logger = logging.getLogger("cocoro.integration")


class DiscordBridge:
    """Discord Bot Webhook ブリッジ"""

    def __init__(self, webhook_url: str = None, bot_token: str = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        self.bot_token = bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
        self._message_count = 0

    async def send_message(self, content: str, username: str = "cocoro") -> dict:
        """Discord Webhookに メッセージ送信"""
        if not self.webhook_url:
            return {"sent": False, "error": "DISCORD_WEBHOOK_URL not configured"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.webhook_url, json={
                    "content": content[:2000],  # Discord limit
                    "username": username,
                })
                self._message_count += 1
                return {
                    "sent": resp.status_code in (200, 204),
                    "status": resp.status_code,
                }
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return {"sent": False, "error": str(e)}

    def parse_interaction(self, payload: dict) -> dict:
        """Discord Interaction ペイロードの解析"""
        itype = payload.get("type", 0)
        if itype == 1:  # PING
            return {"type": "ping", "response": {"type": 1}}
        if itype == 2:  # APPLICATION_COMMAND
            data = payload.get("data", {})
            options = {o["name"]: o.get("value") for o in data.get("options", [])}
            return {
                "type": "command",
                "name": data.get("name", ""),
                "options": options,
                "user_id": payload.get("member", {}).get("user", {}).get("id"),
                "channel_id": payload.get("channel_id"),
            }
        return {"type": "unknown", "raw_type": itype}

    def get_status(self) -> dict:
        return {
            "platform": "discord",
            "configured": bool(self.webhook_url),
            "bot_token_set": bool(self.bot_token),
            "messages_sent": self._message_count,
        }


class LINEBridge:
    """LINE Messaging API ブリッジ"""

    def __init__(self, channel_token: str = None, channel_secret: str = None):
        self.channel_token = channel_token or os.getenv("LINE_CHANNEL_TOKEN", "")
        self.channel_secret = channel_secret or os.getenv("LINE_CHANNEL_SECRET", "")
        self._reply_count = 0

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Webhook 署名検証"""
        if not self.channel_secret:
            return False
        h = hmac.new(self.channel_secret.encode(), body, hashlib.sha256)
        expected = h.digest()
        import base64
        return hmac.compare_digest(
            base64.b64encode(expected).decode(), signature
        )

    def parse_webhook(self, payload: dict) -> list[dict]:
        """LINE Webhook イベント解析"""
        events = []
        for event in payload.get("events", []):
            parsed = {
                "type": event.get("type", "unknown"),
                "reply_token": event.get("replyToken"),
                "user_id": event.get("source", {}).get("userId"),
                "timestamp": event.get("timestamp"),
            }
            if event.get("type") == "message":
                msg = event.get("message", {})
                parsed["message_type"] = msg.get("type", "text")
                parsed["text"] = msg.get("text", "")
            events.append(parsed)
        return events

    async def reply(self, reply_token: str, text: str) -> dict:
        """LINE返信メッセージ送信"""
        if not self.channel_token:
            return {"sent": False, "error": "LINE_CHANNEL_TOKEN not configured"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.line.me/v2/bot/message/reply",
                    headers={
                        "Authorization": f"Bearer {self.channel_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "replyToken": reply_token,
                        "messages": [{"type": "text", "text": text[:5000]}],
                    },
                )
                self._reply_count += 1
                return {"sent": resp.status_code == 200, "status": resp.status_code}
        except Exception as e:
            logger.error(f"LINE reply failed: {e}")
            return {"sent": False, "error": str(e)}

    def get_status(self) -> dict:
        return {
            "platform": "line",
            "configured": bool(self.channel_token),
            "secret_set": bool(self.channel_secret),
            "replies_sent": self._reply_count,
        }


class IntegrationManager:
    """統合プラットフォーム管理"""

    def __init__(self):
        self.discord = DiscordBridge()
        self.line = LINEBridge()

    def get_all_status(self) -> dict:
        return {
            "discord": self.discord.get_status(),
            "line": self.line.get_status(),
            "platforms_configured": sum([
                bool(self.discord.webhook_url),
                bool(self.line.channel_token),
            ]),
        }
