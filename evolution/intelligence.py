"""cocoro-core — Intelligence Expansion Layer
AIの知識・スキル・ツール使用能力を拡張する。

v5仕様: Intelligence Expansion Layer
- Knowledge Expansion: 知識の拡張・記録
- Skill Acquisition: スキル獲得・成長追跡
- Tool Learning: ツール利用の学習・最適化
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.intelligence")

JST = timezone(timedelta(hours=9))


class IntelligenceExpansionEngine:
    """知能拡張エンジン — 知識・スキル・ツール学習"""

    def __init__(self, db):
        self.db = db

    # ─── Knowledge Expansion ───
    async def add_knowledge(self, topic: str, content: str,
                             source: str = "conversation",
                             confidence: float = 0.7) -> dict:
        """知識を追加"""
        row = await self.db.fetchrow(
            "INSERT INTO knowledge_base "
            "(topic, content, source, confidence) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            topic, content, source, confidence)
        logger.info(f"Knowledge added: {topic[:40]} (confidence={confidence})")
        return dict(row)

    async def search_knowledge(self, query: str, limit: int = 10) -> list[dict]:
        """知識を検索"""
        rows = await self.db.fetch(
            "SELECT * FROM knowledge_base "
            "WHERE topic ILIKE $1 OR content ILIKE $1 "
            "ORDER BY confidence DESC, created_at DESC LIMIT $2",
            f"%{query}%", limit)
        return [dict(r) for r in rows]

    async def get_knowledge_stats(self) -> dict:
        """知識統計"""
        total = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM knowledge_base")
        by_source = await self.db.fetch(
            "SELECT source, COUNT(*) as cnt, AVG(confidence) as avg_conf "
            "FROM knowledge_base GROUP BY source ORDER BY cnt DESC")
        return {
            "total_knowledge": total["cnt"] if total else 0,
            "by_source": [{"source": r["source"], "count": r["cnt"],
                           "avg_confidence": round(float(r["avg_conf"]), 3)}
                          for r in by_source],
        }

    # ─── Skill Acquisition ───
    async def register_skill(self, name: str, category: str = "general",
                              proficiency: float = 0.1) -> dict:
        """スキルを登録"""
        row = await self.db.fetchrow(
            "INSERT INTO skills "
            "(name, category, proficiency) "
            "VALUES ($1, $2, $3) "
            "ON CONFLICT (name) DO UPDATE SET "
            "proficiency = GREATEST(skills.proficiency, $3), "
            "practice_count = skills.practice_count + 1 "
            "RETURNING *",
            name, category, proficiency)
        logger.info(f"Skill registered: {name} (proficiency={proficiency})")
        return dict(row)

    async def improve_skill(self, name: str, delta: float = 0.05) -> dict:
        """スキルを向上"""
        row = await self.db.fetchrow(
            "UPDATE skills SET "
            "proficiency = LEAST(1.0, proficiency + $1), "
            "practice_count = practice_count + 1 "
            "WHERE name=$2 RETURNING *",
            delta, name)
        if not row:
            return await self.register_skill(name, proficiency=delta)
        return dict(row)

    async def get_skills(self, category: str | None = None) -> list[dict]:
        """スキル一覧"""
        if category:
            rows = await self.db.fetch(
                "SELECT * FROM skills WHERE category=$1 "
                "ORDER BY proficiency DESC", category)
        else:
            rows = await self.db.fetch(
                "SELECT * FROM skills ORDER BY proficiency DESC")
        return [dict(r) for r in rows]

    # ─── Tool Learning ───
    async def record_tool_usage(self, tool_name: str, success: bool,
                                 duration_ms: int = 0,
                                 context: str = "") -> dict:
        """ツール使用を記録"""
        row = await self.db.fetchrow(
            "INSERT INTO tool_usage_log "
            "(tool_name, success, duration_ms, context) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            tool_name, success, duration_ms, context[:500])

        # スキルとしても記録
        await self.improve_skill(f"tool:{tool_name}",
                                  delta=0.03 if success else 0.01)
        return dict(row)

    async def get_tool_stats(self) -> dict:
        """ツール使用統計"""
        rows = await self.db.fetch(
            "SELECT tool_name, "
            "COUNT(*) as total, "
            "COUNT(*) FILTER (WHERE success) as successes, "
            "AVG(duration_ms) as avg_duration "
            "FROM tool_usage_log "
            "GROUP BY tool_name ORDER BY total DESC")

        tools = []
        for r in rows:
            total = r["total"]
            successes = r["successes"]
            tools.append({
                "tool_name": r["tool_name"],
                "total_uses": total,
                "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
                "avg_duration_ms": round(float(r["avg_duration"]), 1) if r["avg_duration"] else 0,
            })
        return {"tools": tools}

    async def get_intelligence_report(self) -> dict:
        """知能拡張レポート"""
        knowledge = await self.get_knowledge_stats()
        skills = await self.get_skills()
        tools = await self.get_tool_stats()

        # 総合スコア
        skill_avg = (sum(float(s["proficiency"]) for s in skills) / len(skills)
                     if skills else 0)

        return {
            "knowledge": knowledge,
            "skills_count": len(skills),
            "skill_avg_proficiency": round(skill_avg, 3),
            "top_skills": skills[:5],
            "tool_usage": tools,
            "intelligence_version": "1.0",
        }
