"""cocoro-core — Similarity Calculator
人格ベクトル間の類似度計算。
"""
from personality.personality_vector import PersonalityVector, ALL_PARAMS


def calculate_similarity(vec_a: PersonalityVector,
                          vec_b: PersonalityVector) -> dict:
    """類似度計算: 1 - average(|traitA - traitB|)"""
    total_diff = 0.0
    trait_diffs = {}

    for param in ALL_PARAMS:
        diff = abs(vec_a.get(param) - vec_b.get(param))
        total_diff += diff
        trait_diffs[param] = round(diff, 4)

    similarity = 1.0 - (total_diff / len(ALL_PARAMS))

    # 最も類似する特性と最も異なる特性
    sorted_diffs = sorted(trait_diffs.items(), key=lambda x: x[1])
    most_similar = sorted_diffs[:5]
    most_different = sorted_diffs[-5:]

    return {
        "similarity": round(similarity, 4),
        "average_distance": round(total_diff / len(ALL_PARAMS), 4),
        "most_similar": [{"trait": t, "diff": d} for t, d in most_similar],
        "most_different": [{"trait": t, "diff": d} for t, d in most_different],
        "trait_distances": trait_diffs,
    }
