"""cocoro-core — Personality Communication (C-3)
複数のcocoro人格間でのコミュニケーション・協議プロトコル。
異なる価値観を持つ人格間で判断を協議し、より良い結論を導く。
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("cocoro.comm")

JST = timezone(timedelta(hours=9))


class PersonalityPeer:
    """通信相手の人格定義"""

    def __init__(self, peer_id: str, name: str, endpoint: str = "",
                 personality_summary: str = ""):
        self.peer_id = peer_id
        self.name = name
        self.endpoint = endpoint
        self.personality_summary = personality_summary
        self.registered_at = datetime.now(JST)
        self.last_contact = None
        self.message_count = 0

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "personality_summary": self.personality_summary,
            "registered_at": self.registered_at.isoformat(),
            "last_contact": self.last_contact.isoformat() if self.last_contact else None,
            "message_count": self.message_count,
        }


class Discussion:
    """人格間の協議セッション"""

    def __init__(self, topic: str, initiator: str):
        self.discussion_id = str(uuid.uuid4())[:8]
        self.topic = topic
        self.initiator = initiator
        self.participants: list[str] = [initiator]
        self.messages: list[dict] = []
        self.status = "active"  # active, concluded, cancelled
        self.conclusion = None
        self.created_at = datetime.now(JST)

    def add_message(self, peer_id: str, content: str,
                    stance: str = "neutral") -> dict:
        """メッセージを追加"""
        msg = {
            "id": len(self.messages) + 1,
            "peer_id": peer_id,
            "content": content,
            "stance": stance,  # agree, disagree, neutral, question
            "timestamp": datetime.now(JST).isoformat(),
        }
        self.messages.append(msg)
        if peer_id not in self.participants:
            self.participants.append(peer_id)
        return msg

    def conclude(self, conclusion: str) -> dict:
        """協議を結論付ける"""
        self.status = "concluded"
        self.conclusion = conclusion
        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "discussion_id": self.discussion_id,
            "topic": self.topic,
            "initiator": self.initiator,
            "participants": self.participants,
            "message_count": len(self.messages),
            "status": self.status,
            "conclusion": self.conclusion,
            "created_at": self.created_at.isoformat(),
            "messages": self.messages[-10:],  # 最新10件のみ
        }


class PersonalityCommunication:
    """人格間コミュニケーション管理"""

    def __init__(self, self_id: str = "cocoro-main"):
        self.self_id = self_id
        self._peers: dict[str, PersonalityPeer] = {}
        self._discussions: dict[str, Discussion] = {}
        self._inbox: list[dict] = []

    def register_peer(self, peer_id: str, name: str,
                      endpoint: str = "",
                      personality_summary: str = "") -> dict:
        """通信相手を登録"""
        peer = PersonalityPeer(peer_id, name, endpoint, personality_summary)
        self._peers[peer_id] = peer
        logger.info(f"Peer registered: {name} ({peer_id})")
        return peer.to_dict()

    def unregister_peer(self, peer_id: str) -> bool:
        """通信相手を解除"""
        if peer_id in self._peers:
            del self._peers[peer_id]
            return True
        return False

    def list_peers(self) -> list[dict]:
        """通信相手一覧"""
        return [p.to_dict() for p in self._peers.values()]

    def start_discussion(self, topic: str, participant_ids: list[str] = None) -> dict:
        """協議セッションを開始"""
        discussion = Discussion(topic, self.self_id)
        if participant_ids:
            for pid in participant_ids:
                if pid in self._peers:
                    discussion.participants.append(pid)
        self._discussions[discussion.discussion_id] = discussion
        logger.info(f"Discussion started: {topic} ({discussion.discussion_id})")
        return discussion.to_dict()

    def add_opinion(self, discussion_id: str, peer_id: str,
                    content: str, stance: str = "neutral") -> dict:
        """協議に意見を追加"""
        disc = self._discussions.get(discussion_id)
        if not disc:
            return {"error": "Discussion not found"}
        if disc.status != "active":
            return {"error": "Discussion already concluded"}
        msg = disc.add_message(peer_id, content, stance)
        # 相手のメッセージカウント更新
        if peer_id in self._peers:
            self._peers[peer_id].message_count += 1
            self._peers[peer_id].last_contact = datetime.now(JST)
        return msg

    def conclude_discussion(self, discussion_id: str,
                             conclusion: str) -> dict:
        """協議を結論付ける"""
        disc = self._discussions.get(discussion_id)
        if not disc:
            return {"error": "Discussion not found"}
        return disc.conclude(conclusion)

    def get_discussion(self, discussion_id: str) -> dict:
        """協議詳細を取得"""
        disc = self._discussions.get(discussion_id)
        if not disc:
            return {"error": "Discussion not found"}
        return disc.to_dict()

    def list_discussions(self, status: str = None) -> list[dict]:
        """協議一覧"""
        discussions = list(self._discussions.values())
        if status:
            discussions = [d for d in discussions if d.status == status]
        return [d.to_dict() for d in discussions]

    def send_message(self, to_peer_id: str, content: str,
                     msg_type: str = "general") -> dict:
        """ダイレクトメッセージ送信"""
        if to_peer_id not in self._peers:
            return {"error": f"Peer not found: {to_peer_id}"}
        peer = self._peers[to_peer_id]
        msg = {
            "id": str(uuid.uuid4())[:8],
            "from": self.self_id,
            "to": to_peer_id,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now(JST).isoformat(),
        }
        peer.message_count += 1
        peer.last_contact = datetime.now(JST)
        logger.info(f"Message sent to {peer.name}: {content[:50]}")
        return msg

    def receive_message(self, from_peer_id: str, content: str,
                        msg_type: str = "general") -> dict:
        """メッセージ受信"""
        msg = {
            "id": str(uuid.uuid4())[:8],
            "from": from_peer_id,
            "to": self.self_id,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now(JST).isoformat(),
        }
        self._inbox.append(msg)
        if from_peer_id in self._peers:
            self._peers[from_peer_id].message_count += 1
            self._peers[from_peer_id].last_contact = datetime.now(JST)
        return msg

    def get_inbox(self, limit: int = 20) -> list[dict]:
        """受信メッセージ一覧"""
        return self._inbox[-limit:]

    def build_consensus_prompt(self, discussion_id: str) -> str:
        """協議内容からコンセンサスプロンプトを生成"""
        disc = self._discussions.get(discussion_id)
        if not disc:
            return ""

        parts = [f"協議テーマ: {disc.topic}", ""]
        for msg in disc.messages:
            peer_name = self._peers.get(msg["peer_id"], None)
            name = peer_name.name if peer_name else msg["peer_id"]
            parts.append(f"[{name}] ({msg['stance']}): {msg['content']}")

        parts.append("")
        parts.append("上記の意見を踏まえ、バランスの取れた結論を導いてください。")
        return "\n".join(parts)

    def get_stats(self) -> dict:
        """統計"""
        active_disc = sum(
            1 for d in self._discussions.values() if d.status == "active"
        )
        return {
            "self_id": self.self_id,
            "peer_count": len(self._peers),
            "total_discussions": len(self._discussions),
            "active_discussions": active_disc,
            "inbox_count": len(self._inbox),
        }
