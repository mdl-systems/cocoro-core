"""cocoro-core — Goal Engine
人格の目標管理。短期/長期/人生目標を管理し、判断方針に反映する。

v1 GPTレビュー + v2 仕様で要求:
「人格にはGoalが必要。長期目標と短期目標がAgent task generationになる。」
"""
import logging

logger = logging.getLogger("cocoro.goals")


class GoalEngine:
    """目標管理 — 人格の方向性を定義"""

    def __init__(self, db):
        self.db = db

    async def get_all(self) -> list[dict]:
        """全目標を取得"""
        rows = await self.db.fetch(
            "SELECT * FROM goals ORDER BY priority DESC, created_at")
        return [dict(r) for r in rows]

    async def get_by_type(self, goal_type: str) -> list[dict]:
        """種別ごとに目標を取得"""
        rows = await self.db.fetch(
            "SELECT * FROM goals WHERE goal_type=$1 ORDER BY priority DESC",
            goal_type)
        return [dict(r) for r in rows]

    async def get_active(self) -> list[dict]:
        """アクティブな目標のみ取得"""
        rows = await self.db.fetch(
            "SELECT * FROM goals WHERE status='active' ORDER BY priority DESC")
        return [dict(r) for r in rows]

    async def add(self, title: str, description: str = "",
                  goal_type: str = "short_term",
                  priority: int = 5) -> dict:
        """新しい目標を追加"""
        row = await self.db.fetchrow(
            "INSERT INTO goals (title, description, goal_type, priority) "
            "VALUES ($1, $2, $3, $4) RETURNING *",
            title, description, goal_type, priority)
        logger.info(f"Goal added: [{goal_type}] {title} (priority={priority})")
        return dict(row)

    async def update_status(self, goal_id: str, status: str) -> dict | None:
        """目標のステータスを更新"""
        row = await self.db.fetchrow(
            "UPDATE goals SET status=$1 WHERE id=$2::uuid RETURNING *",
            status, goal_id)
        if row:
            logger.info(f"Goal status updated: {row['title'][:40]} → {status}")
            return dict(row)
        return None

    async def update(self, goal_id: str, **kwargs) -> dict | None:
        """目標を更新"""
        sets, params, i = [], [], 1
        for key in ("title", "description", "goal_type", "priority", "status"):
            if key in kwargs and kwargs[key] is not None:
                sets.append(f"{key}=${i}")
                params.append(kwargs[key])
                i += 1
        if not sets:
            return None
        params.append(goal_id)
        row = await self.db.fetchrow(
            f"UPDATE goals SET {','.join(sets)} WHERE id=${i}::uuid RETURNING *",
            *params)
        if row:
            logger.info(f"Goal updated: {row['title'][:40]}")
            return dict(row)
        return None

    async def delete(self, goal_id: str) -> bool:
        """目標を削除"""
        result = await self.db.execute(
            "DELETE FROM goals WHERE id=$1::uuid", goal_id)
        deleted = result == "DELETE 1"
        if deleted:
            logger.info(f"Goal deleted: {goal_id[:8]}")
        return deleted

    async def to_prompt(self) -> str:
        """目標をプロンプト文に変換"""
        goals = await self.get_active()
        if not goals:
            return ""

        lines = ["【目標・方針】"]
        type_labels = {
            "life_mission": "🌟 人生目標",
            "long_term": "📌 長期目標",
            "short_term": "📋 短期目標",
        }
        for goal_type in ("life_mission", "long_term", "short_term"):
            typed = [g for g in goals if g["goal_type"] == goal_type]
            if typed:
                lines.append(f"{type_labels.get(goal_type, goal_type)}:")
                for g in typed[:3]:
                    lines.append(f"  - {g['title']}")
        return "\n".join(lines)
