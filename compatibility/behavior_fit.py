"""cocoro-core — Behavior Fit Calculator
行動パターンの適合度を計算する。
"""
from personality.personality_vector import PersonalityVector

BEHAVIOR_TRAITS = ["speed", "patience", "risk_tolerance", "sociability"]

# 行動特性の大きな不一致を許容する閾値
MISMATCH_THRESHOLD = 0.3


def calculate_behavior_fit(vec_a: PersonalityVector,
                            vec_b: PersonalityVector) -> dict:
    """行動フィット計算
    
    speed, patience, risk_tolerance, sociability の大きな不一致を検出。
    不一致が大きいほど低スコア。
    """
    trait_fits = []
    total_penalty = 0.0

    for trait in BEHAVIOR_TRAITS:
        val_a = vec_a.get(trait)
        val_b = vec_b.get(trait)
        diff = abs(val_a - val_b)

        # 閾値を超える不一致にはペナルティ
        if diff > MISMATCH_THRESHOLD:
            penalty = (diff - MISMATCH_THRESHOLD) * 2.0
        else:
            penalty = 0.0

        total_penalty += penalty

        trait_fits.append({
            "trait": trait,
            "a": round(val_a, 4),
            "b": round(val_b, 4),
            "difference": round(diff, 4),
            "mismatch": diff > MISMATCH_THRESHOLD,
            "penalty": round(penalty, 4),
        })

    # 最大ペナルティは各特性 1.4 × 4 = 5.6
    max_penalty = len(BEHAVIOR_TRAITS) * 1.4
    behavior_fit = max(0.0, 1.0 - (total_penalty / max_penalty))

    mismatches = [t for t in trait_fits if t["mismatch"]]
    friction_areas = [t["trait"] for t in mismatches]

    return {
        "behavior_fit": round(behavior_fit, 4),
        "trait_fits": trait_fits,
        "mismatches": len(mismatches),
        "total_traits": len(BEHAVIOR_TRAITS),
        "friction_areas": friction_areas,
        "smooth_interaction": len(mismatches) == 0,
    }
