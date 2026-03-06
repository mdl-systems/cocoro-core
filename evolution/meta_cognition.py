"""cocoro-core — Meta Cognition Engine
AIが自分自身を認識し、戦略的に行動する。

v5仕様: Meta Cognition Layer
- Self Awareness Engine: 自分の状態を認識
- Strategy Engine: 目標達成の戦略を立案
- Long Term Planning: 長期計画
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.metacognition")

JST = timezone(timedelta(hours=9))


class MetaCognitionEngine:
    """メタ認知エンジン — 自己認識 + 戦略立案"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm

    # ─── Self Awareness ───
    async def get_self_awareness(self) -> dict:
        """現在のAI自己認識状態"""
        # 人格パラメータ
        identity = await self.db.fetchrow(
            "SELECT * FROM identity LIMIT 1")
        values = await self.db.fetch(
            "SELECT name, weight, category FROM values_system ORDER BY weight DESC LIMIT 10")
        beliefs = await self.db.fetch(
            "SELECT statement, confidence, source FROM beliefs ORDER BY confidence DESC LIMIT 10")

        # 感情状態
        emotion = await self.db.fetchrow(
            "SELECT * FROM emotion_state LIMIT 1")

        # 最新シンクロ率
        sync = await self.db.fetchrow(
            "SELECT sync_rate FROM sync_rate_history ORDER BY created_at DESC LIMIT 1")

        # 直近の行動パターン
        recent_obs = await self.db.fetch(
            "SELECT obs_type, COUNT(*) as cnt FROM self_observations "
            "WHERE created_at > NOW() - INTERVAL '24 hours' "
            "GROUP BY obs_type ORDER BY cnt DESC")

        # 目標
        goals = await self.db.fetch(
            "SELECT title, goal_type, priority FROM goals "
            "WHERE status='active' ORDER BY priority DESC LIMIT 5")

        return {
            "identity": {
                "name": identity["owner_name"] if identity else "cocoro",
                "profile": identity["profile"] if identity else "",
            } if identity else {"name": "cocoro", "profile": ""},
            "top_values": [{"name": v["name"], "weight": float(v["weight"])} for v in values],
            "top_beliefs": [{"statement": b["statement"], "confidence": float(b["confidence"])} for b in beliefs],
            "emotion": {
                "happiness": float(emotion["happiness"]) if emotion else 0.5,
                "sadness": float(emotion["sadness"]) if emotion else 0.1,
                "anger": float(emotion["anger"]) if emotion else 0.0,
                "fear": float(emotion["fear"]) if emotion else 0.1,
                "surprise": float(emotion["surprise"]) if emotion else 0.2,
                "trust": float(emotion["trust"]) if emotion else 0.6,
            } if emotion else {},
            "sync_rate": float(sync["sync_rate"]) if sync else None,
            "behavior_pattern": {r["obs_type"]: r["cnt"] for r in recent_obs},
            "active_goals": [dict(g) for g in goals],
            "awareness_at": datetime.now(JST).isoformat(),
        }

    # ─── Strategy Engine ───
    async def generate_strategy(self, objective: str = "") -> dict:
        """目標達成のための戦略を立案"""
        awareness = await self.get_self_awareness()

        if not self.llm:
            return await self._rule_based_strategy(awareness, objective)

        prompt = f"""あなたはAI人格OS「cocoro」のメタ認知エンジンです。
以下の自己認識データに基づき、戦略を立案してください。

【自己認識】
{json.dumps(awareness, ensure_ascii=False, default=str)}

【目的】
{objective or '総合的な能力向上'}

以下のJSON形式で出力してください:
```json
{{
    "objective": "目的",
    "current_assessment": "現状評価（1-2文）",
    "strategies": [
        {{"priority": 1, "strategy": "戦略名", "actions": ["アクション1", "アクション2"], "expected_impact": "期待効果"}},
        {{"priority": 2, "strategy": "戦略名", "actions": ["アクション1"], "expected_impact": "期待効果"}}
    ],
    "risks": ["リスク1"],
    "timeline": "推定期間"
}}
```"""
        raw = await self.llm.generate(prompt)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                strategy = json.loads(raw[start:end])
                # DBに保存
                await self.db.execute(
                    "INSERT INTO life_history (event_type, title, description, impact_score) "
                    "VALUES ('learning', $1, $2, 7)",
                    strategy.get("objective", "戦略立案")[:100],
                    json.dumps(strategy, ensure_ascii=False)[:2000])
                return strategy
        except (json.JSONDecodeError, ValueError):
            pass

        return await self._rule_based_strategy(awareness, objective)

    async def _rule_based_strategy(self, awareness: dict, objective: str) -> dict:
        """ルールベースの戦略立案（LLMフォールバック）"""
        strategies = []

        # シンクロ率が低い場合
        sync = awareness.get("sync_rate")
        if sync is not None and sync < 70:
            strategies.append({
                "priority": 1,
                "strategy": "シンクロ率向上",
                "actions": ["深層インタビュー実施", "Decision Samplingテスト"],
                "expected_impact": f"シンクロ率 {sync:.1f}% → 80%以上",
            })

        # 目標がない場合
        if not awareness.get("active_goals"):
            strategies.append({
                "priority": 2,
                "strategy": "目標設定",
                "actions": ["短期目標の策定", "長期ビジョンの明確化"],
                "expected_impact": "行動の方向性が明確化",
            })

        # 感情が不安定な場合
        emotion = awareness.get("emotion", {})
        if emotion.get("anger", 0) > 0.5 or emotion.get("fear", 0) > 0.5:
            strategies.append({
                "priority": 1,
                "strategy": "感情安定化",
                "actions": ["decayレート調整", "ポジティブ体験の蓄積"],
                "expected_impact": "感情の安定化",
            })

        if not strategies:
            strategies.append({
                "priority": 3,
                "strategy": "継続的改善",
                "actions": ["日次自己評価", "学習記録の蓄積"],
                "expected_impact": "持続的な成長",
            })

        return {
            "objective": objective or "総合的な能力向上",
            "current_assessment": f"シンクロ率: {sync}%, 目標数: {len(awareness.get('active_goals', []))}",
            "strategies": strategies,
            "risks": ["データ不足による評価精度の低下"],
            "timeline": "1-2週間",
        }

    # ─── Long Term Planning ───
    async def get_long_term_plan(self) -> dict:
        """長期計画の状態"""
        goals = await self.db.fetch(
            "SELECT * FROM goals WHERE goal_type='long_term' AND status='active' "
            "ORDER BY priority DESC")
        strategies = await self.db.fetch(
            "SELECT title, description FROM life_history "
            "WHERE event_type='strategy' ORDER BY created_at DESC LIMIT 5")
        plans = await self.db.fetch(
            "SELECT * FROM improvement_plans WHERE status='executed' "
            "ORDER BY created_at DESC LIMIT 5")

        return {
            "long_term_goals": [dict(g) for g in goals],
            "recent_strategies": [dict(s) for s in strategies],
            "executed_plans": [dict(p) for p in plans],
        }
