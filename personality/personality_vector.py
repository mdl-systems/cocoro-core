"""cocoro-core — Personality Vector (32次元)
32パラメータで人格を表現する人格ベクトルシステム。
"""
import logging
from typing import Optional

logger = logging.getLogger("cocoro.personality_vector")

# 32次元パラメータ定義
PERSONALITY_DIMENSIONS = {
    "thinking": ["logic", "intuition", "analysis", "creativity"],
    "emotion": ["empathy", "emotional_stability", "sensitivity", "optimism"],
    "social": ["sociability", "leadership", "cooperation", "assertiveness"],
    "willpower": ["discipline", "persistence", "self_control", "motivation"],
    "risk": ["risk_tolerance", "adventure", "caution", "stability_seek"],
    "learning": ["curiosity", "knowledge_drive", "adaptability", "reflection"],
    "behavior": ["planning", "execution", "speed", "patience"],
    "values": ["ethics", "fairness", "loyalty", "purpose"],
}

ALL_PARAMS = []
for _cat, _params in PERSONALITY_DIMENSIONS.items():
    ALL_PARAMS.extend(_params)

assert len(ALL_PARAMS) == 32, f"Expected 32 params, got {len(ALL_PARAMS)}"


class PersonalityVector:
    """32次元の人格ベクトル"""

    def __init__(self, values: Optional[dict[str, float]] = None):
        self._values: dict[str, float] = {}
        for param in ALL_PARAMS:
            self._values[param] = 0.5  # デフォルト値
        if values:
            for k, v in values.items():
                if k in self._values:
                    self._values[k] = max(0.0, min(1.0, v))

    def get(self, param: str) -> float:
        return self._values.get(param, 0.5)

    def set(self, param: str, value: float) -> None:
        if param in self._values:
            self._values[param] = max(0.0, min(1.0, value))

    def adjust(self, param: str, delta: float) -> float:
        """パラメータを微調整し、新しい値を返す"""
        if param in self._values:
            new_val = max(0.0, min(1.0, self._values[param] + delta))
            self._values[param] = new_val
            return new_val
        return 0.5

    def apply_modifiers(self, modifiers: dict[str, float]) -> None:
        """複数のパラメータに修正値を適用"""
        for param, delta in modifiers.items():
            self.adjust(param, delta)

    def get_category(self, category: str) -> dict[str, float]:
        """カテゴリ別にパラメータを取得"""
        params = PERSONALITY_DIMENSIONS.get(category, [])
        return {p: self._values[p] for p in params if p in self._values}

    def distance(self, other: "PersonalityVector") -> float:
        """他のベクトルとの平均距離を計算"""
        total = sum(abs(self._values[p] - other._values[p]) for p in ALL_PARAMS)
        return total / len(ALL_PARAMS)

    def similarity(self, other: "PersonalityVector") -> float:
        """類似度 (0.0〜1.0)"""
        return 1.0 - self.distance(other)

    def to_dict(self) -> dict[str, float]:
        return dict(self._values)

    def to_categorized_dict(self) -> dict[str, dict[str, float]]:
        result = {}
        for cat, params in PERSONALITY_DIMENSIONS.items():
            result[cat] = {p: self._values[p] for p in params}
        return result

    def category_averages(self) -> dict[str, float]:
        """カテゴリごとの平均値"""
        result = {}
        for cat, params in PERSONALITY_DIMENSIONS.items():
            vals = [self._values[p] for p in params]
            result[cat] = round(sum(vals) / len(vals), 4)
        return result

    def dominant_traits(self, top_n: int = 5) -> list[tuple[str, float]]:
        """最も高い特性のTop N"""
        sorted_params = sorted(self._values.items(), key=lambda x: x[1], reverse=True)
        return sorted_params[:top_n]

    def weak_traits(self, bottom_n: int = 5) -> list[tuple[str, float]]:
        """最も低い特性のBottom N"""
        sorted_params = sorted(self._values.items(), key=lambda x: x[1])
        return sorted_params[:bottom_n]

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "PersonalityVector":
        return cls(values=data)

    def __repr__(self) -> str:
        top = self.dominant_traits(3)
        return f"PersonalityVector(top={top})"
