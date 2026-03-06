"""cocoro-core — Long-Term Memory (PostgreSQL)
永続記憶。会話・思考・判断・学習をすべて保存。
"""
import json
import uuid
import logging

logger = logging.getLogger("cocoro.memory.long")


class LongTermMemory:
    def __init__(self, db):
        self.db = db

    # === Conversation ===
    async def save_message(self, session_id: str, role: str, content: str, emotion: str = "neutral") -> str:
        row = await self.db.fetchrow(
            "INSERT INTO conversation_log (session_id, role, content, emotion) "
            "VALUES ($1::uuid,$2,$3,$4) RETURNING id", session_id, role, content, emotion,
        )
        return str(row["id"])

    async def get_session(self, session_id: str, limit: int = 50) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT role, content, emotion, created_at FROM conversation_log "
            "WHERE session_id=$1::uuid ORDER BY created_at LIMIT $2", session_id, limit,
        )
        return [dict(r) for r in rows]

    # === Thought ===
    async def save_thought(self, thought_type: str, input_summary: str, reasoning_chain: str,
                           conclusion: str = "", confidence: float = 0.0,
                           values_applied: list = None, session_id: str = None) -> str:
        row = await self.db.fetchrow(
            "INSERT INTO thought_log (session_id, thought_type, input_summary, reasoning_chain, "
            "conclusion, confidence, values_applied) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7) RETURNING id",
            session_id, thought_type, input_summary, reasoning_chain,
            conclusion, confidence, json.dumps(values_applied or []),
        )
        return str(row["id"])

    # === Decision ===
    async def save_decision(self, category: str, question: str, decision: str,
                            reasoning: str = "", confidence: float = 0.0,
                            values_used: list = None, options: list = None) -> str:
        row = await self.db.fetchrow(
            "INSERT INTO decision_log (category, question, decision, reasoning, confidence, "
            "values_used, options) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id",
            category, question, decision, reasoning, confidence,
            json.dumps(values_used or []), json.dumps(options or []),
        )
        return str(row["id"])

    async def get_past_decisions(self, category: str = None, limit: int = 10) -> list[dict]:
        if category:
            rows = await self.db.fetch(
                "SELECT * FROM decision_log WHERE category=$1 ORDER BY created_at DESC LIMIT $2",
                category, limit)
        else:
            rows = await self.db.fetch(
                "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

    # === Learning ===
    async def save_learning(self, source: str, lesson: str, category: str = "general",
                            importance: int = 5, source_id: str = None) -> str:
        row = await self.db.fetchrow(
            "INSERT INTO learning_log (source, source_id, lesson, category, importance) "
            "VALUES ($1,$2::uuid,$3,$4,$5) RETURNING id",
            source, source_id, lesson, category, importance,
        )
        return str(row["id"])

    async def get_learnings(self, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT * FROM learning_log ORDER BY importance DESC, created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]
