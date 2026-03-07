"""cocoro-core — Value Alignment Calculator
価値観の整合性を計算する。
"""
from personality.personality_vector import PersonalityVector

VALUE_TRAITS = ["ethics", "fairness", "loyalty", "purpose"]


def calculate_value_alignment(vec_a: PersonalityVector,
                                vec_b: PersonalityVector) -> dict:
    """価値観の整合度を計算
    
    ethics, fairness, loyalty, purpose の距離が近いほど高スコア。
    """
    trait_comparisons = []
    total_distance = 0.0

    for trait in VALUE_TRAITS:
        val_a = vec_a.get(trait)
        val_b = vec_b.get(trait)
        distance = abs(val_a - val_b)
        total_distance += distance
        trait_comparisons.append({
            "trait": trait,
            "a": round(val_a, 4),
            "b": round(val_b, 4),
            "distance": round(distance, 4),
            "aligned": distance < 0.15,
        })

    alignment = 1.0 - (total_distance / len(VALUE_TRAITS))

    aligned_count = sum(1 for t in trait_comparisons if t["aligned"])
    conflict_traits = [t for t in trait_comparisons if not t["aligned"]]

    return {
        "value_alignment": round(alignment, 4),
        "trait_comparisons": trait_comparisons,
        "aligned_traits": aligned_count,
        "total_traits": len(VALUE_TRAITS),
        "conflict_areas": [t["trait"] for t in conflict_traits],
        "fully_aligned": aligned_count == len(VALUE_TRAITS),
    }
