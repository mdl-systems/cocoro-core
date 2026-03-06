"""cocoro-core — Self Evaluation Engine
AIが自分のパフォーマンスを評価する。

v5仕様: Self Evaluation Engine
評価対象: タスク成功率, 判断の質, 感情安定度, 成長速度
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.evaluation")

JST = timezone(timedelta(hours=9))


class SelfEvaluationEngine:
    """自己評価エンジン — パフォーマンス分析"""

    def __init__(self, db):
        self.db = db

    async def evaluate(self, hours: int = 24) -> dict:
        """総合自己評価を実行"""
        task_eval = await self._evaluate_tasks(hours)
        emotion_eval = await self._evaluate_emotion_stability(hours)
        decision_eval = await self._evaluate_decisions(hours)
        growth_eval = await self._evaluate_growth()

        # 総合スコア（0-100）
        scores = []
        if task_eval["score"] is not None:
            scores.append(task_eval["score"])
        if emotion_eval["score"] is not None:
            scores.append(emotion_eval["score"])
        if decision_eval["score"] is not None:
            scores.append(decision_eval["score"])
        if growth_eval["score"] is not None:
            scores.append(growth_eval["score"])

        overall = round(sum(scores) / len(scores), 1) if scores else None

        # 改善が必要な領域を特定
        weak_areas = []
        if task_eval["score"] is not None and task_eval["score"] < 70:
            weak_areas.append({"area": "task_performance", "score": task_eval["score"],
                               "suggestion": "タスク失敗率が高い。原因分析と再試行戦略の強化が必要"})
        if emotion_eval["score"] is not None and emotion_eval["score"] < 60:
            weak_areas.append({"area": "emotion_stability", "score": emotion_eval["score"],
                               "suggestion": "感情の変動が大きい。decayレートの調整を検討"})
        if decision_eval["score"] is not None and decision_eval["score"] < 70:
            weak_areas.append({"area": "decision_quality", "score": decision_eval["score"],
                               "suggestion": "判断の信頼度が低い。データ収集と分析プロセスの改善が必要"})

        # 強みを特定
        strengths = []
        for eval_item in [task_eval, emotion_eval, decision_eval, growth_eval]:
            if eval_item["score"] is not None and eval_item["score"] >= 80:
                strengths.append(eval_item["area"])

        return {
            "overall_score": overall,
            "period_hours": hours,
            "evaluations": {
                "task_performance": task_eval,
                "emotion_stability": emotion_eval,
                "decision_quality": decision_eval,
                "growth": growth_eval,
            },
            "strengths": strengths,
            "weak_areas": weak_areas,
            "evaluated_at": datetime.now(JST).isoformat(),
        }

    async def _evaluate_tasks(self, hours: int) -> dict:
        """タスクパフォーマンス評価"""
        stats = await self.db.fetchrow(
            "SELECT "
            "  COUNT(*) FILTER (WHERE obs_type='task_success') as successes, "
            "  COUNT(*) FILTER (WHERE obs_type='task_failure') as failures "
            "FROM self_observations "
            "WHERE obs_type IN ('task_success', 'task_failure') "
            "AND created_at > NOW() - INTERVAL '1 hour' * $1",
            hours)

        successes = stats["successes"] if stats else 0
        failures = stats["failures"] if stats else 0
        total = successes + failures

        if total == 0:
            return {"area": "task_performance", "score": None,
                    "detail": "評価期間内にタスクデータなし"}

        rate = successes / total * 100
        return {
            "area": "task_performance",
            "score": round(rate, 1),
            "detail": f"成功率: {rate:.1f}% ({successes}/{total})",
            "successes": successes,
            "failures": failures,
        }

    async def _evaluate_emotion_stability(self, hours: int) -> dict:
        """感情安定度評価"""
        changes = await self.db.fetchrow(
            "SELECT COUNT(*) as change_count "
            "FROM self_observations "
            "WHERE obs_type='emotion_change' "
            "AND created_at > NOW() - INTERVAL '1 hour' * $1",
            hours)

        count = changes["change_count"] if changes else 0

        # 変化が少ないほど安定
        if count == 0:
            return {"area": "emotion_stability", "score": None,
                    "detail": "評価期間内に感情変化データなし"}

        # 24時間で10回以下が理想、50回以上は不安定
        stability = max(0, min(100, 100 - (count - 10) * 2.5))
        return {
            "area": "emotion_stability",
            "score": round(stability, 1),
            "detail": f"感情変化回数: {count}回/{hours}h",
            "change_count": count,
        }

    async def _evaluate_decisions(self, hours: int) -> dict:
        """判断品質評価"""
        decisions = await self.db.fetch(
            "SELECT detail FROM self_observations "
            "WHERE obs_type='decision' "
            "AND created_at > NOW() - INTERVAL '1 hour' * $1 "
            "LIMIT 50",
            hours)

        if not decisions:
            return {"area": "decision_quality", "score": None,
                    "detail": "評価期間内に判断データなし"}

        # 信頼度の平均
        import json
        confidences = []
        for d in decisions:
            try:
                detail = json.loads(d["detail"]) if isinstance(d["detail"], str) else d["detail"]
                if "confidence" in detail:
                    confidences.append(float(detail["confidence"]))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        if not confidences:
            return {"area": "decision_quality", "score": 70,
                    "detail": f"判断数: {len(decisions)}件 (信頼度データなし)"}

        avg_conf = sum(confidences) / len(confidences)
        score = avg_conf * 100

        return {
            "area": "decision_quality",
            "score": round(score, 1),
            "detail": f"平均信頼度: {avg_conf:.3f} ({len(confidences)}件)",
            "avg_confidence": round(avg_conf, 3),
            "total_decisions": len(decisions),
        }

    async def _evaluate_growth(self) -> dict:
        """成長度評価 — シンクロ率の変化から評価"""
        recent = await self.db.fetch(
            "SELECT sync_rate, created_at FROM sync_rate_history "
            "ORDER BY created_at DESC LIMIT 10")

        if len(recent) < 2:
            return {"area": "growth", "score": None,
                    "detail": "シンクロ率の履歴が不十分"}

        latest = float(recent[0]["sync_rate"])
        oldest = float(recent[-1]["sync_rate"])
        trend = latest - oldest

        # 成長傾向をスコア化（+5%以上 = 100, ±0 = 70, -5%以下 = 40）
        score = min(100, max(0, 70 + trend * 6))

        return {
            "area": "growth",
            "score": round(score, 1),
            "detail": f"シンクロ率推移: {oldest:.1f}% → {latest:.1f}% (Δ{trend:+.1f}%)",
            "current_sync_rate": latest,
            "trend": round(trend, 2),
        }
