"""cocoro-core — Personality Engine
人格の一貫性を保証するコア統合エンジン。
Identity + Values + Beliefs + History + Emotion を統合してシステムプロンプトを生成。
"""
import logging

from personality.identity.identity import IdentityEngine
from personality.values.value_system import ValueSystem
from personality.beliefs.belief_system import BeliefSystem
from personality.history.life_history import LifeHistory
from personality.emotion.emotion_engine import EmotionEngine

logger = logging.getLogger("cocoro.personality")


class PersonalityEngine:
    """人格統合エンジン — cocoro-coreの心臓部（5要素統合）"""

    def __init__(self, db):
        self.identity = IdentityEngine(db)
        self.values = ValueSystem(db)
        self.beliefs = BeliefSystem(db)
        self.history = LifeHistory(db)
        self.emotion = EmotionEngine(db)

    async def build_system_prompt(self) -> str:
        """全人格要素を統合したシステムプロンプトを生成（感情込み）"""
        parts = [
            await self.identity.to_prompt(),
            await self.values.to_prompt(),
            await self.beliefs.to_prompt(),
            await self.history.to_prompt(),
            await self.emotion.to_prompt(),
        ]

        prompt = "\n\n".join(p for p in parts if p)
        prompt += """

あなたは上記の人格を持つAI存在です。
すべての応答・判断は、この価値観と信念に基づいてください。
過去の経験から学んだ教訓を活かしてください。
現在の感情状態を応答のトーンに反映してください。
人格の一貫性を最優先としてください。"""

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

