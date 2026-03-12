"""cocoro-core — Emotion Engine
感情の連続値シミュレーション。

6感情パラメータ (0.0-1.0):
  happiness, sadness, anger, fear, trust, surprise

イベントにより変化し、時間経過で中立に減衰する。
感情は判断・応答の「色」を決める。
"""
import json
import logging
from dataclasses import dataclass, asdict

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

# テキスト内キーワード → 感情ラベルのマッピング（会話自動分析用）
KEYWORD_EMOTION_MAP: list[tuple[list[str], str, float]] = [
    (["ありがとう", "感謝", "助かった", "嬉しい", "良かった", "最高", "素晴らしい"], "grateful", 0.6),
    (["楽しい", "面白い", "好き", "ポジティブ", "幸せ", "ハッピー"], "happy", 0.5),
    (["すごい", "驚いた", "知らなかった", "初めて", "発見", "なるほど", "へえ"], "curious", 0.5),
    (["悲しい", "つらい", "残念", "失敗", "ごめん", "申し訳"], "sad", 0.4),
    (["怒り", "ムカつく", "ひどい", "最悪", "許せない", "嫌い", "批判"], "angry", 0.5),
    (["不安", "心配", "怖い", "危険", "リスク", "問題", "困った"], "anxious", 0.4),
    (["新しい", "実験", "試して", "不思議", "謎"], "curious", 0.4),
]

# trust キーワード（直接 trust パラメータを上昇させる）
TRUST_KEYWORDS = ["信頼", "安心", "頼れる", "任せる", "大丈夫", "信じる", "よろしく"]

# 中立値と減衰率
NEUTRAL_VALUES = {
    "happiness": 0.5,
    "sadness": 0.1,
    "anger": 0.0,
    "fear": 0.1,
    "trust": 0.6,
    "surprise": 0.2,
}
DECAY_RATE = 0.1
EMOTION_FIELDS = list(NEUTRAL_VALUES.keys())

# 感情の日本語説明（/emotion/state の description フィールド用）
MOOD_DESCRIPTIONS = {
    "happiness": "前向きで明るい気分です。温かく、励ましを含んだ応答をします。",
    "sadness":   "やや物静かで内省的な気分です。落ち着いた、共感のある応答をします。",
    "anger":     "やや批判的で率直な視点を持っています。問題点を明確に指摘します。",
    "fear":      "慎重で警戒的な心理状態です。リスクを考慮した応答をします。",
    "trust":     "信頼感に溢れ協力的な気分です。チームワークを重視した応答をします。",
    "surprise":  "好奇心旺盛で探究的な気分です。新しい発見を楽しんで応答します。",
    "neutral":   "バランスのとれた冷静な状態です。",
}

MOOD_SHORT = {
    "happiness": "前向きで明るい",
    "sadness":   "物静かで内省的",
    "anger":     "批判的で率直",
    "fear":      "慎重で警戒的",
    "trust":     "協力的で信頼感旺盛",
    "surprise":  "好奇心旺盛で探究的",
    "neutral":   "冷静でバランスが取れている",
}


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
        """最も強い感情を返す（中立値からの偏差が最大のもの）"""
        max_delta = 0.0
        dominant = "neutral"
        for f in EMOTION_FIELDS:
            val = getattr(self, f)
            delta = abs(val - NEUTRAL_VALUES[f])
            if delta > max_delta:
                max_delta = delta
                dominant = f
        return "neutral" if max_delta < 0.15 else dominant

    def to_dict(self) -> dict:
        d = {k: round(v, 3) for k, v in asdict(self).items()}
        d["dominant"] = self.dominant()
        return d

    def intensity(self) -> float:
        """感情の総強度 (0.0-1.0)"""
        total = sum(abs(getattr(self, f) - NEUTRAL_VALUES[f]) for f in EMOTION_FIELDS)
        return min(1.0, total / len(EMOTION_FIELDS))

    def description(self) -> str:
        """現在の感情状態の日本語説明"""
        return MOOD_DESCRIPTIONS.get(self.dominant(), "バランスのとれた冷静な状態です。")

    def short_mood(self) -> str:
        """短い感情説明（system prompt 冒頭用）"""
        return MOOD_SHORT.get(self.dominant(), "冷静でバランスが取れている")


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
        """イベント（感情ラベル）に基づいて感情状態を変化させる"""
        state = await self.get_state()
        before = state.to_dict()
        adjustments = {}

        deltas = EMOTION_LABEL_MAP.get(emotion_label, {})
        for field_name, delta in deltas.items():
            old_val = getattr(state, field_name)
            new_val = max(0.0, min(1.0, old_val + delta * intensity))
            setattr(state, field_name, new_val)
            adjustments[field_name] = {
                "before": round(old_val, 3),
                "after": round(new_val, 3),
                "delta": round(delta * intensity, 3),
            }

        if adjustments:
            await self._save_state(state)
            await self._record_history(emotion_label, before, state.to_dict(), adjustments)
            logger.info(f"Emotion adjusted: {emotion_label} → dominant={state.dominant()}, "
                        f"intensity={state.intensity():.2f}")

        return {"before": before, "after": state.to_dict(),
                "adjustments": adjustments, "dominant": state.dominant()}

    async def analyze_and_adjust(self, text: str) -> str:
        """会話テキストを分析して感情を自動更新する（ユーザー発言・AI応答両方に適用）。

        Returns:
            適用された感情ラベル（変化なしの場合 "neutral"）
        """
        if not text or len(text) < 2:
            return "neutral"

        # キーワードマッチで最強の感情を検出
        detected_label = "neutral"
        max_intensity = 0.0
        for keywords, label, kw_intensity in KEYWORD_EMOTION_MAP:
            for kw in keywords:
                if kw in text:
                    if kw_intensity > max_intensity:
                        max_intensity = kw_intensity
                        detected_label = label
                    break

        # trust キーワードは直接 trust を上昇
        trust_hit = any(kw in text for kw in TRUST_KEYWORDS)
        if trust_hit:
            state = await self.get_state()
            before = state.to_dict()
            old_trust = state.trust
            state.trust = min(1.0, state.trust + 0.08)
            if abs(state.trust - old_trust) > 0.001:
                await self._save_state(state)
                await self._record_history(
                    "trust_keyword", before, state.to_dict(),
                    {"trust": {"before": round(old_trust, 3),
                               "after": round(state.trust, 3), "delta": 0.08}},
                )

        if detected_label != "neutral" and max_intensity > 0:
            await self.adjust(detected_label, intensity=max_intensity * 0.5)
            return detected_label

        return "neutral"

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
            new_val = max(0.0, min(1.0, current + (neutral - current) * DECAY_RATE))
            setattr(state, f, new_val)
            adjustments[f] = {"before": round(current, 3), "after": round(new_val, 3)}

        if adjustments:
            await self._save_state(state)
            logger.info(f"Emotion decayed: {len(adjustments)} params, dominant={state.dominant()}")

        return {"before": before, "after": state.to_dict(), "decayed": len(adjustments)}

    async def to_prompt(self) -> str:
        """感情状態をプロンプト文に変換（system prompt 冒頭に付加する 1 行）"""
        state = await self.get_state()
        if state.intensity() < 0.1:
            return "【現在の気分】冷静でバランスが取れている"
        return f"【現在の気分】{state.short_mood()}（{state.dominant()}・強度{state.intensity():.0%}）"

    async def get_history(self, limit: int = 20) -> list[dict]:
        """感情変化の履歴"""
        rows = await self.db.fetch(
            "SELECT trigger_event, before_state, after_state, adjustments, created_at "
            "FROM emotion_history ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

    async def get_history_7days(self) -> list[dict]:
        """過去7日間の感情変化履歴"""
        rows = await self.db.fetch(
            "SELECT trigger_event, before_state, after_state, adjustments, created_at "
            "FROM emotion_history "
            "WHERE created_at >= NOW() - INTERVAL '7 days' "
            "ORDER BY created_at DESC LIMIT 500"
        )
        return [dict(r) for r in rows]

    async def _save_state(self, state: EmotionState):
        """DBに感情状態を保存"""
        await self.db.execute(
            "UPDATE emotion_state SET "
            "happiness=$1, sadness=$2, anger=$3, fear=$4, trust=$5, surprise=$6, "
            "dominant_emotion=$7 "
            "WHERE id=(SELECT id FROM emotion_state LIMIT 1)",
            state.happiness, state.sadness, state.anger,
            state.fear, state.trust, state.surprise, state.dominant())
        self._cache = state

    async def _record_history(self, trigger: str, before: dict, after: dict, adjustments: dict):
        """感情変化を履歴に記録"""
        await self.db.execute(
            "INSERT INTO emotion_history (trigger_event, before_state, after_state, adjustments) "
            "VALUES ($1, $2, $3, $4)",
            trigger, json.dumps(before), json.dumps(after), json.dumps(adjustments))
