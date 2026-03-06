"""cocoro-core — Task Router"""
import logging

logger = logging.getLogger("cocoro.agent.router")

AGENTS = {
    "dev":        {"name": "Dev Agent",       "keywords": ["開発","コード","プログラム","API","バグ","設計","技術","デプロイ","テスト","GitHub","サーバー"]},
    "sales":      {"name": "Sales Agent",     "keywords": ["営業","顧客","提案","見積","交渉","商談","売上","クライアント","契約"]},
    "marketing":  {"name": "Marketing Agent", "keywords": ["マーケ","広告","SNS","コンテンツ","集客","ブランド","PR","キャンペーン","分析"]},
    "researcher": {"name": "Research Agent",  "keywords": ["調査","リサーチ","論文","分析","データ","統計","比較","検証","情報収集","トレンド"]},
    "legal":      {"name": "Legal Agent",     "keywords": ["法律","契約書","規約","コンプライアンス","利用規約","プライバシー","知的財産","特許","著作権"]},
    "finance":    {"name": "Finance Agent",   "keywords": ["経理","会計","予算","コスト","利益","財務","税金","請求","決算","キャッシュフロー"]},
    "support":    {"name": "Support Agent",   "keywords": ["サポート","問い合わせ","FAQ","トラブル","ヘルプ","カスタマー","対応","苦情","改善"]},
}

SYSTEM_PROMPTS = {
    "dev":        "あなたはDev Agentです。ソフトウェア開発、設計、コードレビュー、デバッグの専門家です。具体的で実装可能な回答をしてください。",
    "sales":      "あなたはSales Agentです。営業戦略、顧客対応、提案書作成の専門家です。数字とデータに基づいた回答をしてください。",
    "marketing":  "あなたはMarketing Agentです。デジタルマーケティング、ブランド戦略、コンテンツ企画の専門家です。ROIを意識した回答をしてください。",
    "researcher": "あなたはResearch Agentです。情報収集、データ分析、競合調査の専門家です。エビデンスベースで客観的な回答をしてください。",
    "legal":      "あなたはLegal Agentです。法務、契約書レビュー、コンプライアンスの専門家です。リスクを明示した慎重な回答をしてください。",
    "finance":    "あなたはFinance Agentです。財務分析、予算管理、コスト最適化の専門家です。数値に基づいた正確な回答をしてください。",
    "support":    "あなたはSupport Agentです。顧客対応、問題解決、FAQ管理の専門家です。丁寧で分かりやすい回答をしてください。",
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
        return SYSTEM_PROMPTS.get(agent_type, "あなたは汎用AIアシスタントです。専門的かつ具体的に回答してください。")

    def list_agents(self) -> list[dict]:
        return [{"type": k, **v} for k, v in AGENTS.items()]
