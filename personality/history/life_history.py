"""cocoro-core — Life History
人生経験の蓄積。人格形成の「体験」を記録する。
"""
import logging

logger = logging.getLogger("cocoro.history")


class LifeHistory:
    """人生経験トラッカー"""

    def __init__(self, db):
        self.db = db

    async def add_event(self, event_type: str, title: str, description: str = "",
                        impact_score: int = 5, lessons: str = "") -> dict:
        row = await self.db.fetchrow(
            "INSERT INTO life_history (event_type, title, description, impact_score, lessons_learned) "
            "VALUES ($1,$2,$3,$4,$5) RETURNING *",
            event_type, title, description, impact_score, lessons,
        )
        logger.info(f"History recorded: [{event_type}] {title} (impact={impact_score})")
        return dict(row)

    async def get_recent(self, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT * FROM life_history ORDER BY created_at DESC LIMIT $1", limit
        )
        return [dict(r) for r in rows]

    async def get_impactful(self, min_impact: int = 7, limit: int = 5) -> list[dict]:
        """人格形成に大きく影響した経験"""
        rows = await self.db.fetch(
            "SELECT * FROM life_history WHERE impact_score >= $1 ORDER BY impact_score DESC LIMIT $2",
            min_impact, limit,
        )
        return [dict(r) for r in rows]

    async def to_prompt(self) -> str:
        events = await self.get_impactful(6, 5)
        if not events:
            return ""
        lines = ["【重要な経験】"]
        for e in events:
            lines.append(f"- [{e['event_type']}] {e['title']} (影響度: {e['impact_score']})")
            if e.get("lessons_learned"):
                lines.append(f"  → 教訓: {e['lessons_learned'][:100]}")
        return "\n".join(lines)
