"""cocoro-core — AI Tool Registry & Executor (v6)
LLM Function Calling用のツール定義と実行エンジン。
AIが自律的にツールを呼び出し、結果を利用して応答を生成する。
"""
import logging
from typing import Any

logger = logging.getLogger("cocoro.tools")


# === ツール定義（Gemini Function Calling形式） ===
TOOL_DEFINITIONS = [
    {
        "name": "search_memory",
        "description": "ユーザーとの過去の会話や記憶を検索する。以前の話題や文脈を思い出すときに使う。",
        "parameters": {
            "query": "検索キーワードまたは質問（日本語）",
        },
    },
    {
        "name": "create_task",
        "description": "新しいタスクを作成してAgentに割り当てる。ユーザーが何かをやってほしいと頼んだ時に使う。",
        "parameters": {
            "title": "タスクのタイトル（80文字以内）",
            "description": "タスクの詳細説明",
            "agent": "担当Agent（dev, sales, marketing のいずれか。不明なら空文字）",
        },
    },
    {
        "name": "get_org_status",
        "description": "AI組織の現在の状況を取得する。Agentの稼働状況や実績を確認したい時に使う。",
        "parameters": {},
    },
    {
        "name": "search_learnings",
        "description": "過去の学習内容や教訓を検索する。過去の経験から学んだことを振り返る時に使う。",
        "parameters": {
            "category": "カテゴリ（general, decision, conversation, など）",
        },
    },
    {
        "name": "get_personality",
        "description": "自分（cocoro）の人格情報を取得する。自己紹介や自分の価値観について聞かれた時に使う。",
        "parameters": {},
    },
]


class ToolExecutor:
    """ツール実行エンジン — Function Callの結果を返す"""

    def __init__(self, memory=None, worker=None, org=None,
                 personality=None, db=None, router=None):
        self.memory = memory
        self.worker = worker
        self.org = org
        self.personality = personality
        self.db = db
        self.router = router

    async def execute(self, tool_name: str, args: dict) -> dict:
        """ツールを実行して結果を返す"""
        logger.info(f"Executing tool: {tool_name}({args})")

        try:
            if tool_name == "search_memory":
                return await self._search_memory(args)
            elif tool_name == "create_task":
                return await self._create_task(args)
            elif tool_name == "get_org_status":
                return await self._get_org_status()
            elif tool_name == "search_learnings":
                return await self._search_learnings(args)
            elif tool_name == "get_personality":
                return await self._get_personality()
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {"error": str(e)}

    async def _search_memory(self, args: dict) -> dict:
        query = args.get("query", "")
        if not query:
            return {"results": [], "message": "検索キーワードが指定されていません"}

        results = await self.memory.long.search(query, limit=5)
        return {
            "results": [
                {"content": r.get("content", "")[:200],
                 "role": r.get("role", ""),
                 "created_at": str(r.get("created_at", ""))}
                for r in results
            ],
            "count": len(results),
        }

    async def _create_task(self, args: dict) -> dict:
        title = args.get("title", "")
        description = args.get("description", "")
        agent = args.get("agent", "")

        if not title:
            return {"error": "タスク名が指定されていません"}

        if not agent:
            agent = self.router.route(title, description) or "dev"

        task_id = await self.worker.execute_async(
            task_name=title, description=description,
            agent_type=agent, priority=5)

        return {
            "task_id": task_id,
            "title": title,
            "agent": agent,
            "status": "queued",
            "message": f"タスク「{title}」を{agent} Agentに割り当てました",
        }

    async def _get_org_status(self) -> dict:
        if not self.org:
            return {"error": "Organization not available"}
        report = await self.org.get_org_report()
        return report.get("summary", {})

    async def _search_learnings(self, args: dict) -> dict:
        category = args.get("category", "general")
        rows = await self.db.fetch(
            "SELECT lesson, source, importance, created_at FROM learning_log "
            "WHERE category=$1 ORDER BY importance DESC, created_at DESC LIMIT 5",
            category)
        return {
            "learnings": [dict(r) for r in rows],
            "count": len(rows),
        }

    async def _get_personality(self) -> dict:
        if not self.personality:
            return {"error": "Personality not available"}
        profile = await self.personality.get_full_profile()
        return {
            "name": profile.get("identity", {}).get("name", "Cocoro"),
            "values": [v.get("value", "") for v in profile.get("values", [])[:5]],
            "beliefs": [b.get("belief", "") for b in profile.get("beliefs", [])[:5]],
        }
