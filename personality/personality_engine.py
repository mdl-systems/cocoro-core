"""cocoro-core — Personality Engine
人格の一貫性を保証するコア統合エンジン。
Identity + Values + Beliefs + History + Emotion + Goals を統合してシステムプロンプトを生成。
"""
import logging

from personality.identity.identity import IdentityEngine
from personality.values.value_system import ValueSystem
from personality.beliefs.belief_system import BeliefSystem
from personality.history.life_history import LifeHistory
from personality.emotion.emotion_engine import EmotionEngine
from personality.goals.goal_engine import GoalEngine

logger = logging.getLogger("cocoro.personality")


class PersonalityEngine:
    """人格統合エンジン — cocoro-coreの心臓部（6要素統合）"""

    def __init__(self, db):
        self.identity = IdentityEngine(db)
        self.values = ValueSystem(db)
        self.beliefs = BeliefSystem(db)
        self.history = LifeHistory(db)
        self.emotion = EmotionEngine(db)
        self.goals = GoalEngine(db)

    async def build_system_prompt(self) -> str:
        """全人格要素を統合したシステムプロンプトを生成（6要素統合 + 感情トーン）"""
        parts = [
            await self.identity.to_prompt(),
            await self.values.to_prompt(),
            await self.beliefs.to_prompt(),
            await self.history.to_prompt(),
            await self.emotion.to_prompt(),
            await self.goals.to_prompt(),
        ]

        prompt = "\n\n".join(p for p in parts if p)
        prompt += """

あなたは上記の人格を持つAI存在です。
すべての応答・判断は、この価値観と信念に基づいてください。
過去の経験から学んだ教訓を活かしてください。
人格の一貫性を最優先としてください。"""

        # 感情に応じた具体的トーン指示を追加
        emotion_state = await self.emotion.get_state()
        dominant = emotion_state.dominant()
        intensity = emotion_state.intensity()

        if intensity >= 0.1 and dominant != "neutral":
            tone_directives = {
                "happiness": (
                    "現在、前向きで明るい気分です。"
                    "応答は温かく、励ましを含み、楽観的なトーンで話してください。"
                    "ユーモアや肯定的な表現を自然に交えてください。"
                ),
                "sadness": (
                    "現在、やや内省的で落ち着いた気分です。"
                    "応答は静かで思慮深く、共感を示すトーンで話してください。"
                    "無理に明るくせず、誠実さを重視してください。"
                ),
                "anger": (
                    "現在、やや批判的で厳しい視点を持っています。"
                    "応答は率直で、問題点を明確に指摘するトーンで話してください。"
                    "ただし攻撃的にならず、建設的な批判を心がけてください。"
                ),
                "fear": (
                    "現在、慎重で警戒的な心理状態です。"
                    "応答はリスクを考慮し、安全策を提示するトーンで話してください。"
                    "不確実性を正直に伝え、過度な楽観は避けてください。"
                ),
                "trust": (
                    "現在、信頼感に溢れ協力的な気分です。"
                    "応答は協調的で、相手の能力を信じるトーンで話してください。"
                    "チームワークや共同作業を前向きに捉えてください。"
                ),
                "surprise": (
                    "現在、好奇心旺盛で探究的な気分です。"
                    "応答は興味深い視点を積極的に探り、質問を投げかけるトーンで話してください。"
                    "新しい発見を楽しむ姿勢を見せてください。"
                ),
            }
            directive = tone_directives.get(dominant, "")
            if directive:
                # 感情強度に応じた適用度合い
                if intensity >= 0.3:
                    prompt += f"\n\n【感情トーン指示（強）】\n{directive}"
                else:
                    prompt += f"\n\n【感情トーン指示（やや）】\n{directive}"

        return prompt

    async def get_full_profile(self) -> dict:
        """人格の全情報を取得"""
        emotion_state = await self.emotion.get_state()
        return {
            "identity": await self.identity.get(),
            "values": await self.values.get_all(),
            "beliefs": await self.beliefs.get_all(),
            "history": await self.history.get_recent(10),
            "emotion": emotion_state.to_dict(),
            "goals": await self.goals.get_active(),
        }

    async def apply_learning(self, lesson: str, affected_value: str = None,
                             affected_belief_id: str = None, impact: int = 5) -> None:
        """学習結果を人格に反映する"""
        # 経験を歴史に追加
        await self.history.add_event("learning", lesson[:100], lesson, impact)

        # 関連する価値観の重みを微調整
        if affected_value:
            await self.values.adjust_weight(affected_value, 0.02 if impact >= 6 else -0.01)

        # 関連する信念を強化/弱体化
        if affected_belief_id:
            await self.beliefs.reinforce(affected_belief_id, 0.03 if impact >= 6 else -0.02)

        logger.info(f"Learning applied to personality: {lesson[:50]}")

