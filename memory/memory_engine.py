"""cocoro-core — Memory Engine (統合)"""
from memory.short_term.short_term import ShortTermMemory
from memory.long_term.long_term import LongTermMemory
from memory.vector_memory.vector_memory import VectorMemory


class MemoryEngine:
    """3層記憶を統合管理"""

    def __init__(self, db, redis_url: str):
        self.short = ShortTermMemory(redis_url)
        self.long = LongTermMemory(db)
        self.vector = VectorMemory(db)
        self._db = db

    async def build_context(self, session_id: str, query: str = "") -> str:
        """現在の文脈を構築（感情付き）"""
        parts = []

        # Short-term: 直近の会話（現セッション・10件）
        messages = await self.short.get_messages(session_id, limit=10)
        if messages:
            parts.append("【直近の会話】")
            for m in messages:
                parts.append(f"{m['role']}: {m['content'][:200]}")

        # Long-term: 過去セッションの関連会話（クロスセッション記憶）
        if query and len(query) >= 2:
            try:
                past_rows = await self._db.fetch(
                    "SELECT role, content FROM conversation_log "
                    "WHERE content ILIKE $1 "
                    "AND session_id != $2::uuid "
                    "ORDER BY created_at DESC LIMIT 5",
                    f"%{query[:20]}%", session_id
                )
                if past_rows:
                    parts.append("\n【過去の会話から関連する記憶】")
                    for r in past_rows:
                        parts.append(f"- ({r['role']}) {r['content'][:150]}")
            except Exception:
                pass  # 検索失敗時はスキップ

        # Long-term: 過去の判断
        decisions = await self.long.get_past_decisions(limit=3)
        if decisions:
            parts.append("\n【過去の判断】")
            for d in decisions:
                parts.append(f"- {d['question'][:80]} → {d['decision'][:80]}")

        # Long-term: 学習
        learnings = await self.long.get_learnings(limit=3)
        if learnings:
            parts.append("\n【学んだ教訓】")
            for l in learnings:
                parts.append(f"- {l['lesson'][:120]}")

        # Vector: 関連知識
        if query:
            knowledge = await self.vector.search(query, limit=3)
            if knowledge:
                parts.append("\n【関連知識】")
                for k in knowledge:
                    parts.append(f"- {k['content'][:150]}")

        return "\n".join(parts) if parts else ""
