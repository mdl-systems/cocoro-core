"""cocoro-core — Emotion Engine
感情の連続値シミュレーション。

6感情パラメータ (0.0-1.0):
  happiness, sadness, anger, fear, trust, surprise

イベントにより変化し、時間経過で中立に減衰する。
感情は判断・応答の「色」を決める。
"""
import json
import math
import logging
from dataclasses import dataclass, asdict, field

logger = logging.getLogger("cocoro.emotion")

# 感情ラベル → パラメータ変化のマッピング
EMOTION_LABEL_MAP: dict[str, dict[str, float]] = {
    "happy":    {"happiness": +0.20, "sadness": -0.05, "trust": +0.05},
    "grateful": {"happiness": +0.15, "trust": +0.15, "sadness": -0.05},
    "excited":  {"happiness": +0.15, "surprise": +0.15, "fear": -0.05},
    "curious":  {"surprise": +0.10, "happiness": +0.05, "fear": -0.03},
    "neutral":  {},  # 変化なし
    "sad":      {"sadness": +0.20, "happiness": -0.10, "trust": -0.05},
    "angry":    {"anger": +0.25, "happiness": -0.10, "trust": -0.10},
    "anxious":  {"fear": +0.20, "happiness": -0.05, "trust": -0.05, "sadness": +0.05},
}

# 減衰率: 各感情は中立値に向かって時間経過で戻る
NEUTRAL_VALUES = {
    "happiness": 0.5,
    "sadness": 0.1,
    "anger": 0.0,
    "fear": 0.1,
    "trust": 0.6,
    "surprise": 0.2,
}

DECAY_RATE = 0.1  # 1回の減衰で中立方向に10%戻る
EMOTION_FIELDS = list(NEUTRAL_VALUES.keys())


@dataclass
class EmotionState:
    """6次元の感情状態"""
    happiness: float = 0.5
    sadness: float = 0.1
    anger: float = 0.0
    fear: float = 0.1
    trust: float = 0.6
    surprise: float = 0.2

    def dominant(self) -> str:
        """最も強い感情を返す"""
        # 中立値からの偏差が最大のものを支配的感情とする
        max_delta = 0.0
        dominant = "neutral"
        for f in EMOTION_FIELDS:
            val = getattr(self, f)
            neutral = NEUTRAL_VALUES[f]
            delta = abs(val - neutral)
            if delta > max_delta:
                max_delta = delta
                dominant = f
        # 偏差が小さすぎる場合は neutral
        if max_delta < 0.15:
            return "neutral"
        return dominant

    def to_dict(self) -> dict:
        d = asdict(self)
        d["dominant"] = self.dominant()
        return d

    def intensity(self) -> float:
        """感情の総強度 (0.0-1.0)"""
        total = sum(abs(getattr(self, f) - NEUTRAL_VALUES[f]) for f in EMOTION_FIELDS)
        return min(1.0, total / len(EMOTION_FIELDS))


class EmotionEngine:
    """感情の連続値シミュレーションエンジン"""

    def __init__(self, db):
        self.db = db
        self._cache: EmotionState | None = None

    async def get_state(self) -> EmotionState:
        """現在の感情状態を取得"""
        if self._cache:
            return self._cache
        row = await self.db.fetchrow(
            "SELECT happiness, sadness, anger, fear, trust, surprise FROM emotion_state LIMIT 1")
        if row:
            self._cache = EmotionState(
                happiness=float(row["happiness"]),
                sadness=float(row["sadness"]),
                anger=float(row["anger"]),
                fear=float(row["fear"]),
                trust=float(row["trust"]),
                surprise=float(row["surprise"]),
            )
        else:
            self._cache = EmotionState()
        return self._cache

    async def adjust(self, emotion_label: str, intensity: float = 1.0) -> dict:
        """イベント（感情ラベル）に基づいて感情状態を変化させる

        Args:
            emotion_label: "happy", "sad", "angry" 等
            intensity: 変化の強度倍率 (デフォルト1.0)

        Returns:
            {"before": {...}, "after": {...}, "adjustments": {...}}
        """
        state = await self.get_state()
        before = state.to_dict()
        adjustments = {}

        # ラベルに対応する変化を適用
        deltas = EMOTION_LABEL_MAP.get(emotion_label, {})
        for field_name, delta in deltas.items():
            old_val = getattr(state, field_name)
            new_val = max(0.0, min(1.0, old_val + delta * intensity))
            setattr(state, field_name, new_val)
            adjustments[field_name] = {"before": round(old_val, 3), "after": round(new_val, 3),
                                       "delta": round(delta * intensity, 3)}

        if adjustments:
            await self._save_state(state)
            await self._record_history(emotion_label, before, state.to_dict(), adjustments)
            logger.info(f"Emotion adjusted: {emotion_label} → dominant={state.dominant()}, "
                       f"intensity={state.intensity():.2f}")

        return {"before": before, "after": state.to_dict(), "adjustments": adjustments,
                "dominant": state.dominant()}

    async def decay(self) -> dict:
        """感情を中立値に向かって減衰させる（時間経過シミュレーション）"""
        state = await self.get_state()
        before = state.to_dict()
        adjustments = {}

        for f in EMOTION_FIELDS:
            current = getattr(state, f)
            neutral = NEUTRAL_VALUES[f]
            if abs(current - neutral) < 0.01:
                continue
            # 中立に向かって DECAY_RATE 分だけ戻す
            new_val = current + (neutral - current) * DECAY_RATE
            new_val = max(0.0, min(1.0, new_val))
            setattr(state, f, new_val)
            adjustments[f] = {"before": round(current, 3), "after": round(new_val, 3)}

        if adjustments:
            await self._save_state(state)
            logger.info(f"Emotion decayed: {len(adjustments)} params, dominant={state.dominant()}")

        return {"before": before, "after": state.to_dict(), "decayed": len(adjustments)}

    async def to_prompt(self) -> str:
        """感情状態をプロンプト文に変換"""
        state = await self.get_state()
        dominant = state.dominant()
        intensity = state.intensity()

        if intensity < 0.1:
            return "【感情状態】平静（安定）"

        # 感情の強さをバーで表現
        lines = ["【感情状態】"]
        for f in EMOTION_FIELDS:
            val = getattr(state, f)
            bar = "█" * int(val * 10)
            if val > 0.3 or f == dominant:
                lines.append(f"  {f}: {bar} ({val:.2f})")

        mood_map = {
            "happiness": "前向きで明るい",
            "sadness": "やや物静かで内省的",
            "anger": "やや批判的で厳しい",
            "fear": "慎重で警戒的",
            "trust": "信頼感に溢れ協力的",
            "surprise": "好奇心旺盛で探究的",
            "neutral": "バランスのとれた冷静さ",
        }
        lines.append(f"  → 今のムード: {mood_map.get(dominant, '平静')}")
        lines.append(f"  → 感情強度: {intensity:.0%}")

        return "\n".join(lines)

    async def get_history(self, limit: int = 20) -> list[dict]:
        """感情変化の履歴"""
        rows = await self.db.fetch(
            "SELECT trigger_event, before_state, after_state, adjustments, created_at "
            "FROM emotion_history ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

    async def _save_state(self, state: EmotionState):
        """DBに感情状態を保存"""
        dominant = state.dominant()
        await self.db.execute(
            "UPDATE emotion_state SET "
            "happiness=$1, sadness=$2, anger=$3, fear=$4, trust=$5, surprise=$6, "
            "dominant_emotion=$7 "
            "WHERE id=(SELECT id FROM emotion_state LIMIT 1)",
            state.happiness, state.sadness, state.anger,
            state.fear, state.trust, state.surprise, dominant)
        self._cache = state

    async def _record_history(self, trigger: str, before: dict, after: dict, adjustments: dict):
        """感情変化を履歴に記録"""
        await self.db.execute(
            "INSERT INTO emotion_history (trigger_event, before_state, after_state, adjustments) "
            "VALUES ($1, $2, $3, $4)",
            trigger, json.dumps(before), json.dumps(after), json.dumps(adjustments))
