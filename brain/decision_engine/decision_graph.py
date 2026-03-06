"""cocoro-core — Decision Graph
判断木を構築し、価値観で重み付けされた意思決定を行う。
単純なYes/Noではなく、多次元の価値観で判断する。
"""
import json
import logging

logger = logging.getLogger("cocoro.decision")

CLASSIFY_PROMPT = """以下のユーザー入力を分類してください。

【入力】
{user_input}

以下のJSON形式で回答:
{{"action": "chat|think|decide|delegate|learn", "reason": "分類理由", "category": "general|business|technical|personal", "agent": "dev|sales|marketing|null", "priority": 5, "emotion": "neutral|happy|sad|angry|anxious|curious|excited|grateful"}}

分類基準:
- chat: 雑談・質問・日常会話
- think: 深く考える必要がある問題
- decide: ビジネス判断・意思決定
- delegate: 専門AIへの作業依頼
- learn: 新しい知識・経験の記録

emotion基準:
- ユーザーの入力から感じ取れる感情を判定"""

DECISION_PROMPT = """以下の判断を、あなたの価値観に基づいて行ってください。

{personality_prompt}

{values_context}

【カテゴリ】{category}
【質問】{question}

【過去の関連判断】
{past_decisions}

以下のJSON形式で回答:
{{
  "decision": "判断内容",
  "reasoning": "判断根拠",
  "values_applied": ["使用した価値観"],
  "confidence": 0.0,
  "risk": "リスク評価"
}}"""


class DecisionGraph:
    """価値観ベースの意思決定エンジン"""

    def __init__(self, personality, memory):
        self.personality = personality
        self.memory = memory

    def build_classify_prompt(self, user_input: str) -> str:
        return CLASSIFY_PROMPT.format(user_input=user_input)

    def parse_classification(self, llm_output: str) -> dict:
        try:
            start = llm_output.find("{")
            end = llm_output.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(llm_output[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"action": "chat", "reason": "parse_failed", "category": "general",
                "agent": None, "priority": 5}

    async def build_decision_prompt(self, question: str, category: str = "general") -> str:
        personality_prompt = await self.personality.identity.to_prompt()
        values_ctx = await self.personality.values.apply_to_decision(question)
        past = await self.memory.long.get_past_decisions(category, limit=3)
        past_text = "\n".join(
            f"- {d['question'][:80]} → {d['decision'][:80]}" for d in past
        ) if past else "なし"
        return DECISION_PROMPT.format(
            personality_prompt=personality_prompt, values_context=values_ctx,
            category=category, question=question, past_decisions=past_text,
        )

    def parse_decision(self, llm_output: str) -> dict:
        try:
            start = llm_output.find("{")
            end = llm_output.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(llm_output[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"decision": llm_output[:200], "reasoning": "", "values_applied": [],
                "confidence": 0.5, "risk": "unknown"}

    async def record_decision(self, category: str, question: str, result: dict) -> str:
        return await self.memory.long.save_decision(
            category=category, question=question,
            decision=result.get("decision", ""),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.5),
            values_used=result.get("values_applied", []),
        )
