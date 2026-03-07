"""cocoro-core — Compatibility Engine
人格間の相性を総合的に評価するエンジン。
Human-Human, Human-AI, AI-AI の相性診断をサポート。
"""
import logging
from personality.personality_vector import PersonalityVector
from compatibility.similarity_calculator import calculate_similarity
from compatibility.balance_calculator import calculate_balance
from compatibility.value_alignment import calculate_value_alignment
from compatibility.behavior_fit import calculate_behavior_fit

logger = logging.getLogger("cocoro.compatibility")

# 重み付け
WEIGHTS = {
    "similarity": 0.35,
    "balance": 0.25,
    "value_alignment": 0.25,
    "behavior_fit": 0.15,
}

# 相性レベル定義
COMPATIBILITY_LEVELS = [
    (0.85, 1.00, "ideal_partner", "理想的パートナー",
     "非常に高い相性。自然体で深い関係を築ける。"),
    (0.70, 0.85, "strong_match", "強いマッチ",
     "良好な相性。互いの強みを活かし合える。"),
    (0.50, 0.70, "neutral", "普通",
     "標準的な相性。努力次第で良い関係に。"),
    (0.30, 0.50, "challenging", "課題あり",
     "相違点が多い。理解と歩み寄りが必要。"),
    (0.00, 0.30, "conflict", "衝突リスク",
     "大きな価値観の違い。慎重なコミュニケーションが必要。"),
]

# 相互作用スタイル提案
INTERACTION_STRATEGIES = {
    "ideal_partner": {
        "style": "collaborative",
        "approach": "オープンで自由な対話",
        "tips": [
            "率直な意見交換が可能",
            "共同プロジェクトに最適",
            "互いの成長を促進できる",
        ],
    },
    "strong_match": {
        "style": "collaborative",
        "approach": "建設的な議論ベース",
        "tips": [
            "定期的なコミュニケーションが重要",
            "互いの強みを認め合う",
            "小さな違いを楽しむ姿勢を持つ",
        ],
    },
    "neutral": {
        "style": "structured",
        "approach": "構造化されたコミュニケーション",
        "tips": [
            "明確な期待値を共有する",
            "定期的な振り返りを行う",
            "共通目標を設定する",
        ],
    },
    "challenging": {
        "style": "mediated",
        "approach": "仲介・調整ベース",
        "tips": [
            "相手の価値観を理解する努力をする",
            "感情的にならず論理的に話す",
            "共通点を意識的に探す",
        ],
    },
    "conflict": {
        "style": "conflict_mitigation",
        "approach": "衝突回避・論理的フレーミング",
        "tips": [
            "第三者を交えた対話を検討",
            "短い接触時間から始める",
            "書面でのコミュニケーションも活用",
        ],
    },
}


class CompatibilityEngine:
    """相性診断エンジン"""

    def __init__(self, weights: dict[str, float] = None):
        self.weights = weights or dict(WEIGHTS)

    def check(self, vec_a: PersonalityVector,
              vec_b: PersonalityVector,
              relationship_type: str = "general") -> dict:
        """2つの人格ベクトル間の相性を総合評価

        relationship_type: general / human-human / human-ai / ai-ai
        """
        # 各要素を計算
        sim_result = calculate_similarity(vec_a, vec_b)
        bal_result = calculate_balance(vec_a, vec_b)
        val_result = calculate_value_alignment(vec_a, vec_b)
        beh_result = calculate_behavior_fit(vec_a, vec_b)

        # 加重平均
        score = (
            self.weights["similarity"] * sim_result["similarity"]
            + self.weights["balance"] * bal_result["balance"]
            + self.weights["value_alignment"] * val_result["value_alignment"]
            + self.weights["behavior_fit"] * beh_result["behavior_fit"]
        )

        # レベル判定
        level = self._determine_level(score)
        strategy = INTERACTION_STRATEGIES.get(level["level_id"], {})

        result = {
            "compatibility_score": round(score, 4),
            "relationship_type": relationship_type,
            "level": level,
            "components": {
                "similarity": {
                    "score": sim_result["similarity"],
                    "weight": self.weights["similarity"],
                    "weighted": round(self.weights["similarity"] * sim_result["similarity"], 4),
                    "most_similar": sim_result["most_similar"][:3],
                    "most_different": sim_result["most_different"][:3],
                },
                "balance": {
                    "score": bal_result["balance"],
                    "weight": self.weights["balance"],
                    "weighted": round(self.weights["balance"] * bal_result["balance"], 4),
                    "strongest_complements": bal_result["strongest_complements"],
                },
                "value_alignment": {
                    "score": val_result["value_alignment"],
                    "weight": self.weights["value_alignment"],
                    "weighted": round(self.weights["value_alignment"] * val_result["value_alignment"], 4),
                    "conflict_areas": val_result["conflict_areas"],
                    "fully_aligned": val_result["fully_aligned"],
                },
                "behavior_fit": {
                    "score": beh_result["behavior_fit"],
                    "weight": self.weights["behavior_fit"],
                    "weighted": round(self.weights["behavior_fit"] * beh_result["behavior_fit"], 4),
                    "friction_areas": beh_result["friction_areas"],
                    "smooth": beh_result["smooth_interaction"],
                },
            },
            "interaction_strategy": strategy,
        }

        logger.info(
            f"Compatibility check: score={score:.4f}, "
            f"level={level['level_id']}, type={relationship_type}"
        )
        return result

    def _determine_level(self, score: float) -> dict:
        """スコアからレベルを判定"""
        for low, high, level_id, label, description in COMPATIBILITY_LEVELS:
            if low <= score <= high:
                return {
                    "level_id": level_id,
                    "label": label,
                    "description": description,
                    "range": [low, high],
                }
        return {
            "level_id": "unknown",
            "label": "不明",
            "description": "スコア範囲外",
            "range": [0, 1],
        }

    def get_report(self, result: dict) -> dict:
        """相性レポートを生成"""
        score = result["compatibility_score"]
        level = result["level"]
        components = result["components"]
        strategy = result["interaction_strategy"]

        # 強みと課題を抽出
        strengths = []
        challenges = []

        for name, comp in components.items():
            if comp["score"] >= 0.7:
                strengths.append(f"{name}: {comp['score']:.2f}")
            elif comp["score"] < 0.5:
                challenges.append(f"{name}: {comp['score']:.2f}")

        return {
            "summary": f"相性スコア: {score:.1%} ({level['label']})",
            "score": score,
            "level": level,
            "strengths": strengths,
            "challenges": challenges,
            "strategy": strategy,
            "recommendation": self._generate_recommendation(result),
        }

    def _generate_recommendation(self, result: dict) -> str:
        """相性に基づく推奨アドバイス"""
        score = result["compatibility_score"]
        if score >= 0.85:
            return "素晴らしい相性です！自然体で関係を深められます。"
        elif score >= 0.70:
            return "良い相性です。互いの強みを認め合い、共に成長しましょう。"
        elif score >= 0.50:
            return "標準的な相性です。コミュニケーションを大切にし、共通の目標を見つけましょう。"
        elif score >= 0.30:
            return "相違点がありますが、お互いを理解する努力で良い関係が築けます。"
        else:
            return "価値観の違いが大きいです。無理をせず、適切な距離感を保ちましょう。"
