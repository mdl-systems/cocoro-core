"""cocoro-core — Belief System
信念 = 経験から形成される「真だと信じること」。
確信度(confidence)は経験によって変動する。
"""
import logging

logger = logging.getLogger("cocoro.beliefs")


class BeliefSystem:
    """信念管理 — 経験で進化する信念体系"""

    def __init__(self, db):
        self.db = db

    async def get_all(self) -> list[dict]:
        rows = await self.db.fetch("SELECT * FROM beliefs ORDER BY confidence DESC")
        return [dict(r) for r in rows]

    async def get_strong(self, threshold: float = 0.7) -> list[dict]:
        """確信度の高い信念のみ取得"""
        rows = await self.db.fetch(
            "SELECT * FROM beliefs WHERE confidence >= $1 ORDER BY confidence DESC", threshold
        )
        return [dict(r) for r in rows]

    async def add(self, statement: str, confidence: float = 0.5, source: str = "experience") -> dict:
        row = await self.db.fetchrow(
            "INSERT INTO beliefs (statement, confidence, source) VALUES ($1,$2,$3) RETURNING *",
            statement, confidence, source,
        )
        logger.info(f"Belief added: '{statement[:50]}' (conf={confidence})")
        return dict(row)

    async def reinforce(self, belief_id: str, delta: float = 0.05) -> dict | None:
        """信念を強化/弱体化する (経験による学習)"""
        row = await self.db.fetchrow(
            "UPDATE beliefs SET confidence = LEAST(1.0, GREATEST(0.0, confidence + $1)), "
            "evidence_count = evidence_count + 1 WHERE id=$2::uuid RETURNING *",
            delta, belief_id,
        )
        if row:
            logger.info(f"Belief reinforced: '{row['statement'][:40]}' → {row['confidence']:.2f}")
            return dict(row)
        return None

    async def challenge(self, belief_id: str) -> dict | None:
        """反証により信念を弱体化"""
        return await self.reinforce(belief_id, delta=-0.1)

    async def to_prompt(self) -> str:
        beliefs = await self.get_strong(0.6)
        if not beliefs:
            return ""
        lines = ["【信念】"]
        for b in beliefs[:5]:
            lines.append(f"- {b['statement']} (確信度: {b['confidence']:.1f})")
        return "\n".join(lines)
