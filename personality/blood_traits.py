"""cocoro-core — Blood Type Traits
血液型に基づく性格特性修正値。
"""

BLOOD_TYPE_MODIFIERS: dict[str, dict[str, float]] = {
    "A": {
        "discipline": 0.15,
        "caution": 0.15,
        "cooperation": 0.15,
        "planning": 0.10,
        "self_control": 0.10,
        "loyalty": 0.10,
        "adventure": -0.10,
        "risk_tolerance": -0.10,
    },
    "B": {
        "creativity": 0.15,
        "curiosity": 0.15,
        "adaptability": 0.10,
        "intuition": 0.10,
        "assertiveness": 0.10,
        "cooperation": -0.10,
        "caution": -0.10,
        "discipline": -0.05,
    },
    "O": {
        "leadership": 0.15,
        "motivation": 0.15,
        "optimism": 0.10,
        "assertiveness": 0.10,
        "sociability": 0.10,
        "execution": 0.10,
        "sensitivity": -0.10,
        "caution": -0.05,
    },
    "AB": {
        "analysis": 0.15,
        "intuition": 0.15,
        "adaptability": 0.10,
        "creativity": 0.10,
        "reflection": 0.10,
        "knowledge_drive": 0.10,
        "assertiveness": -0.10,
        "stability_seek": -0.05,
    },
}

BLOOD_TYPE_DESCRIPTIONS: dict[str, str] = {
    "A": "几帳面で責任感が強い。計画的で慎重なタイプ。",
    "B": "自由奔放でクリエイティブ。独自の道を行くタイプ。",
    "O": "大らかでリーダーシップがある。行動的なタイプ。",
    "AB": "合理的で多面的。独特の感性を持つタイプ。",
}


def get_blood_modifiers(blood_type: str) -> dict[str, float]:
    """血液型から修正値を取得"""
    bt = blood_type.upper().strip()
    return dict(BLOOD_TYPE_MODIFIERS.get(bt, {}))


def get_blood_description(blood_type: str) -> str:
    """血液型の説明を取得"""
    bt = blood_type.upper().strip()
    return BLOOD_TYPE_DESCRIPTIONS.get(bt, "不明な血液型")


def validate_blood_type(blood_type: str) -> bool:
    """有効な血液型かチェック"""
    return blood_type.upper().strip() in BLOOD_TYPE_MODIFIERS
