"""cocoro-core — Decision Graph
v1仕様: Memory → Value → Emotion → Decision フルパイプライン。

判断木を構築し、価値観で重み付けされた意思決定を行う。
単純なYes/Noではなく、多次元の価値観と感情と過去記憶で判断する。
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
- chat: 雑談・質問・情報確認・日常会話。以下もchatに含む:
  * 時刻・日付を聞く（「今何時？」「今日は何曜日？」）
  * スケジュール操作（「予定を入れて」「明日の予定は？」）
  * 組織・Agent状況の確認（「Agentの状態は？」）
  * Web検索・調べもの（「〜を調べて」「〜って何？」）
  * タスク一覧の確認（「最近のタスクは？」）
  * 過去の会話の検索（「前に話した〜」）
  * 自己紹介・人格に関する質問（「あなたは誰？」）
- think: 深く考える必要がある複雑な問題・哲学的な問い
- decide: 重要なビジネス判断・トレードオフのある意思決定
- delegate: 専門AIが長時間かけて作成する成果物の依頼のみ（レポート作成、コード生成、企画書作成、分析レポートなど）
- learn: 「覚えて」「記録して」など、明示的な学習指示

重要: 迷ったらchatにしてください。delegateは「成果物を作って」という明確な依頼のみです。

emotion基準:
- ユーザーの入力から感じ取れる感情を判定"""

DECISION_PROMPT = """以下の判断を、あなたの人格・価値観・感情状態・過去の記憶に基づいて行ってください。

{personality_prompt}

{values_context}

{emotion_context}

{memory_context}

【カテゴリ】{category}
【質問】{question}

【過去の関連判断】
{past_decisions}

上記を全て踏まえて、以下のJSON形式で回答:
{{
  "decision": "判断内容",
  "reasoning": "判断根拠（どの価値観・記憶・感情が影響したか明示）",
  "values_applied": ["使用した価値観"],
  "memory_influence": "過去の記憶がどう影響したか",
  "emotion_influence": "現在の感情がどう影響したか",
  "confidence": 0.0,
  "risk": "リスク評価",
  "alternatives": ["検討した代替案"]
}}"""


class DecisionGraph:
    """価値観ベースの意思決定エンジン（フルパイプライン）"""

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

    # === Full Pipeline: Memory → Value → Emotion → Decision ===

    async def build_decision_prompt(self, question: str, category: str = "general") -> str:
        """Memory → Value → Emotion → Decision フルパイプライン"""

        # 1. Memory: 過去の関連記憶と判断を検索
        personality_prompt = await self.personality.identity.to_prompt()
        values_ctx = await self.personality.values.apply_to_decision(question)
        past = await self.memory.long.get_past_decisions(category, limit=3)
        past_text = "\n".join(
            f"- {d['question'][:80]} → {d['decision'][:80]}" for d in past
        ) if past else "なし"

        # Memory検索: 関連する過去の会話・学習を取得
        memory_context = await self._gather_memory_context(question)

        # 2. Emotion: 現在の感情状態を取得
        emotion_context = await self._build_emotion_context()

        return DECISION_PROMPT.format(
            personality_prompt=personality_prompt, values_context=values_ctx,
            emotion_context=emotion_context, memory_context=memory_context,
            category=category, question=question, past_decisions=past_text,
        )

    async def _gather_memory_context(self, question: str) -> str:
        """Memory ステージ: 関連する過去の記憶を収集"""
        parts = ["【関連する過去の記憶】"]

        # 長期記憶から関連メッセージを検索
        try:
            related = await self.memory.long.search(question, limit=3)
            if related:
                parts.append("過去の関連会話:")
                for r in related:
                    role = r.get("role", "?")
                    content = r.get("content", "")[:100]
                    parts.append(f"  - [{role}] {content}")
        except Exception:
            pass

        # 学習データがあれば追加
        try:
            learnings = await self.memory.long.search_learnings(question, limit=2)
            if learnings:
                parts.append("過去の学習:")
                for l in learnings:
                    parts.append(f"  - {l.get('content', '')[:100]}")
        except Exception:
            pass

        if len(parts) == 1:
            parts.append("関連する記憶はありません")
        return "\n".join(parts)

    async def _build_emotion_context(self) -> str:
        """Emotion ステージ: 現在の感情状態を判断文脈に変換"""
        try:
            state = await self.personality.emotion.get_state()
            dominant = state.dominant()
            intensity = state.intensity()

            context = f"【現在の感情状態】dominant={dominant}, intensity={intensity:.2f}\n"

            # 感情が判断に与える影響を明示
            emotion_biases = {
                "happiness": "楽観的バイアスに注意。リスクを過小評価していないか確認すること。",
                "sadness": "悲観的バイアスに注意。チャンスを見逃していないか確認すること。",
                "anger": "攻撃的バイアスに注意。冷静に分析し、感情的な判断を避けること。",
                "fear": "回避バイアスに注意。リスクを過大評価していないか確認すること。",
                "trust": "信頼過多バイアスに注意。批判的視点も持つこと。",
                "surprise": "新奇性バイアスに注意。基本原則を忘れないこと。",
            }

            if dominant != "neutral" and intensity >= 0.1:
                bias_warning = emotion_biases.get(dominant, "")
                context += f"感情バイアス警告: {bias_warning}\n"
                context += f"判断は感情を認識した上で、価値観を最優先にすること。"
            else:
                context += "感情は安定しており、判断への影響は最小限です。"

            return context
        except Exception:
            return "【現在の感情状態】取得できませんでした"

    def parse_decision(self, llm_output: str) -> dict:
        try:
            start = llm_output.find("{")
            end = llm_output.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(llm_output[start:end])
                # フルパイプラインの追加フィールドにデフォルト値を設定
                data.setdefault("memory_influence", "")
                data.setdefault("emotion_influence", "")
                data.setdefault("alternatives", [])
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        return {"decision": llm_output[:200], "reasoning": "", "values_applied": [],
                "memory_influence": "", "emotion_influence": "",
                "confidence": 0.5, "risk": "unknown", "alternatives": []}

    async def record_decision(self, category: str, question: str, result: dict) -> str:
        return await self.memory.long.save_decision(
            category=category, question=question,
            decision=result.get("decision", ""),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.5),
            values_used=result.get("values_applied", []),
        )

    def get_pipeline_info(self) -> dict:
        """Decision Graphのパイプライン情報を返す（デバッグ用）"""
        return {
            "pipeline": "Memory → Value → Emotion → Decision",
            "stages": [
                {"name": "Memory", "description": "過去の会話・学習・判断を検索"},
                {"name": "Value", "description": "価値観 (weight付き) を判断コンテキストに適用"},
                {"name": "Emotion", "description": "感情状態 + バイアス警告を注入"},
                {"name": "Decision", "description": "LLMが全コンテキストを統合して判断"},
            ],
            "output_fields": [
                "decision", "reasoning", "values_applied",
                "memory_influence", "emotion_influence",
                "confidence", "risk", "alternatives",
            ],
        }
