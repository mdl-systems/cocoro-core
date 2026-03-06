"""cocoro-core — Multi-User Session Manager (C-2)
マルチユーザー対応。ユーザーごとのセッション管理と人格コンテキスト分離。
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("cocoro.users")

JST = timezone(timedelta(hours=9))


class UserSession:
    """ユーザーセッション"""

    def __init__(self, user_id: str, display_name: str = ""):
        self.user_id = user_id
        self.display_name = display_name or user_id
        self.session_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.now(JST)
        self.last_active = datetime.now(JST)
        self.message_count = 0
        self.context: dict = {}  # ユーザー固有コンテキスト

    def touch(self):
        """アクティブ更新"""
        self.last_active = datetime.now(JST)
        self.message_count += 1

    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """セッション期限切れ判定"""
        elapsed = (datetime.now(JST) - self.last_active).total_seconds()
        return elapsed > timeout_minutes * 60

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "is_expired": self.is_expired(),
        }


class MultiUserManager:
    """マルチユーザーセッション管理"""

    def __init__(self, db=None, session_timeout: int = 60):
        self.db = db
        self.session_timeout = session_timeout
        self._sessions: dict[str, UserSession] = {}
        self._user_preferences: dict[str, dict] = {}

    def get_or_create_session(self, user_id: str,
                               display_name: str = "") -> UserSession:
        """セッション取得 or 新規作成"""
        if user_id in self._sessions:
            session = self._sessions[user_id]
            if session.is_expired(self.session_timeout):
                logger.info(f"Session expired for {user_id}, creating new")
                session = UserSession(user_id, display_name)
                self._sessions[user_id] = session
            else:
                session.touch()
            return session

        session = UserSession(user_id, display_name)
        self._sessions[user_id] = session
        logger.info(f"New session: {user_id} ({session.session_id})")
        return session

    def end_session(self, user_id: str) -> bool:
        """セッション終了"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info(f"Session ended: {user_id}")
            return True
        return False

    def set_preference(self, user_id: str, key: str, value) -> None:
        """ユーザー設定を保存"""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][key] = value

    def get_preference(self, user_id: str, key: str, default=None):
        """ユーザー設定を取得"""
        return self._user_preferences.get(user_id, {}).get(key, default)

    def get_user_preferences(self, user_id: str) -> dict:
        """ユーザー全設定を取得"""
        return self._user_preferences.get(user_id, {})

    def set_context(self, user_id: str, key: str, value) -> None:
        """セッションコンテキストを設定"""
        session = self._sessions.get(user_id)
        if session:
            session.context[key] = value

    def get_context(self, user_id: str, key: str, default=None):
        """セッションコンテキストを取得"""
        session = self._sessions.get(user_id)
        if session:
            return session.context.get(key, default)
        return default

    def build_user_prompt_prefix(self, user_id: str) -> str:
        """ユーザー固有のプロンプトプレフィックスを生成"""
        session = self._sessions.get(user_id)
        prefs = self._user_preferences.get(user_id, {})

        if not session and not prefs:
            return ""

        parts = []
        if session:
            parts.append(f"[ユーザー: {session.display_name}]")
            parts.append(f"[セッション: メッセージ{session.message_count}件目]")

        if prefs:
            tone = prefs.get("tone", "")
            lang = prefs.get("language", "")
            if tone:
                parts.append(f"[話し方: {tone}]")
            if lang:
                parts.append(f"[言語: {lang}]")

        return "\n".join(parts)

    def cleanup_expired(self) -> int:
        """期限切れセッションの一括削除"""
        expired = [
            uid for uid, s in self._sessions.items()
            if s.is_expired(self.session_timeout)
        ]
        for uid in expired:
            del self._sessions[uid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        return len(expired)

    def list_active_sessions(self) -> list[dict]:
        """アクティブセッション一覧"""
        return [s.to_dict() for s in self._sessions.values()
                if not s.is_expired(self.session_timeout)]

    def get_stats(self) -> dict:
        """統計"""
        active = [s for s in self._sessions.values()
                  if not s.is_expired(self.session_timeout)]
        total_messages = sum(s.message_count for s in self._sessions.values())
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active),
            "total_users_with_preferences": len(self._user_preferences),
            "total_messages": total_messages,
            "session_timeout_minutes": self.session_timeout,
        }
