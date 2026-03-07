"""cocoro-core — Personality Learning
人格ベクトルの学習・更新システム。
会話や行動パターンから人格ベクトルを継続的に調整する。
"""
import logging
from datetime import datetime
from personality.personality_vector import PersonalityVector

logger = logging.getLogger("cocoro.personality_learning")


class PersonalityLearning:
    """人格学習エンジン — 経験から人格ベクトルを調整"""

    def __init__(self, learning_rate: float = 0.02, decay: float = 0.98):
        self.learning_rate = learning_rate
        self.decay = decay
        self._history: list[dict] = []

    def learn_from_feedback(self, vector: PersonalityVector,
                            feedback_type: str, traits: dict[str, float]) -> dict:
        """フィードバックからベクトルを更新

        feedback_type: positive / negative / neutral
        traits: 影響する特性と強度 {"creativity": 0.8, "discipline": 0.3}
        """
        multiplier = {
            "positive": 1.0,
            "negative": -1.0,
            "neutral": 0.3,
        }.get(feedback_type, 0.5)

        changes = {}
        for trait, intensity in traits.items():
            delta = self.learning_rate * intensity * multiplier
            old_val = vector.get(trait)
            new_val = vector.adjust(trait, delta)
            changes[trait] = {"old": round(old_val, 4), "new": round(new_val, 4),
                              "delta": round(delta, 4)}

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_type": feedback_type,
            "changes": changes,
            "traits_affected": len(changes),
        }
        self._history.append(record)
        logger.info(f"Learning applied: {feedback_type}, {len(changes)} traits updated")
        return record

    def learn_from_conversation(self, vector: PersonalityVector,
                                 analysis: dict) -> dict:
        """会話分析結果からベクトルを更新

        analysis: {"dominant_trait": "empathy", "intensity": 0.7,
                   "secondary": "cooperation", ...}
        """
        changes = {}
        dominant = analysis.get("dominant_trait")
        intensity = analysis.get("intensity", 0.5)

        if dominant:
            delta = self.learning_rate * intensity * 0.5
            old_val = vector.get(dominant)
            new_val = vector.adjust(dominant, delta)
            changes[dominant] = {"old": round(old_val, 4), "new": round(new_val, 4),
                                 "delta": round(delta, 4)}

        secondary = analysis.get("secondary")
        if secondary:
            delta = self.learning_rate * intensity * 0.25
            old_val = vector.get(secondary)
            new_val = vector.adjust(secondary, delta)
            changes[secondary] = {"old": round(old_val, 4), "new": round(new_val, 4),
                                  "delta": round(delta, 4)}

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "conversation",
            "changes": changes,
            "traits_affected": len(changes),
        }
        self._history.append(record)
        return record

    def learn_from_decision(self, vector: PersonalityVector,
                             decision_traits: dict[str, float]) -> dict:
        """意思決定の結果からベクトルを更新"""
        changes = {}
        for trait, weight in decision_traits.items():
            delta = self.learning_rate * weight * 0.3
            old_val = vector.get(trait)
            new_val = vector.adjust(trait, delta)
            changes[trait] = {"old": round(old_val, 4), "new": round(new_val, 4),
                              "delta": round(delta, 4)}

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "decision",
            "changes": changes,
            "traits_affected": len(changes),
        }
        self._history.append(record)
        return record

    def apply_decay(self, vector: PersonalityVector) -> dict:
        """全パラメータに減衰を適用（極端な値を中心に戻す）"""
        from personality.personality_vector import ALL_PARAMS
        changes = {}
        for param in ALL_PARAMS:
            current = vector.get(param)
            # 0.5 からの距離に応じて減衰
            distance_from_center = current - 0.5
            decay_amount = distance_from_center * (1 - self.decay)
            if abs(decay_amount) > 0.001:
                new_val = vector.adjust(param, -decay_amount)
                changes[param] = {"old": round(current, 4), "new": round(new_val, 4)}
        return {"decayed_params": len(changes), "changes": changes}

    def get_history(self, limit: int = 50) -> list[dict]:
        """学習履歴を取得"""
        return self._history[-limit:]

    def get_stats(self) -> dict:
        """学習統計"""
        return {
            "total_updates": len(self._history),
            "learning_rate": self.learning_rate,
            "decay_rate": self.decay,
        }
