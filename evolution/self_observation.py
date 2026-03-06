"""cocoro-core — Self Observation Engine
AIが自分自身の行動を観察・記録する。

v5仕様: Self Observation Engine
記録対象: 会話, 判断, 成功, 失敗, タスク結果, 感情変化
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.observation")

JST = timezone(timedelta(hours=9))

# 観測カテゴリ
OBSERVATION_TYPES = [
    "conversation",    # 会話
    "decision",        # 判断
    "task_success",    # タスク成功
    "task_failure",    # タスク失敗
    "emotion_change",  # 感情変化
    "learning",        # 学習
    "value_change",    # 価値観変化
    "error",           # エラー
]


class SelfObservationEngine:
    """自己観察エンジン — AIの行動を記録・集計"""

    def __init__(self, db):
        self.db = db

    async def observe(self, obs_type: str, summary: str,
                      detail: dict | None = None, impact: int = 5) -> dict:
        """行動を観察・記録"""
        if obs_type not in OBSERVATION_TYPES:
            obs_type = "conversation"

        row = await self.db.fetchrow(
            "INSERT INTO self_observations "
            "(obs_type, summary, detail, impact_score) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            obs_type, summary, json.dumps(detail or {}), impact)

        logger.debug(f"Observed [{obs_type}]: {summary[:60]}")
        return dict(row)

    async def observe_conversation(self, session_id: str, user_msg: str,
                                    ai_response: str, emotion: str = "neutral") -> dict:
        """会話を観察"""
        return await self.observe("conversation", f"Session {session_id[:8]}: {user_msg[:80]}", {
            "session_id": session_id,
            "user_message": user_msg[:500],
            "ai_response": ai_response[:500],
            "emotion": emotion,
        }, impact=3)

    async def observe_decision(self, context: str, decision: str,
                                confidence: float = 0.5) -> dict:
        """判断を観察"""
        return await self.observe("decision", f"Decision: {decision[:80]}", {
            "context": context[:500],
            "decision": decision[:500],
            "confidence": confidence,
        }, impact=6)

    async def observe_task(self, task_id: str, agent: str,
                           success: bool, duration_ms: int = 0) -> dict:
        """タスク結果を観察"""
        obs_type = "task_success" if success else "task_failure"
        return await self.observe(obs_type, f"Task {task_id[:8]} by {agent}: {'✅' if success else '❌'}", {
            "task_id": task_id,
            "agent": agent,
            "success": success,
            "duration_ms": duration_ms,
        }, impact=7 if not success else 4)

    async def observe_emotion_change(self, before: dict, after: dict,
                                      trigger: str = "") -> dict:
        """感情変化を観察"""
        return await self.observe("emotion_change", f"Emotion shift: {trigger[:60]}", {
            "before": before,
            "after": after,
            "trigger": trigger,
        }, impact=3)

    async def observe_value_change(self, name: str, old_weight: float,
                                    new_weight: float) -> dict:
        """価値観変化を観察"""
        delta = new_weight - old_weight
        return await self.observe("value_change",
            f"Value '{name}': {old_weight:.3f} → {new_weight:.3f} (Δ{delta:+.3f})", {
            "value_name": name,
            "old_weight": old_weight,
            "new_weight": new_weight,
            "delta": delta,
        }, impact=8)

    async def get_recent(self, limit: int = 50) -> list[dict]:
        """直近の観察データ"""
        rows = await self.db.fetch(
            "SELECT * FROM self_observations ORDER BY created_at DESC LIMIT $1",
            limit)
        return [dict(r) for r in rows]

    async def get_by_type(self, obs_type: str, limit: int = 20) -> list[dict]:
        """カテゴリ別の観察データ"""
        rows = await self.db.fetch(
            "SELECT * FROM self_observations WHERE obs_type=$1 "
            "ORDER BY created_at DESC LIMIT $2",
            obs_type, limit)
        return [dict(r) for r in rows]

    async def get_stats(self, hours: int = 24) -> dict:
        """集計統計"""
        rows = await self.db.fetch(
            "SELECT obs_type, COUNT(*) as count, "
            "AVG(impact_score) as avg_impact "
            "FROM self_observations "
            "WHERE created_at > NOW() - INTERVAL '1 hour' * $1 "
            "GROUP BY obs_type ORDER BY count DESC",
            hours)

        stats = {r["obs_type"]: {"count": r["count"], "avg_impact": round(float(r["avg_impact"]), 2)}
                 for r in rows}

        total = await self.db.fetchrow(
            "SELECT COUNT(*) as total FROM self_observations "
            "WHERE created_at > NOW() - INTERVAL '1 hour' * $1", hours)

        success = stats.get("task_success", {}).get("count", 0)
        failure = stats.get("task_failure", {}).get("count", 0)
        task_total = success + failure

        return {
            "period_hours": hours,
            "total_observations": total["total"] if total else 0,
            "by_type": stats,
            "task_success_rate": round(success / task_total * 100, 1) if task_total > 0 else None,
        }
