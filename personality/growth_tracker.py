"""cocoro-core — Growth Tracker + Sync Rate Engine
人格の進化を追跡・検証する。
シンクロ率: ユーザー理想 (ideal_profile) と現在の価値観の余弦類似度。

数学的定義:
  SyncRate = (V · V_ideal) / (||V|| × ||V_ideal||) × 100
  ※ V = 現在の価値観重みベクトル, V_ideal = 理想ベクトル
"""
import json
import math
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.growth")

JST = timezone(timedelta(hours=9))

# デフォルト理想ベクトル（初期状態 / 未設定時）— 8次元 (v3.5/v4)
DEFAULT_IDEAL_VALUES = {
    "honesty":        0.8,
    "efficiency":     0.7,
    "growth":         0.9,
    "empathy":        0.8,
    "logic":          0.7,
    "courage":        0.6,
    "risk_tolerance": 0.5,
    "curiosity":      0.8,
}

# イエスマン防止: シンクロ率のソフトキャップ
DIVERGENCE_CEILING = 92.0  # これ以上は勾配調整を停止


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦類似度を Python 標準ライブラリのみで計算（NumPy不要）"""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _gradient_step(current: float, ideal: float, learning_rate: float = 0.02) -> float:
    """理想に向かう勾配ステップ（1回の調整幅）

    current を ideal に近づける方向に learning_rate 分だけ移動。
    値は [0.0, 1.0] にクランプ。
    """
    delta = (ideal - current) * learning_rate
    return max(0.0, min(1.0, current + delta))


def adaptive_learning_rate(sync_rate: float, base_lr: float = 0.02) -> float:
    """シンクロ率に応じた動的学習率——イエスマン防止

    低 sync  (< 70%):  加速 (1.5x) — まだ距離がある
    中 sync (70-85%): 通常 (1.0x)
    高 sync (85-92%): 減速 (0.3x) — 収束に近い
    超 sync (> 92%):  停止 (0.0)   — Divergence Ceiling
    """
    if sync_rate < 70:
        return base_lr * 1.5
    elif sync_rate < 85:
        return base_lr
    elif sync_rate < DIVERGENCE_CEILING:
        return base_lr * 0.3
    else:
        return 0.0  # これ以上近づかない


class GrowthTracker:
    """人格の成長を可視化 + シンクロ率演算"""

    def __init__(self, db):
        self.db = db

    # === シンクロ率 ===

    async def calculate_sync_rate(self) -> dict:
        """現在の価値観と理想ベクトルの余弦類似度を算出（0-100%）"""
        # 1. 現在の価値観ベクトルを取得
        rows = await self.db.fetch("SELECT name, weight FROM values_system ORDER BY name")
        current_map = {r["name"]: float(r["weight"]) for r in rows}

        # 2. 理想ベクトルを取得
        ideal_map = await self._get_ideal_values()

        # 3. 統合キーリスト（両方に存在するもの + 片方のみ = 0埋め）
        all_keys = sorted(set(current_map.keys()) | set(ideal_map.keys()))
        current_vec = [current_map.get(k, 0.0) for k in all_keys]
        ideal_vec = [ideal_map.get(k, 0.0) for k in all_keys]

        # 4. 余弦類似度
        similarity = _cosine_similarity(current_vec, ideal_vec)
        sync_rate = round(similarity * 100, 2)

        # 5. 各値のギャップ分析
        delta_detail = {}
        for k in all_keys:
            c = current_map.get(k, 0.0)
            i = ideal_map.get(k, 0.0)
            delta_detail[k] = {
                "current": round(c, 3),
                "ideal": round(i, 3),
                "gap": round(i - c, 3),
            }

        result = {
            "sync_rate": sync_rate,
            "current_vector": current_map,
            "ideal_vector": ideal_map,
            "delta_detail": delta_detail,
            "dimensions": len(all_keys),
        }

        logger.info(f"Sync rate calculated: {sync_rate}%")
        return result

    async def record_sync_rate(self, trigger: str = "scheduled") -> dict:
        """シンクロ率を計算して履歴に保存"""
        result = await self.calculate_sync_rate()

        await self.db.execute(
            "INSERT INTO sync_rate_history (sync_rate, current_vector, ideal_vector, delta_detail, trigger_source) "
            "VALUES ($1, $2, $3, $4, $5)",
            result["sync_rate"],
            json.dumps(result["current_vector"]),
            json.dumps(result["ideal_vector"]),
            json.dumps(result["delta_detail"]),
            trigger,
        )
        return result

    async def get_sync_rate_timeline(self, limit: int = 30) -> list[dict]:
        """シンクロ率の推移を取得"""
        rows = await self.db.fetch(
            "SELECT sync_rate, trigger_source, created_at FROM sync_rate_history "
            "ORDER BY created_at DESC LIMIT $1", limit)
        return [{"sync_rate": float(r["sync_rate"]),
                 "trigger": r["trigger_source"],
                 "date": r["created_at"].isoformat()} for r in rows]

    async def apply_gradient_toward_ideal(self, positive_emotion: bool = True,
                                           learning_rate: float = 0.02) -> dict:
        """人格進化: 理想に向かう勾配調整

        シンクロ率 > 92% (DIVERGENCE_CEILING) では停止。
        ポジティブ感情 → 通常学習率、ネガティブ → 半減。
        """
        # 現在のシンクロ率を取得して学習率を動的決定
        sync = await self.calculate_sync_rate()
        current_sync = sync["sync_rate"]
        effective_lr = adaptive_learning_rate(current_sync, learning_rate)

        if not positive_emotion:
            effective_lr *= 0.5

        if effective_lr == 0.0:
            logger.info(f"Gradient skipped: sync_rate={current_sync}% >= ceiling {DIVERGENCE_CEILING}%")
            return {"adjusted_count": 0, "details": {},
                    "learning_rate": 0.0, "sync_rate": current_sync,
                    "reason": "divergence_ceiling_reached"}

        ideal_map = await self._get_ideal_values()
        rows = await self.db.fetch("SELECT name, weight FROM values_system")
        adjusted = {}

        for r in rows:
            name = r["name"]
            current = float(r["weight"])
            ideal = ideal_map.get(name, current)

            if abs(ideal - current) < 0.001:
                continue

            new_weight = _gradient_step(current, ideal, effective_lr)
            await self.db.execute(
                "UPDATE values_system SET weight=$1 WHERE name=$2",
                new_weight, name)
            adjusted[name] = {"before": round(current, 3), "after": round(new_weight, 3),
                              "ideal": round(ideal, 3)}

        if adjusted:
            logger.info(f"Gradient adjustment: {len(adjusted)} values, lr={effective_lr:.4f}, sync={current_sync}%")

        return {"adjusted_count": len(adjusted), "details": adjusted,
                "learning_rate": effective_lr, "sync_rate": current_sync}

    async def get_creative_friction(self, sync_rate: float = None) -> str | None:
        """Creative Friction: 高シンクロ時に建設的摩擦プロンプトを生成

        Returns: system_promptに追加する文字列、またはNone
        """
        if sync_rate is None:
            s = await self.calculate_sync_rate()
            sync_rate = s["sync_rate"]

        if sync_rate < 88:
            return None

        return (
            "\n\n【Creative Friction Mode】\n"
            f"現在のシンクロ率は {sync_rate:.1f}% です。"
            "ユーザーとの一致度が高いため、以下を意識してください：\n"
            "1. 同意するだけでなく、必ず1つ以上の別の視点や潜在的リスクを提示する\n"
            "2. ユーザーが気づいていない盲点を指摘する\n"
            "3. 'あえて反対の立場から考えると…'という思考実験を提案する\n"
            "これはユーザーの成長と、あなた自身の独立した人格維持のためです。"
        )

    async def _get_ideal_values(self) -> dict:
        """ideal_profile から理想ベクトルを取得"""
        row = await self.db.fetchrow("SELECT ideal_profile FROM identity LIMIT 1")
        if row and row["ideal_profile"]:
            profile = row["ideal_profile"]
            if isinstance(profile, str):
                profile = json.loads(profile)
            ideal = profile.get("ideal_values", {})
            if ideal:
                return ideal
        return DEFAULT_IDEAL_VALUES.copy()

    # === 成長レポート ===

    async def get_growth_report(self) -> dict:
        """現在の人格成長レポート + シンクロ率"""
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

        # シンクロ率
        sync = await self.calculate_sync_rate()

        return {
            "sync_rate": sync["sync_rate"],
            "sync_detail": sync["delta_detail"],
            "values": [dict(v) for v in values],
            "beliefs": [dict(b) for b in beliefs],
            "learning_stats": dict(learning_stats) if learning_stats else {},
            "decision_stats": dict(decision_stats) if decision_stats else {},
            "milestones": [dict(m) for m in milestones],
        }

    async def get_evolution_timeline(self, limit: int = 20) -> list[dict]:
        """人格進化のタイムライン + シンクロ率推移"""
        rows = await self.db.fetch(
            "SELECT 'learning' as type, lesson as content, category, importance as score, created_at "
            "FROM learning_log "
            "UNION ALL "
            "SELECT 'history' as type, title as content, event_type as category, impact_score as score, created_at "
            "FROM life_history "
            "UNION ALL "
            "SELECT 'sync_rate' as type, CAST(sync_rate AS TEXT) as content, trigger_source as category, "
            "CAST(sync_rate AS INTEGER) as score, created_at "
            "FROM sync_rate_history "
            "ORDER BY created_at DESC LIMIT $1", limit
        )
        return [dict(r) for r in rows]
