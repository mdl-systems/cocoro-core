"""cocoro-core — Improvement Engine
自己評価結果に基づき、改善計画を生成・実行する。

v5仕様: Improvement Engine
入力: Self Evaluation の結果
出力: 改善アクション（価値観調整, 目標追加, 学習記録）
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.improvement")

JST = timezone(timedelta(hours=9))


class ImprovementEngine:
    """改善エンジン — 自己評価 → 改善計画 → 実行"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm

    async def generate_plan(self, evaluation: dict) -> dict:
        """自己評価結果から改善計画を生成"""
        weak_areas = evaluation.get("weak_areas", [])
        overall = evaluation.get("overall_score")

        plan = {
            "generated_at": datetime.now(JST).isoformat(),
            "overall_score": overall,
            "actions": [],
        }

        # 弱点ベースのアクション生成
        for weak in weak_areas:
            area = weak.get("area", "")
            score = weak.get("score", 0)

            if area == "task_performance":
                plan["actions"].append({
                    "type": "goal",
                    "action": "add_goal",
                    "title": "タスク成功率の向上",
                    "description": f"現在のスコア: {score}。失敗パターンの分析と再試行戦略を強化",
                    "goal_type": "short_term",
                    "priority": 8,
                })
            elif area == "emotion_stability":
                plan["actions"].append({
                    "type": "parameter",
                    "action": "adjust_decay",
                    "description": f"感情安定度スコア: {score}。decay率を上げて安定化",
                    "parameter": "emotion_decay_rate",
                    "suggestion": "decay率を0.15に設定",
                })
            elif area == "decision_quality":
                plan["actions"].append({
                    "type": "learning",
                    "action": "add_learning",
                    "description": f"判断品質スコア: {score}。データ収集プロセスを改善",
                    "lesson": "判断前に十分なコンテキストを収集する",
                    "impact": 7,
                })

        # LLMによる高度な改善提案
        if self.llm and overall is not None and overall < 80:
            try:
                llm_suggestions = await self._generate_llm_suggestions(evaluation)
                if llm_suggestions:
                    plan["actions"].extend(llm_suggestions)
            except Exception as e:
                logger.warning(f"LLM suggestion failed: {e}")

        # 改善計画をDBに保存
        row = await self.db.fetchrow(
            "INSERT INTO improvement_plans "
            "(evaluation_score, weak_areas, actions, status) "
            "VALUES ($1, $2, $3, 'pending') RETURNING *",
            overall or 0, json.dumps(weak_areas),
            json.dumps(plan["actions"]))

        plan["plan_id"] = str(row["id"])
        plan["status"] = "pending"
        logger.info(f"Improvement plan generated: {len(plan['actions'])} actions, "
                     f"score={overall}")
        return plan

    async def execute_plan(self, plan_id: str) -> dict:
        """改善計画を実行"""
        row = await self.db.fetchrow(
            "SELECT * FROM improvement_plans WHERE id=$1::uuid", plan_id)
        if not row:
            return {"error": "Plan not found"}

        actions = json.loads(row["actions"]) if isinstance(row["actions"], str) else row["actions"]
        results = []

        for action in actions:
            result = await self._execute_action(action)
            results.append(result)

        # ステータス更新
        await self.db.execute(
            "UPDATE improvement_plans SET status='executed', "
            "executed_at=NOW() WHERE id=$1::uuid", plan_id)

        executed = sum(1 for r in results if r.get("success"))
        logger.info(f"Plan {plan_id[:8]} executed: {executed}/{len(results)} actions")

        return {
            "plan_id": plan_id,
            "total_actions": len(results),
            "executed": executed,
            "results": results,
        }

    async def _execute_action(self, action: dict) -> dict:
        """個別アクションを実行"""
        action_type = action.get("type", "")
        result = {"action": action, "success": False}

        try:
            if action_type == "goal" and action.get("action") == "add_goal":
                await self.db.execute(
                    "INSERT INTO goals (title, description, goal_type, priority) "
                    "VALUES ($1, $2, $3, $4)",
                    action.get("title", "改善目標"),
                    action.get("description", ""),
                    action.get("goal_type", "short_term"),
                    action.get("priority", 5))
                result["success"] = True
                result["message"] = f"Goal added: {action.get('title', '')[:40]}"

            elif action_type == "learning" and action.get("action") == "add_learning":
                await self.db.execute(
                    "INSERT INTO life_history (event_type, title, description, impact_score) "
                    "VALUES ('learning', $1, $2, $3)",
                    action.get("lesson", "")[:100],
                    action.get("description", ""),
                    action.get("impact", 5))
                result["success"] = True
                result["message"] = f"Learning recorded: {action.get('lesson', '')[:40]}"

            elif action_type == "parameter":
                result["success"] = True
                result["message"] = f"Parameter suggestion: {action.get('suggestion', '')}"
                result["requires_manual"] = True

            elif action_type == "value_adjustment":
                name = action.get("value_name", "")
                delta = action.get("delta", 0)
                if name and abs(delta) <= 0.1:
                    await self.db.execute(
                        "UPDATE values_system SET weight = "
                        "GREATEST(0, LEAST(1, weight + $1)) WHERE name=$2",
                        float(delta), name)
                    result["success"] = True
                    result["message"] = f"Value '{name}' adjusted by {delta:+.3f}"

            else:
                result["message"] = f"Unknown action type: {action_type}"

        except Exception as e:
            result["message"] = f"Execution failed: {str(e)}"
            logger.error(f"Action execution failed: {e}")

        return result

    async def _generate_llm_suggestions(self, evaluation: dict) -> list[dict]:
        """LLMで高度な改善提案を生成"""
        eval_summary = json.dumps(evaluation, ensure_ascii=False, default=str)
        prompt = f"""以下はAI人格の自己評価結果です。改善アクションをJSON配列で提案してください。

{eval_summary}

以下の形式でJSON配列を出力:
```json
[
  {{"type": "value_adjustment", "value_name": "courage", "delta": 0.05, "reason": "理由"}},
  {{"type": "learning", "action": "add_learning", "lesson": "学びの内容", "description": "詳細", "impact": 7}}
]
```"""
        raw = await self.llm.generate(prompt)
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    async def get_plans(self, limit: int = 10) -> list[dict]:
        """改善計画一覧"""
        rows = await self.db.fetch(
            "SELECT * FROM improvement_plans ORDER BY created_at DESC LIMIT $1",
            limit)
        return [dict(r) for r in rows]

    async def get_plan(self, plan_id: str) -> dict | None:
        """改善計画詳細"""
        row = await self.db.fetchrow(
            "SELECT * FROM improvement_plans WHERE id=$1::uuid", plan_id)
        return dict(row) if row else None
