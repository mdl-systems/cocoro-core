"""cocoro-core — Task Router"""
import logging

logger = logging.getLogger("cocoro.agent.router")

AGENTS = {
    "dev":       {"name": "Dev Agent",       "keywords": ["開発","コード","プログラム","API","バグ","設計","技術"]},
    "sales":     {"name": "Sales Agent",     "keywords": ["営業","顧客","提案","見積","交渉","商談","売上"]},
    "marketing": {"name": "Marketing Agent", "keywords": ["マーケ","広告","SNS","コンテンツ","集客","ブランド"]},
}


class TaskRouter:
    def route(self, task_name: str, description: str = "") -> str | None:
        text = f"{task_name} {description}".lower()
        scores = {}
        for agent_type, info in AGENTS.items():
            score = sum(1 for kw in info["keywords"] if kw in text)
            if score > 0:
                scores[agent_type] = score
        if scores:
            best = max(scores, key=scores.get)
            logger.info(f"Routed: '{task_name}' → {best}")
            return best
        return None

    def get_system_prompt(self, agent_type: str) -> str:
        agent = AGENTS.get(agent_type)
        if not agent:
            return "あなたは汎用AIアシスタントです。"
        return f"あなたは{agent['name']}です。専門的かつ具体的に回答してください。"

    def list_agents(self) -> list[dict]:
        return [{"type": k, **v} for k, v in AGENTS.items()]
