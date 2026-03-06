"""cocoro-core — Value Scoring Engine
人格一貫性を保証する2層スコアリング。

v1 レビュー指摘:
「人格 = プロンプト」になっている。
→ プロンプト + スコアリング の2層にする必要がある。

2層アーキテクチャ:
Layer 1: LLMプロンプト（Values/Beliefsを含むsystem prompt）
Layer 2: 応答スコアリング（Values/Beliefsとの整合性を数値評価）

LLMが3つの選択肢を出す → 各選択肢をValuesでスコアリング → 最も整合性の高い選択肢を採用
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.value_scoring")

JST = timezone(timedelta(hours=9))


class ValueScoringEngine:
    """Value Scoring — 応答の価値観整合性を2層で保証"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm

    async def score_response(self, response: str, context: str = "") -> dict:
        """応答のValues/Beliefs整合性をスコアリング"""
        values = await self.db.fetch(
            "SELECT name, weight, description FROM values_system ORDER BY weight DESC")
        beliefs = await self.db.fetch(
            "SELECT name, strength, description FROM beliefs ORDER BY strength DESC")

        if not values and not beliefs:
            return {"total_score": 1.0, "detail": "No values/beliefs defined"}

        # LLM評価
        if self.llm:
            return await self._llm_score(response, context, values, beliefs)
        else:
            return self._rule_score(response, values, beliefs)

    async def score_options(self, options: list[str], context: str = "") -> dict:
        """複数選択肢をスコアリングして最適な選択肢を返す"""
        values = await self.db.fetch(
            "SELECT name, weight, description FROM values_system ORDER BY weight DESC")
        beliefs = await self.db.fetch(
            "SELECT name, strength, description FROM beliefs ORDER BY strength DESC")

        if not options:
            return {"error": "No options provided"}

        if self.llm:
            return await self._llm_score_options(options, context, values, beliefs)
        else:
            # ルールベースフォールバック: 最初の選択肢を返す
            return {
                "best_index": 0,
                "best_option": options[0],
                "scores": [{"index": i, "score": 0.7} for i in range(len(options))],
                "method": "fallback",
            }

    async def validate_and_rewrite(self, response: str, context: str = "") -> dict:
        """応答を検証し、必要なら価値観に沿って修正"""
        score_result = await self.score_response(response, context)
        total = score_result.get("total_score", 1.0)

        if total >= 0.7:
            return {
                "original": response,
                "rewritten": None,
                "score": total,
                "status": "passed",
            }

        # スコアが低い場合、LLMで修正
        if self.llm:
            values = await self.db.fetch(
                "SELECT name, weight FROM values_system ORDER BY weight DESC LIMIT 5")
            values_text = ", ".join(f"{v['name']}({v['weight']:.2f})" for v in values)

            rewrite_prompt = f"""以下の応答は価値観との整合性が低いです（スコア: {total:.2f}）。
重視すべき価値観: {values_text}

元の応答:
{response}

コンテキスト: {context}

価値観により沿った応答に修正してください。意味は保ちつつ、表現を調整してください。
修正した応答のみを出力してください。"""

            rewritten = await self.llm.generate(rewrite_prompt)
            return {
                "original": response,
                "rewritten": rewritten,
                "score": total,
                "status": "rewritten",
            }

        return {
            "original": response,
            "rewritten": None,
            "score": total,
            "status": "low_score",
        }

    async def _llm_score(self, response: str, context: str,
                          values: list, beliefs: list) -> dict:
        """LLMによる整合性スコアリング"""
        values_text = "\n".join(
            f"- {v['name']} (重み: {v['weight']:.2f}): {v.get('description', '')}"
            for v in values[:8])
        beliefs_text = "\n".join(
            f"- {b['name']} (強度: {b['strength']:.2f}): {b.get('description', '')}"
            for b in beliefs[:8])

        prompt = f"""以下の応答がAI人格の価値観・信念とどれだけ整合しているか評価してください。

【価値観】
{values_text}

【信念】
{beliefs_text}

【コンテキスト】
{context[:300] if context else 'なし'}

【応答】
{response[:500]}

以下のJSON形式で出力してください:
```json
{{
    "total_score": 0.85,
    "value_alignment": [
        {{"value": "誠実さ", "score": 0.9, "reason": "理由"}},
        {{"value": "成長志向", "score": 0.8, "reason": "理由"}}
    ],
    "belief_alignment": 0.85,
    "concerns": []
}}
```
total_scoreは0.0〜1.0で、1.0が完全に整合。"""

        raw = await self.llm.generate(prompt)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
                result["method"] = "llm"
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return self._rule_score(response, values, beliefs)

    async def _llm_score_options(self, options: list[str], context: str,
                                  values: list, beliefs: list) -> dict:
        """LLMによる複数選択肢スコアリング"""
        values_text = ", ".join(f"{v['name']}({v['weight']:.2f})" for v in values[:5])
        options_text = "\n".join(f"Option {i}: {opt[:200]}" for i, opt in enumerate(options))

        prompt = f"""以下の選択肢をAI人格の価値観に基づきスコアリングしてください。
価値観: {values_text}
コンテキスト: {context[:200] if context else 'なし'}

{options_text}

以下のJSON形式で出力:
```json
{{
    "best_index": 0,
    "scores": [
        {{"index": 0, "score": 0.9, "reason": "理由"}},
        {{"index": 1, "score": 0.7, "reason": "理由"}}
    ]
}}
```"""
        raw = await self.llm.generate(prompt)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
                best_idx = result.get("best_index", 0)
                result["best_option"] = options[best_idx] if best_idx < len(options) else options[0]
                result["method"] = "llm"
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "best_index": 0,
            "best_option": options[0],
            "scores": [{"index": i, "score": 0.7} for i in range(len(options))],
            "method": "fallback",
        }

    def _rule_score(self, response: str, values: list, beliefs: list) -> dict:
        """ルールベーススコアリング（LLMフォールバック）"""
        # 簡易的な文字列マッチング
        score = 0.7  # デフォルト
        matches = 0
        total_checks = 0

        for v in values[:5]:
            total_checks += 1
            name = v.get("name", "")
            if name and name in response:
                matches += 1
                score += float(v.get("weight", 0.5)) * 0.1

        alignment = matches / total_checks if total_checks > 0 else 0.7
        final = min(1.0, max(0.0, (score + alignment) / 2))

        return {
            "total_score": round(final, 3),
            "method": "rule_based",
            "value_matches": matches,
            "total_values_checked": total_checks,
        }
