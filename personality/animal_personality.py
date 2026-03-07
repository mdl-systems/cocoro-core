"""cocoro-core — Animal Personality Archetypes
動物パーソナリティに基づく性格特性マッピング。
"""

ANIMAL_ARCHETYPES: dict[str, dict] = {
    "lion": {
        "name": "ライオン",
        "description": "王者の風格。カリスマ性と決断力で集団を率いる。",
        "modifiers": {
            "leadership": 0.30,
            "assertiveness": 0.20,
            "discipline": 0.10,
            "motivation": 0.15,
            "self_control": 0.10,
            "cooperation": -0.10,
        },
    },
    "cheetah": {
        "name": "チーター",
        "description": "圧倒的なスピードと行動力。即断即決型。",
        "modifiers": {
            "speed": 0.30,
            "risk_tolerance": 0.25,
            "execution": 0.20,
            "adventure": 0.15,
            "patience": -0.15,
            "caution": -0.10,
        },
    },
    "elephant": {
        "name": "ゾウ",
        "description": "深い知恵と忍耐力。信頼関係を大切にする。",
        "modifiers": {
            "discipline": 0.30,
            "persistence": 0.25,
            "loyalty": 0.20,
            "patience": 0.15,
            "empathy": 0.10,
            "speed": -0.10,
        },
    },
    "koala": {
        "name": "コアラ",
        "description": "独自の世界観を持つクリエイター。マイペース。",
        "modifiers": {
            "creativity": 0.25,
            "curiosity": 0.20,
            "reflection": 0.20,
            "patience": 0.15,
            "assertiveness": -0.10,
            "speed": -0.10,
        },
    },
    "black_panther": {
        "name": "クロヒョウ",
        "description": "鋭い直感と美的感覚。独立独歩の探求者。",
        "modifiers": {
            "intuition": 0.25,
            "sensitivity": 0.20,
            "sociability": 0.20,
            "analysis": 0.10,
            "cooperation": -0.05,
            "stability_seek": -0.10,
        },
    },
    "wolf": {
        "name": "オオカミ",
        "description": "強い絆と忠誠心。チームの中で力を発揮する。",
        "modifiers": {
            "loyalty": 0.25,
            "cooperation": 0.20,
            "persistence": 0.15,
            "discipline": 0.10,
            "empathy": 0.10,
            "sociability": -0.10,
        },
    },
    "eagle": {
        "name": "ワシ",
        "description": "鳥瞰的視点と高い目標。全体を見渡す戦略家。",
        "modifiers": {
            "analysis": 0.25,
            "planning": 0.20,
            "knowledge_drive": 0.15,
            "risk_tolerance": 0.10,
            "purpose": 0.10,
            "empathy": -0.10,
        },
    },
    "dolphin": {
        "name": "イルカ",
        "description": "高いコミュニケーション力と楽観性。場を明るくする。",
        "modifiers": {
            "sociability": 0.25,
            "optimism": 0.20,
            "cooperation": 0.15,
            "adaptability": 0.15,
            "empathy": 0.10,
            "discipline": -0.10,
        },
    },
    "owl": {
        "name": "フクロウ",
        "description": "知性と洞察力。静かに観察し本質を見抜く。",
        "modifiers": {
            "analysis": 0.25,
            "knowledge_drive": 0.20,
            "reflection": 0.20,
            "intuition": 0.15,
            "caution": 0.10,
            "speed": -0.15,
        },
    },
    "cat": {
        "name": "ネコ",
        "description": "自由気ままで独立心が強い。繊細な感性。",
        "modifiers": {
            "curiosity": 0.25,
            "sensitivity": 0.20,
            "adaptability": 0.15,
            "creativity": 0.15,
            "cooperation": -0.15,
            "discipline": -0.10,
        },
    },
    "bear": {
        "name": "クマ",
        "description": "力強さと優しさの両面。守るべきものを大切にする。",
        "modifiers": {
            "self_control": 0.20,
            "persistence": 0.20,
            "loyalty": 0.15,
            "ethics": 0.15,
            "patience": 0.10,
            "sociability": -0.10,
        },
    },
    "fox": {
        "name": "キツネ",
        "description": "賢さと機転。変化する状況に素早く適応する。",
        "modifiers": {
            "adaptability": 0.25,
            "creativity": 0.20,
            "analysis": 0.15,
            "speed": 0.10,
            "caution": 0.10,
            "loyalty": -0.10,
        },
    },
}


def get_animal_archetype(animal_type: str) -> dict | None:
    """動物タイプからアーキタイプ情報を取得"""
    return ANIMAL_ARCHETYPES.get(animal_type.lower())


def get_animal_modifiers(animal_type: str) -> dict[str, float]:
    """動物タイプから修正値を取得"""
    archetype = get_animal_archetype(animal_type)
    if archetype:
        return dict(archetype["modifiers"])
    return {}


def list_animals() -> list[dict]:
    """全動物アーキタイプ一覧"""
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in ANIMAL_ARCHETYPES.items()
    ]
