"""cocoro-core — Memory Consolidation
短期記憶 → 長期記憶への定着プロセス。
経験を人格に反映する「睡眠」のような機能。

GPTレビュー指摘:
「Memory Consolidationが人格進化の鍵。
 短期→長期の移行時に"何を学んだか"を抽出すべき」
"""
import json
import logging

logger = logging.getLogger("cocoro.consolidation")

CONSOLIDATION_PROMPT = """以下は最近の会話と行動のログです。
この経験から以下を抽出してください。

【最近の経験】
{recent_events}

以下のJSON形式で回答:
{{
  "learnings": [
    {{"lesson": "学んだこと", "category": "general|business|technical|social", "importance": 5}}
  ],
  "value_adjustments": [
    {{"value_name": "honesty|efficiency|growth|empathy|logic|courage", "direction": "strengthen|weaken", "reason": "理由"}}
  ],
  "belief_updates": [
    {{"statement": "新しい信念or既存信念の更新", "confidence": 0.7, "action": "add|reinforce|challenge"}}
  ],
  "growth_summary": "成長の要約"
}}"""


class MemoryConsolidation:
    """記憶定着 — 経験を人格に反映"""

    def __init__(self, memory, personality, llm, growth=None):
        self.memory = memory
        self.personality = personality
        self.llm = llm
        self.growth = growth  # GrowthTracker (シンクロ率 + 勾配調整)

    async def consolidate(self, session_id: str = None) -> dict:
        """最近の経験を分析し、人格に反映する"""
        # 1. 最近の経験を収集
        events = []

        recent_decisions = await self.memory.long.get_past_decisions(limit=5)
        for d in recent_decisions:
            events.append(f"[判断] {d['question'][:100]} → {d['decision'][:100]}")

        recent_learnings = await self.memory.long.get_learnings(limit=5)
        for l in recent_learnings:
            events.append(f"[学習] {l['lesson'][:100]}")

        if not events:
            return {"status": "no_events", "learnings": []}

        # 2. LLMで経験を分析
        prompt = CONSOLIDATION_PROMPT.format(recent_events="\n".join(events))
        system_prompt = await self.personality.build_system_prompt()
        raw = await self.llm.generate(prompt, system_prompt)

        # 3. パース
        result = self._parse(raw)

        # 4. 人格に反映
        applied = await self._apply(result)

        # 5. 人格進化: 感情に基づく勾配調整
        gradient_result = {}
        if self.growth:
            # 直近の会話からポジティブ感情の割合を判定
            positive = await self._check_positive_emotion_ratio()
            gradient_result = await self.growth.apply_gradient_toward_ideal(
                positive_emotion=positive, learning_rate=0.02)
            applied["gradient"] = gradient_result

            # シンクロ率を記録
            sync = await self.growth.record_sync_rate(trigger="consolidation")
            applied["sync_rate"] = sync["sync_rate"]

        logger.info(f"Consolidation complete: {applied}")
        return {"status": "consolidated", **result, "applied": applied}

    async def _check_positive_emotion_ratio(self) -> bool:
        """直近の会話感情がポジティブ寄りかどうかを判定"""
        try:
            rows = await self.memory.long.db.fetch(
                "SELECT emotion FROM conversation_log "
                "WHERE role='user' ORDER BY created_at DESC LIMIT 20")
            if not rows:
                return True  # デフォルトはポジティブ

            positive_emotions = {'happy', 'grateful', 'excited', 'curious'}
            positive_count = sum(1 for r in rows if r["emotion"] in positive_emotions)
            ratio = positive_count / len(rows)
            logger.info(f"Positive emotion ratio: {ratio:.2f} ({positive_count}/{len(rows)})")
            return ratio >= 0.3  # 30%以上ポジティブならTrue
        except Exception:
            return True

    def _parse(self, llm_output: str) -> dict:
        try:
            s = llm_output.find("{")
            e = llm_output.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(llm_output[s:e])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"learnings": [], "value_adjustments": [], "belief_updates": [], "growth_summary": ""}

    async def _apply(self, result: dict) -> dict:
        applied = {"learnings": 0, "values": 0, "beliefs": 0}

        # 学習保存
        for l in result.get("learnings", []):
            await self.memory.long.save_learning(
                source="consolidation",
                lesson=l.get("lesson", ""),
                category=l.get("category", "general"),
                importance=l.get("importance", 5),
            )
            applied["learnings"] += 1

        # 価値観調整
        for v in result.get("value_adjustments", []):
            delta = 0.02 if v.get("direction") == "strengthen" else -0.01
            await self.personality.values.adjust_weight(v.get("value_name", ""), delta)
            applied["values"] += 1

        # 信念更新
        for b in result.get("belief_updates", []):
            action = b.get("action", "add")
            if action == "add":
                await self.personality.beliefs.add(
                    b.get("statement", ""), b.get("confidence", 0.5), "consolidation"
                )
            applied["beliefs"] += 1

        # 成長を歴史に記録
        summary = result.get("growth_summary", "")
        if summary:
            await self.personality.history.add_event(
                "milestone", f"成長: {summary[:80]}", summary, impact_score=6
            )

        return applied

