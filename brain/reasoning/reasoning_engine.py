"""cocoro-core — Reasoning Engine
思考連鎖 (Chain of Thought) を人格フィルタ付きで実行する。
LLMは「声帯」、Reasoning Engineは「思考回路」。
"""
import json
import logging

logger = logging.getLogger("cocoro.reasoning")

REASONING_PROMPT = """以下の問題について、段階的に思考してください。

{values_context}

{beliefs_context}

【問題】
{question}

【思考手順】
1. 問題の本質を分析する
2. 自分の価値観・信念に照らして評価する
3. 過去の経験から類似事例を想起する
4. 選択肢を列挙する
5. 各選択肢を価値観で評価する
6. 結論を出す

以下のJSON形式で回答:
{{
  "analysis": "問題の分析",
  "options": ["選択肢1", "選択肢2"],
  "evaluation": "価値観に基づく評価",
  "conclusion": "最終結論",
  "confidence": 0.0,
  "reasoning_chain": ["思考ステップ1", "思考ステップ2"]
}}"""


class ReasoningEngine:
    """人格に基づく思考エンジン"""

    def __init__(self, personality, memory):
        self.personality = personality
        self.memory = memory

    async def build_reasoning_prompt(self, question: str) -> str:
        """価値観・信念を組み込んだ思考プロンプトを構築"""
        values_ctx = await self.personality.values.to_prompt()
        beliefs_ctx = await self.personality.beliefs.to_prompt()
        return REASONING_PROMPT.format(
            values_context=values_ctx,
            beliefs_context=beliefs_ctx,
            question=question,
        )

    def parse_reasoning(self, llm_output: str) -> dict:
        """LLM出力をパース"""
        try:
            start = llm_output.find("{")
            end = llm_output.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(llm_output[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {
            "analysis": llm_output,
            "options": [],
            "evaluation": "",
            "conclusion": llm_output[:200],
            "confidence": 0.5,
            "reasoning_chain": [llm_output[:300]],
        }

    async def record_thought(self, question: str, result: dict, session_id: str = None) -> str:
        """思考結果を記憶に保存"""
        values = await self.personality.values.get_all()
        value_names = [v["name"] for v in values[:5]]
        return await self.memory.long.save_thought(
            thought_type="reasoning",
            input_summary=question[:200],
            reasoning_chain=json.dumps(result.get("reasoning_chain", []), ensure_ascii=False),
            conclusion=result.get("conclusion", ""),
            confidence=result.get("confidence", 0.5),
            values_applied=value_names,
            session_id=session_id,
        )
