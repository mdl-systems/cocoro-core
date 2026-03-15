"""cocoro-core — Sync Rate Engine
4要素によるユーザー↔AI シンクロ率を計算・管理する拡張エンジン。

既存の GrowthTracker.calculate_sync_rate() を「価値観一致度（40%）」成分として活用し、
以下の4要素を合成した総合スコアを算出する：

  1. values_match   (40%): 価値観ベクトルの余弦類似度（GrowthTracker）
  2. empathy        (30%): 会話の共感度（肯定的応答 / 会話全体の比率）
  3. emotion_stab   (20%): 感情状態の安定度（entropy逆数）
  4. memory_usage   (10%): 記憶の活用度（直近会話でuser_memory hit率）

履歴は既存の sync_rate_history テーブルに trigger_source='chat' で追記。
"""
import json
import math
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("cocoro.sync")

# 重み
WEIGHTS = {
    "values_match":    0.40,
    "empathy":         0.30,
    "emotion_stab":    0.20,
    "memory_usage":    0.10,
}

# スコア別メッセージ
def _rate_message(rate: float, trend: str) -> str:
    if rate >= 90:
        return "シンクロ率が非常に高く、深い相互理解が形成されています"
    elif rate >= 80:
        return "価値観の一致度が高まっています" if trend == "up" else "高い一致度を維持しています"
    elif rate >= 70:
        return "着実に理解が深まっています" if trend == "up" else "良好な状態を維持しています"
    elif rate >= 60:
        return "コミュニケーションを続けることで理解が深まります"
    elif rate >= 50:
        return "会話量を増やすことでシンクロ率が向上します"
    else:
        return "様々な話題で会話することで関係が深まります"


class SyncRateEngine:
    """4要素シンクロ率計算エンジン"""

    def __init__(self, db_pool, growth_tracker=None):
        self.db = db_pool
        self.growth = growth_tracker  # GrowthTracker インスタンス（任意）

    async def compute_full_sync_rate(self, save: bool = True) -> dict:
        """4要素の総合シンクロ率を計算し、必要に応じて履歴保存。

        Returns:
            {
              "rate": float,
              "trend": "up"|"down"|"stable",
              "delta": float,
              "breakdown": {...},
              "message": str
            }
        """
        # --- 要素1: 価値観一致度 ---
        values_score = await self._calc_values_match()

        # --- 要素2: 共感度 ---
        empathy_score = await self._calc_empathy()

        # --- 要素3: 感情安定度 ---
        emotion_score = await self._calc_emotion_stability()

        # --- 要素4: 記憶活用度 ---
        memory_score = await self._calc_memory_usage()

        # 総合スコア（加重平均, 0〜100）
        total = (
            values_score  * WEIGHTS["values_match"] +
            empathy_score * WEIGHTS["empathy"] +
            emotion_score * WEIGHTS["emotion_stab"] +
            memory_score  * WEIGHTS["memory_usage"]
        )
        rate = round(total, 1)

        # --- トレンド計算 ---
        prev_rate, delta = await self._calc_trend(rate)
        if delta > 1.0:
            trend = "up"
        elif delta < -1.0:
            trend = "down"
        else:
            trend = "stable"

        breakdown = {
            "values_match":    round(values_score,  1),
            "empathy":         round(empathy_score, 1),
            "emotion_stability": round(emotion_score, 1),
            "memory_usage":    round(memory_score,  1),
        }

        result = {
            "rate":      rate,
            "sync_rate": rate,   # ダッシュボード互換エイリアス
            "trend":     trend,
            "delta":     round(delta, 1),
            "breakdown": breakdown,
            "message":   _rate_message(rate, trend),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        # --- 履歴保存 ---
        if save:
            await self._save_to_history(rate, breakdown)

        return result

    async def get_history(self, days: int = 30) -> list:
        """過去 n 日間のシンクロ率の推移を返す。"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            rows = await self.db.fetch(
                """SELECT sync_rate, trigger_source, delta_detail, created_at
                   FROM sync_rate_history
                   WHERE created_at >= $1
                   ORDER BY created_at ASC""",
                cutoff
            )
            history = []
            for r in rows:
                entry = {
                    "date":         r["created_at"].isoformat(),
                    "sync_rate":    round(float(r["sync_rate"]), 1),
                    "trigger":      r["trigger_source"],
                }
                # delta_detail に breakdown が含まれる場合は展開
                dd = r["delta_detail"]
                if isinstance(dd, str):
                    try:
                        dd = json.loads(dd)
                    except Exception:
                        dd = {}
                if isinstance(dd, dict) and "breakdown" in dd:
                    entry["breakdown"] = dd["breakdown"]
                history.append(entry)
            return history
        except Exception as e:
            logger.error(f"Failed to fetch sync history: {e}")
            return []

    # ------------------------------------------------------------------ #
    # 各要素の計算
    # ------------------------------------------------------------------ #

    async def _calc_values_match(self) -> float:
        """要素1: 価値観一致度（GrowthTracker の cosine similarity を利用）"""
        if self.growth is not None:
            try:
                result = await self.growth.calculate_sync_rate()
                return min(result.get("sync_rate", 50.0), 100.0)
            except Exception as e:
                logger.warning(f"values_match via growth failed: {e}")
        # フォールバック: DBから直接計算
        try:
            rows = await self.db.fetch(
                "SELECT name, weight FROM values_system ORDER BY name"
            )
            if not rows:
                return 50.0
            # 全て1.0に近いほど高スコア（平均値ベース）
            avg = sum(float(r["weight"]) for r in rows) / len(rows)
            return round(avg * 100, 1)
        except Exception:
            return 50.0

    async def _calc_empathy(self) -> float:
        """要素2: 共感度 — 直近50会話でのポジティブ応答の割合"""
        POSITIVE_KEYWORDS = [
            "ありがとう", "なるほど", "いいね", "素晴らしい", "助かり",
            "理解", "わかり", "そうですね", "確かに", "その通り",
        ]
        try:
            rows = await self.db.fetch(
                """SELECT content FROM conversation_log
                   WHERE role = 'assistant'
                   ORDER BY created_at DESC LIMIT 50"""
            )
            if not rows:
                return 50.0
            positive_count = 0
            for r in rows:
                content = str(r["content"])
                if any(kw in content for kw in POSITIVE_KEYWORDS):
                    positive_count += 1
            # 0〜100 にスケール (最低40%)
            ratio = positive_count / len(rows)
            return round(40.0 + ratio * 60.0, 1)
        except Exception as e:
            logger.warning(f"empathy calc failed: {e}")
            return 60.0

    async def _calc_emotion_stability(self) -> float:
        """要素3: 感情安定度 — 感情エントロピーが低いほど安定"""
        try:
            row = await self.db.fetchrow(
                """SELECT happiness, sadness, anger, fear, surprise, trust
                   FROM emotion_state LIMIT 1"""
            )
            if not row:
                return 60.0
            emotions = [
                float(row["happiness"]),
                float(row["sadness"]),
                float(row["anger"]),
                float(row["fear"]),
                float(row["surprise"]),
                float(row["trust"]),
            ]
            total = sum(emotions)
            if total == 0:
                return 60.0
            # Shannon entropy (最大値は log(6) ≈ 1.79)
            entropy = 0.0
            for v in emotions:
                p = v / total
                if p > 0:
                    entropy -= p * math.log(p)
            max_entropy = math.log(len(emotions))
            # 安定度 = 1 - (entropy / max_entropy)
            stability = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0)
            # happiness と trust が高いほどボーナス
            bonus = (float(row["happiness"]) + float(row["trust"])) * 10
            score = stability * 80 + min(bonus, 20)
            return round(min(score, 100.0), 1)
        except Exception as e:
            logger.warning(f"emotion_stability calc failed: {e}")
            return 60.0

    async def _calc_memory_usage(self) -> float:
        """要素4: 記憶活用度 — ユーザー記憶の保存数を活用度に変換"""
        try:
            row = await self.db.fetchrow(
                """SELECT COUNT(*) as cnt FROM knowledge_base
                   WHERE source = 'user_memory'
                     AND confidence >= 0.7"""
            )
            cnt = int(row["cnt"]) if row else 0
            # 10件以上で MAX スコア
            score = min(cnt / 10.0, 1.0) * 100.0
            return round(max(score, 30.0), 1)  # 最低30%
        except Exception as e:
            logger.warning(f"memory_usage calc failed: {e}")
            return 50.0

    async def _calc_trend(self, current_rate: float) -> tuple[float, float]:
        """直前の履歴と比較してトレンド・デルタを返す。"""
        try:
            row = await self.db.fetchrow(
                """SELECT sync_rate FROM sync_rate_history
                   ORDER BY created_at DESC LIMIT 1"""
            )
            if not row:
                return current_rate, 0.0
            prev = float(row["sync_rate"])
            return prev, current_rate - prev
        except Exception:
            return current_rate, 0.0

    async def _save_to_history(self, rate: float, breakdown: dict):
        """sync_rate_history に保存（breakdownはdelta_detailに格納）"""
        try:
            await self.db.execute(
                """INSERT INTO sync_rate_history
                   (sync_rate, current_vector, ideal_vector, delta_detail, trigger_source)
                   VALUES ($1, $2, $3, $4, $5)""",
                rate,
                json.dumps({}),   # vector は GrowthTracker 側で保存済み
                json.dumps({}),
                json.dumps({"breakdown": breakdown}),
                "chat",
            )
        except Exception as e:
            logger.error(f"Failed to save sync rate history: {e}")
