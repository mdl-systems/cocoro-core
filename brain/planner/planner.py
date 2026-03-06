"""cocoro-core — Planner
タスクを実行計画に分解する。
"""
import json
import logging

logger = logging.getLogger("cocoro.planner")

PLAN_PROMPT = """以下のタスクを実行計画に分解してください。

【タスク】{task}
【詳細】{description}

JSON形式で回答:
{{
  "steps": [
    {{"step": 1, "action": "アクション", "estimated_minutes": 30}}
  ],
  "recommended_agent": "dev|sales|marketing|null",
  "total_minutes": 60
}}"""


class Planner:
    def build_plan_prompt(self, task: str, description: str = "") -> str:
        return PLAN_PROMPT.format(task=task, description=description)

    def parse_plan(self, llm_output: str) -> dict:
        try:
            s, e = llm_output.find("{"), llm_output.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(llm_output[s:e])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"steps": [], "recommended_agent": None, "total_minutes": 0}
