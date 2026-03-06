"""cocoro-core — Cognitive Profile Engine
decision_logやconversation_logから認知スタイル・リスクプロファイルを算出。

v2仕様: 人格8要素のうち
- Cognitive Style (データ駆動 vs 直感)
- Risk Profile (リスク選好度)
が未実装だった。これらをdecision_logデータから自動推定する。
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.cognitive")

JST = timezone(timedelta(hours=9))


class CognitiveProfileEngine:
    """認知プロファイル — Cognitive Style + Risk Profile"""

    def __init__(self, db):
        self.db = db

    async def analyze(self) -> dict:
        """全認知プロファイルを分析"""
        cognitive_style = await self._analyze_cognitive_style()
        risk_profile = await self._analyze_risk_profile()
        decision_patterns = await self._analyze_decision_patterns()

        return {
            "cognitive_style": cognitive_style,
            "risk_profile": risk_profile,
            "decision_patterns": decision_patterns,
            "analyzed_at": datetime.now(JST).isoformat(),
        }

    async def _analyze_cognitive_style(self) -> dict:
        """認知スタイルを判定 (データ駆動 vs 直感 vs バランス)"""
        # decision_logのカテゴリ分布
        categories = await self.db.fetch(
            "SELECT category, COUNT(*) as cnt FROM decision_log "
            "GROUP BY category ORDER BY cnt DESC")

        # 思考記録からの分析
        thoughts = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM reasoning_log")

        # 値の計算
        total_decisions = sum(r["cnt"] for r in categories) if categories else 0
        total_thoughts = thoughts["cnt"] if thoughts else 0

        # 分析的（思考多い）vs 直感的（決断多い、思考少ない）
        if total_decisions + total_thoughts == 0:
            return {
                "style": "balanced",
                "analytical_ratio": 0.5,
                "intuitive_ratio": 0.5,
                "data_points": 0,
                "detail": "データ不足のため初期値",
            }

        # 思考/決断比率
        analytical_ratio = total_thoughts / (total_decisions + total_thoughts) if (total_decisions + total_thoughts) > 0 else 0.5

        if analytical_ratio > 0.6:
            style = "analytical"  # データ駆動型
        elif analytical_ratio < 0.3:
            style = "intuitive"  # 直感型
        else:
            style = "balanced"  # バランス型

        return {
            "style": style,
            "analytical_ratio": round(analytical_ratio, 3),
            "intuitive_ratio": round(1 - analytical_ratio, 3),
            "total_decisions": total_decisions,
            "total_thoughts": total_thoughts,
            "categories": {r["category"]: r["cnt"] for r in categories},
        }

    async def _analyze_risk_profile(self) -> dict:
        """リスクプロファイルを判定"""
        # decision_logのconfidence分布
        stats = await self.db.fetchrow(
            "SELECT AVG(confidence) as avg_conf, "
            "STDDEV(confidence) as std_conf, "
            "COUNT(*) as cnt "
            "FROM decision_log "
            "WHERE confidence IS NOT NULL")

        # values_systemのrisk_tolerance
        risk_value = await self.db.fetchrow(
            "SELECT weight FROM values_system WHERE name='risk_tolerance'")

        avg_conf = float(stats["avg_conf"]) if stats and stats["avg_conf"] else 0.5
        std_conf = float(stats["std_conf"]) if stats and stats["std_conf"] else 0.0
        data_points = stats["cnt"] if stats else 0
        risk_weight = float(risk_value["weight"]) if risk_value else 0.5

        # リスク選好度: 高confidence＝リスク許容、低confidence＝リスク回避
        if data_points < 3:
            risk_score = risk_weight  # データ不足時はvaluesの値を使用
            source = "values_system"
        else:
            # confidence平均が高い＝自信を持って決断＝リスク選好
            risk_score = avg_conf
            source = "decision_log"

        if risk_score > 0.7:
            profile = "risk_seeker"
        elif risk_score > 0.4:
            profile = "risk_neutral"
        else:
            profile = "risk_averse"

        return {
            "profile": profile,
            "risk_score": round(risk_score, 3),
            "avg_confidence": round(avg_conf, 3),
            "confidence_stddev": round(std_conf, 3),
            "risk_tolerance_value": round(risk_weight, 3),
            "data_points": data_points,
            "source": source,
        }

    async def _analyze_decision_patterns(self) -> dict:
        """意思決定パターンを分析"""
        # 直近の決断の時間帯分布
        hourly = await self.db.fetch(
            "SELECT EXTRACT(HOUR FROM created_at) as hour, COUNT(*) as cnt "
            "FROM decision_log "
            "WHERE created_at > NOW() - INTERVAL '30 days' "
            "GROUP BY hour ORDER BY cnt DESC LIMIT 5")

        # カテゴリごとのconfidence
        cat_conf = await self.db.fetch(
            "SELECT category, AVG(confidence) as avg_conf, COUNT(*) as cnt "
            "FROM decision_log "
            "GROUP BY category HAVING COUNT(*) >= 2 "
            "ORDER BY avg_conf DESC")

        return {
            "peak_hours": [{"hour": int(r["hour"]), "count": r["cnt"]} for r in hourly],
            "category_confidence": [
                {"category": r["category"],
                 "avg_confidence": round(float(r["avg_conf"]), 3),
                 "count": r["cnt"]} for r in cat_conf],
        }
