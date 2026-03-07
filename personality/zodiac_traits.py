"""cocoro-core — Zodiac Traits
星座と四大元素に基づく性格特性マッピング。
"""

ZODIAC_SIGNS = {
    "aries":       {"element": "fire",  "month_day_range": [(3, 21), (4, 19)]},
    "taurus":      {"element": "earth", "month_day_range": [(4, 20), (5, 20)]},
    "gemini":      {"element": "air",   "month_day_range": [(5, 21), (6, 21)]},
    "cancer":      {"element": "water", "month_day_range": [(6, 22), (7, 22)]},
    "leo":         {"element": "fire",  "month_day_range": [(7, 23), (8, 22)]},
    "virgo":       {"element": "earth", "month_day_range": [(8, 23), (9, 22)]},
    "libra":       {"element": "air",   "month_day_range": [(9, 23), (10, 23)]},
    "scorpio":     {"element": "water", "month_day_range": [(10, 24), (11, 22)]},
    "sagittarius": {"element": "fire",  "month_day_range": [(11, 23), (12, 21)]},
    "capricorn":   {"element": "earth", "month_day_range": [(12, 22), (1, 19)]},
    "aquarius":    {"element": "air",   "month_day_range": [(1, 20), (2, 18)]},
    "pisces":      {"element": "water", "month_day_range": [(2, 19), (3, 20)]},
}

# 四大元素に基づく特性修正値
ELEMENT_MODIFIERS: dict[str, dict[str, float]] = {
    "fire": {
        "motivation": 0.20,
        "leadership": 0.15,
        "risk_tolerance": 0.15,
        "assertiveness": 0.10,
        "speed": 0.10,
        "optimism": 0.10,
        "caution": -0.10,
        "patience": -0.05,
    },
    "earth": {
        "discipline": 0.20,
        "planning": 0.15,
        "stability_seek": 0.15,
        "persistence": 0.10,
        "patience": 0.10,
        "loyalty": 0.10,
        "adventure": -0.10,
        "speed": -0.05,
    },
    "air": {
        "sociability": 0.20,
        "curiosity": 0.15,
        "adaptability": 0.15,
        "creativity": 0.10,
        "knowledge_drive": 0.10,
        "cooperation": 0.10,
        "discipline": -0.05,
        "stability_seek": -0.05,
    },
    "water": {
        "empathy": 0.20,
        "intuition": 0.15,
        "sensitivity": 0.15,
        "emotional_stability": -0.05,
        "reflection": 0.10,
        "loyalty": 0.10,
        "ethics": 0.10,
        "assertiveness": -0.10,
    },
}

# 個別星座の追加修正
SIGN_SPECIFIC_MODIFIERS: dict[str, dict[str, float]] = {
    "aries":       {"assertiveness": 0.10, "speed": 0.10, "patience": -0.10},
    "taurus":      {"persistence": 0.10, "loyalty": 0.10, "adaptability": -0.05},
    "gemini":      {"adaptability": 0.10, "creativity": 0.10, "discipline": -0.10},
    "cancer":      {"empathy": 0.10, "loyalty": 0.10, "risk_tolerance": -0.10},
    "leo":         {"leadership": 0.15, "optimism": 0.10, "cooperation": -0.05},
    "virgo":       {"analysis": 0.15, "planning": 0.10, "risk_tolerance": -0.05},
    "libra":       {"fairness": 0.15, "cooperation": 0.10, "assertiveness": -0.10},
    "scorpio":     {"persistence": 0.15, "intuition": 0.10, "sociability": -0.10},
    "sagittarius": {"adventure": 0.15, "optimism": 0.10, "caution": -0.10},
    "capricorn":   {"discipline": 0.15, "self_control": 0.10, "speed": -0.10},
    "aquarius":    {"creativity": 0.15, "knowledge_drive": 0.10, "loyalty": -0.05},
    "pisces":      {"sensitivity": 0.15, "empathy": 0.10, "assertiveness": -0.10},
}


def determine_zodiac(month: int, day: int) -> str:
    """月日から星座を判定"""
    for sign, info in ZODIAC_SIGNS.items():
        (m1, d1), (m2, d2) = info["month_day_range"]
        if m1 == m2:
            if month == m1 and d1 <= day <= d2:
                return sign
        elif m1 > m2:  # capricorn: 12/22 - 1/19
            if (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return sign
        else:
            if (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return sign
    return "unknown"


def get_zodiac_element(sign: str) -> str:
    """星座の元素を取得"""
    info = ZODIAC_SIGNS.get(sign, {})
    return info.get("element", "unknown")


def get_zodiac_modifiers(sign: str) -> dict[str, float]:
    """星座から人格修正値を取得（元素 + 個別）"""
    element = get_zodiac_element(sign)
    modifiers = dict(ELEMENT_MODIFIERS.get(element, {}))
    # 個別修正を上乗せ
    specific = SIGN_SPECIFIC_MODIFIERS.get(sign, {})
    for k, v in specific.items():
        modifiers[k] = modifiers.get(k, 0) + v
    return modifiers
