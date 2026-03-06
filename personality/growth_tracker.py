"""cocoro-core — Growth Tracker
人格の進化を追跡・検証する。
GPTレビュー: 「自動進化設計がStep3の核心」
"""
import logging

logger = logging.getLogger("cocoro.growth")


class GrowthTracker:
    """人格の成長を可視化"""

    def __init__(self, db):
        self.db = db

    async def get_growth_report(self) -> dict:
        """現在の人格成長レポート"""
        # 価値観の変化
        values = await self.db.fetch("SELECT name, weight, updated_at FROM values_system ORDER BY weight DESC")

        # 信念の確信度分布
        beliefs = await self.db.fetch(
            "SELECT statement, confidence, evidence_count, updated_at FROM beliefs ORDER BY confidence DESC"
        )

        # 学習の累積
        learning_stats = await self.db.fetchrow(
            "SELECT COUNT(*) as total, "
            "COUNT(CASE WHEN category='general' THEN 1 END) as general, "
            "COUNT(CASE WHEN category='business' THEN 1 END) as business, "
            "COUNT(CASE WHEN category='technical' THEN 1 END) as technical "
            "FROM learning_log"
        )

        # 判断の成功率
        decision_stats = await self.db.fetchrow(
            "SELECT COUNT(*) as total, "
            "COUNT(CASE WHEN outcome='success' THEN 1 END) as success, "
            "COUNT(CASE WHEN outcome='failure' THEN 1 END) as failure "
            "FROM decision_log WHERE outcome IS NOT NULL"
        )

        # 重要経験
        milestones = await self.db.fetch(
            "SELECT title, impact_score, created_at FROM life_history "
            "WHERE impact_score >= 7 ORDER BY created_at DESC LIMIT 10"
        )

        return {
            "values": [dict(v) for v in values],
            "beliefs": [dict(b) for b in beliefs],
            "learning_stats": dict(learning_stats) if learning_stats else {},
            "decision_stats": dict(decision_stats) if decision_stats else {},
            "milestones": [dict(m) for m in milestones],
        }

    async def get_evolution_timeline(self, limit: int = 20) -> list[dict]:
        """人格進化のタイムライン"""
        rows = await self.db.fetch(
            "SELECT 'learning' as type, lesson as content, category, importance as score, created_at "
            "FROM learning_log "
            "UNION ALL "
            "SELECT 'history' as type, title as content, event_type as category, impact_score as score, created_at "
            "FROM life_history "
            "ORDER BY created_at DESC LIMIT $1", limit
        )
        return [dict(r) for r in rows]
