"""cocoro-core — Personality Profile Model
人格プロファイルデータモデル。
"""
import uuid
from datetime import datetime, date
from typing import Optional
from personality.personality_vector import PersonalityVector
from personality.zodiac_traits import determine_zodiac, get_zodiac_modifiers
from personality.animal_personality import get_animal_modifiers, get_animal_archetype
from personality.blood_traits import get_blood_modifiers, validate_blood_type


class PersonalityProfile:
    """人格プロファイル — 32次元ベクトル + メタ情報"""

    def __init__(self, birthdate: date, blood_type: str,
                 animal_type: str = "wolf",
                 profile_id: str = None):
        self.id = profile_id or str(uuid.uuid4())
        self.birthdate = birthdate
        self.blood_type = blood_type.upper().strip()
        self.animal_type = animal_type.lower().strip()
        self.zodiac_sign = determine_zodiac(birthdate.month, birthdate.day)
        self.vector = PersonalityVector()
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def generate_seed(self) -> dict:
        """生年月日・血液型・動物タイプから初期ベクトルを生成"""
        applied_modifiers = {}

        # 1. 星座修正
        zodiac_mods = get_zodiac_modifiers(self.zodiac_sign)
        self.vector.apply_modifiers(zodiac_mods)
        applied_modifiers["zodiac"] = zodiac_mods

        # 2. 動物人格修正
        animal_mods = get_animal_modifiers(self.animal_type)
        self.vector.apply_modifiers(animal_mods)
        applied_modifiers["animal"] = animal_mods

        # 3. 血液型修正
        blood_mods = get_blood_modifiers(self.blood_type)
        self.vector.apply_modifiers(blood_mods)
        applied_modifiers["blood_type"] = blood_mods

        self.updated_at = datetime.utcnow()

        return {
            "profile_id": self.id,
            "zodiac_sign": self.zodiac_sign,
            "animal_type": self.animal_type,
            "blood_type": self.blood_type,
            "modifiers_applied": applied_modifiers,
            "vector": self.vector.to_categorized_dict(),
            "dominant_traits": self.vector.dominant_traits(5),
        }

    def apply_question_modifiers(self, modifiers: dict[str, float]) -> dict:
        """質問回答による修正を適用"""
        self.vector.apply_modifiers(modifiers)
        self.updated_at = datetime.utcnow()
        return {
            "applied": True,
            "modifiers_count": len(modifiers),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict(self) -> dict:
        """プロファイル全体を辞書に変換"""
        animal_info = get_animal_archetype(self.animal_type)
        return {
            "id": self.id,
            "birthdate": self.birthdate.isoformat(),
            "blood_type": self.blood_type,
            "animal_type": self.animal_type,
            "animal_name": animal_info["name"] if animal_info else self.animal_type,
            "zodiac_sign": self.zodiac_sign,
            "personality_vector": self.vector.to_dict(),
            "personality_categorized": self.vector.to_categorized_dict(),
            "category_averages": self.vector.category_averages(),
            "dominant_traits": [
                {"trait": t, "value": round(v, 4)}
                for t, v in self.vector.dominant_traits(5)
            ],
            "weak_traits": [
                {"trait": t, "value": round(v, 4)}
                for t, v in self.vector.weak_traits(5)
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersonalityProfile":
        """辞書からプロファイルを復元"""
        profile = cls(
            birthdate=date.fromisoformat(data["birthdate"]),
            blood_type=data["blood_type"],
            animal_type=data.get("animal_type", "wolf"),
            profile_id=data.get("id"),
        )
        if "personality_vector" in data:
            profile.vector = PersonalityVector.from_dict(data["personality_vector"])
        return profile
