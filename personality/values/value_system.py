"""cocoro-core — Value System
価値観 = 判断基準の重み付けシステム。
すべての意思決定はこのValue Systemを通過する。
"""
import logging

logger = logging.getLogger("cocoro.values")


class ValueSystem:
    """価値観管理 — 判断のフィルタ"""

    def __init__(self, db):
        self.db = db
        self._cache: list[dict] = []

    async def load(self) -> list[dict]:
        """全価値観をロード"""
        rows = await self.db.fetch("SELECT * FROM values_system ORDER BY weight DESC")
        self._cache = [dict(r) for r in rows]
        return self._cache

    async def get_all(self) -> list[dict]:
        if not self._cache:
            await self.load()
        return self._cache

    async def get_by_category(self, category: str) -> list[dict]:
        values = await self.get_all()
        return [v for v in values if v["category"] == category]

    async def add(self, name: str, description: str, weight: float = 0.5, category: str = "general") -> dict:
        row = await self.db.fetchrow(
            "INSERT INTO values_system (name, description, weight, category) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (name) DO UPDATE SET description=$2, weight=$3, category=$4 RETURNING *",
            name, description, weight, category,
        )
        self._cache = []
        logger.info(f"Value added/updated: {name} (weight={weight})")
        return dict(row)

    async def adjust_weight(self, name: str, delta: float) -> dict | None:
        """経験に基づいて価値観の重みを調整する (学習)"""
        row = await self.db.fetchrow(
            "UPDATE values_system SET weight = LEAST(1.0, GREATEST(0.0, weight + $1)) "
            "WHERE name=$2 RETURNING *", delta, name,
        )
        if row:
            self._cache = []
            logger.info(f"Value weight adjusted: {name} += {delta:.2f} → {row['weight']:.2f}")
            return dict(row)
        return None

    async def to_prompt(self) -> str:
        """価値観を判断プロンプトに変換"""
        values = await self.get_all()
        if not values:
            return "【価値観】未設定"
        lines = ["【価値観・判断基準】"]
        for v in values[:8]:
            bar = "█" * int(v["weight"] * 10)
            lines.append(f"- {v['name']}: {v['description']} [{bar}] ({v['weight']:.1f})")
        return "\n".join(lines)

    async def apply_to_decision(self, question: str) -> str:
        """質問に関連する価値観を判断コンテキストとして出力"""
        values = await self.get_all()
        high = [v for v in values if v["weight"] >= 0.6]
        context = "この判断では以下の価値観を考慮してください:\n"
        for v in high:
            context += f"- {v['name']} ({v['weight']:.1f}): {v['description']}\n"
        return context
