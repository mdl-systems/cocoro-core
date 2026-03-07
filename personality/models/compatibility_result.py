"""cocoro-core — Compatibility Result Model
相性結果のデータモデル。
"""
import uuid
from datetime import datetime


class CompatibilityResult:
    """相性診断結果"""

    def __init__(self, profile_a_id: str, profile_b_id: str,
                 result: dict, relationship_type: str = "general"):
        self.id = str(uuid.uuid4())
        self.profile_a_id = profile_a_id
        self.profile_b_id = profile_b_id
        self.relationship_type = relationship_type
        self.score = result.get("compatibility_score", 0.0)
        self.level = result.get("level", {})
        self.components = result.get("components", {})
        self.strategy = result.get("interaction_strategy", {})
        self.created_at = datetime.utcnow()
        self._raw = result

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "profile_a_id": self.profile_a_id,
            "profile_b_id": self.profile_b_id,
            "relationship_type": self.relationship_type,
            "compatibility_score": self.score,
            "level": self.level,
            "components": {
                k: {"score": v.get("score", 0), "weight": v.get("weight", 0)}
                for k, v in self.components.items()
            },
            "interaction_strategy": self.strategy,
            "created_at": self.created_at.isoformat(),
        }

    def summary(self) -> str:
        label = self.level.get("label", "不明")
        return f"相性: {self.score:.1%} ({label})"
