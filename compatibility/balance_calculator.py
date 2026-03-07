"""cocoro-core — Balance Calculator
補完性（バランス）の計算。
相手が自分の弱い部分を補う関係を評価する。
"""
from personality.personality_vector import PersonalityVector

# 補完ペア: 片方が高く片方が低いと高スコア
COMPLEMENTARY_PAIRS = [
    ("planning", "execution"),
    ("creativity", "analysis"),
    ("intuition", "logic"),
    ("leadership", "cooperation"),
    ("speed", "patience"),
    ("risk_tolerance", "caution"),
    ("assertiveness", "empathy"),
    ("adventure", "stability_seek"),
    ("curiosity", "discipline"),
    ("sensitivity", "emotional_stability"),
]


def calculate_balance(vec_a: PersonalityVector,
                       vec_b: PersonalityVector) -> dict:
    """補完性スコア計算
    
    A が弱くて B が強い（またはその逆）ペアが
    多いほど高スコア。
    """
    pair_scores = []
    total_score = 0.0

    for trait_1, trait_2 in COMPLEMENTARY_PAIRS:
        a1, a2 = vec_a.get(trait_1), vec_a.get(trait_2)
        b1, b2 = vec_b.get(trait_1), vec_b.get(trait_2)

        # 各ペアについて、A の弱点を B が補う度合いを計算
        # trait_1 について: A が弱く B が強い → 補完
        complement_1 = max(0, b1 - a1) * 0.5 + max(0, a1 - b1) * 0.3
        complement_2 = max(0, b2 - a2) * 0.5 + max(0, a2 - b2) * 0.3

        # ペア内の補完: 一方が trait_1 に強く、他方が trait_2 に強い
        cross_complement = (
            abs((a1 - a2) - (b1 - b2)) * 0.3
        )

        pair_score = min(1.0, complement_1 + complement_2 + cross_complement)
        pair_scores.append({
            "pair": [trait_1, trait_2],
            "score": round(pair_score, 4),
            "a_values": [round(a1, 3), round(a2, 3)],
            "b_values": [round(b1, 3), round(b2, 3)],
        })
        total_score += pair_score

    balance = total_score / len(COMPLEMENTARY_PAIRS)

    # 強い補完関係のペア
    strong_complements = sorted(pair_scores, key=lambda x: x["score"], reverse=True)

    return {
        "balance": round(balance, 4),
        "pair_count": len(COMPLEMENTARY_PAIRS),
        "pair_scores": pair_scores,
        "strongest_complements": strong_complements[:3],
        "weakest_complements": strong_complements[-3:],
    }
