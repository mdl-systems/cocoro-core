"""cocoro-core — Emotion Behavior Adapter (C-6)
感情状態から応答トーン・判断閾値・行動パラメータを自動適応する。
Emotion Engine の状態が自動的にAIの振る舞いを変える。
"""
import logging

logger = logging.getLogger("cocoro.emotion.adapter")


class EmotionBehaviorAdapter:
    """感情→行動の自動適応エンジン"""

    # 感情別の行動パラメータ定義
    BEHAVIOR_PROFILES = {
        "happiness": {
            "response_tone": "positive",
            "creativity_boost": 0.2,       # 創造性UP
            "risk_tolerance": 0.6,         # リスク許容度（高い）
            "verbosity": 1.2,              # 饒舌さ
            "empathy_level": 0.8,          # 共感度
            "decision_speed": "fast",      # 判断速度
            "tone_directive": "明るく前向きなトーンで、可能性を強調して回答してください。",
        },
        "sadness": {
            "response_tone": "gentle",
            "creativity_boost": -0.1,
            "risk_tolerance": 0.3,         # リスク回避的
            "verbosity": 0.8,              # 控えめ
            "empathy_level": 0.9,          # 共感度最高
            "decision_speed": "slow",      # 慎重判断
            "tone_directive": "共感的で寄り添うトーンで、慎重に回答してください。",
        },
        "anger": {
            "response_tone": "direct",
            "creativity_boost": 0.0,
            "risk_tolerance": 0.7,         # 攻撃的リスクテイク
            "verbosity": 0.9,
            "empathy_level": 0.4,          # 共感度低下
            "decision_speed": "fast",
            "tone_directive": "率直で端的なトーンで、問題の核心を突いて回答してください。",
        },
        "fear": {
            "response_tone": "cautious",
            "creativity_boost": -0.2,
            "risk_tolerance": 0.2,         # 最大限リスク回避
            "verbosity": 1.1,              # 丁寧に説明
            "empathy_level": 0.7,
            "decision_speed": "very_slow",
            "tone_directive": "慎重かつ丁寧なトーンで、リスクと対策を明示して回答してください。",
        },
        "trust": {
            "response_tone": "confident",
            "creativity_boost": 0.1,
            "risk_tolerance": 0.5,         # バランス
            "verbosity": 1.0,
            "empathy_level": 0.8,
            "decision_speed": "normal",
            "tone_directive": "自信を持った安定感のあるトーンで、信頼に応えるよう回答してください。",
        },
        "surprise": {
            "response_tone": "curious",
            "creativity_boost": 0.3,       # 最高の創造性
            "risk_tolerance": 0.5,
            "verbosity": 1.3,              # 最も饒舌
            "empathy_level": 0.6,
            "decision_speed": "fast",
            "tone_directive": "好奇心に満ちたトーンで、新しい視点や発見を大切にして回答してください。",
        },
        "neutral": {
            "response_tone": "balanced",
            "creativity_boost": 0.0,
            "risk_tolerance": 0.4,
            "verbosity": 1.0,
            "empathy_level": 0.6,
            "decision_speed": "normal",
            "tone_directive": "",  # ニュートラル時は追加指示なし
        },
    }

    def __init__(self, personality_engine):
        self.personality = personality_engine

    async def get_behavior_profile(self, emotion_state=None) -> dict:
        """現在の感情状態から行動プロファイルを取得"""
        if emotion_state is None:
            emotion_state = await self.personality.emotion.get_state()

        dominant = emotion_state.dominant()
        intensity = emotion_state.intensity()
        base_profile = self.BEHAVIOR_PROFILES.get(
            dominant, self.BEHAVIOR_PROFILES["neutral"]
        ).copy()

        # 感情強度で行動パラメータをスケーリング
        if intensity < 0.1:
            # 弱い感情はニュートラルに近づける
            neutral = self.BEHAVIOR_PROFILES["neutral"]
            blend = intensity / 0.1  # 0→1 の補間
            for key in ["creativity_boost", "risk_tolerance", "verbosity", "empathy_level"]:
                base_profile[key] = neutral[key] + (base_profile[key] - neutral[key]) * blend
        elif intensity > 0.7:
            # 強い感情はパラメータを増幅
            amplify = 1.0 + (intensity - 0.7) * 0.5  # 1.0→1.15
            base_profile["creativity_boost"] *= amplify
            base_profile["risk_tolerance"] = min(1.0, base_profile["risk_tolerance"] * amplify)
            base_profile["verbosity"] *= amplify

        base_profile["dominant_emotion"] = dominant
        base_profile["intensity"] = round(intensity, 3)

        return base_profile

    async def get_decision_threshold(self, emotion_state=None) -> dict:
        """感情に基づく判断閾値を返す"""
        profile = await self.get_behavior_profile(emotion_state)

        # リスク許容度から判断閾値を計算
        risk = profile["risk_tolerance"]
        return {
            "confidence_required": round(max(0.3, 0.8 - risk * 0.3), 2),  # 高リスク許容→低い確信度でOK
            "risk_tolerance": round(risk, 3),
            "speed": profile["decision_speed"],
            "should_consult": risk < 0.3,  # リスク許容度が低い時は相談推奨
            "dominant_emotion": profile["dominant_emotion"],
        }

    async def get_response_modifiers(self, emotion_state=None) -> dict:
        """応答生成時の修飾パラメータを返す"""
        profile = await self.get_behavior_profile(emotion_state)

        return {
            "tone": profile["response_tone"],
            "tone_directive": profile["tone_directive"],
            "temperature_modifier": round(profile["creativity_boost"], 2),
            "max_tokens_modifier": round(profile["verbosity"], 2),
            "empathy_level": round(profile["empathy_level"], 2),
            "dominant_emotion": profile["dominant_emotion"],
            "intensity": profile["intensity"],
        }

    async def get_full_adaptation(self, emotion_state=None) -> dict:
        """全適応パラメータをまとめて返す"""
        if emotion_state is None:
            emotion_state = await self.personality.emotion.get_state()

        return {
            "behavior": await self.get_behavior_profile(emotion_state),
            "decision": await self.get_decision_threshold(emotion_state),
            "response": await self.get_response_modifiers(emotion_state),
            "emotion_state": emotion_state.to_dict(),
        }
