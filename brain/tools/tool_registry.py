"""cocoro-core — AI Tool Registry & Executor (v6+)
LLM Function Calling用のツール定義と実行エンジン。
AIが自律的にツールを呼び出し、結果を利用して応答を生成する。
"""
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("cocoro.tools")

JST = timezone(timedelta(hours=9))

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
    # === 新規ツール ===
    {
        "name": "get_current_time",
        "description": "現在の日時を取得する。今何時か、今日は何日かを聞かれた時に使う。",
        "parameters": {},
    },
    {
        "name": "web_search",
        "description": "Webで最新情報を検索する。最新のニュース、技術情報、一般知識を調べたい時に使う。",
        "parameters": {
            "query": "検索クエリ（日本語または英語）",
        },
    },
    {
        "name": "add_schedule",
        "description": "スケジュールに予定を追加する。会議、締切、イベントなどを登録する時に使う。",
        "parameters": {
            "title": "予定のタイトル",
            "description": "詳細な説明（任意）",
            "start_at": "開始日時（ISO8601形式: 2026-03-07T10:00:00）",
            "end_at": "終了日時（ISO8601形式、任意）",
            "reminder_minutes": "リマインダー（分前、デフォルト30）",
        },
    },
    {
        "name": "list_schedules",
        "description": "今後のスケジュールを確認する。予定の一覧を見たい時に使う。",
        "parameters": {
            "days": "何日先まで表示するか（デフォルト7）",
        },
    },
    {
        "name": "list_recent_tasks",
        "description": "最近のタスク一覧を確認する。完了したタスクや進行中のタスクを確認したい時に使う。",
        "parameters": {
            "status": "フィルタ（done, queued, running, failed, 全部ならall）",
        },
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
            handler = {
                "search_memory": self._search_memory,
                "create_task": self._create_task,
                "get_org_status": self._get_org_status,
                "search_learnings": self._search_learnings,
                "get_personality": self._get_personality,
                "get_current_time": self._get_current_time,
                "web_search": self._web_search,
                "add_schedule": self._add_schedule,
                "list_schedules": self._list_schedules,
                "list_recent_tasks": self._list_recent_tasks,
            }.get(tool_name)

            if handler:
                return await handler(args) if args else await handler({})
            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {"error": str(e)}

    # === 記憶検索 ===
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

    # === タスク作成 ===
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

    # === 組織状況 ===
    async def _get_org_status(self, args: dict = None) -> dict:
        if not self.org:
            return {"error": "Organization not available"}
        report = await self.org.get_org_report()
        return report.get("summary", {})

    # === 学習検索 ===
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

    # === 人格情報 ===
    async def _get_personality(self, args: dict = None) -> dict:
        if not self.personality:
            return {"error": "Personality not available"}
        profile = await self.personality.get_full_profile()
        return {
            "name": profile.get("identity", {}).get("name", "Cocoro"),
            "values": [v.get("value", "") for v in profile.get("values", [])[:5]],
            "beliefs": [b.get("belief", "") for b in profile.get("beliefs", [])[:5]],
        }

    # === 現在時刻 ===
    async def _get_current_time(self, args: dict = None) -> dict:
        now = datetime.now(JST)
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y年%m月%d日"),
            "time": now.strftime("%H:%M"),
            "weekday": ["月", "火", "水", "木", "金", "土", "日"][now.weekday()],
            "timezone": "JST (UTC+9)",
        }

    # === Web検索 ===
    async def _web_search(self, args: dict) -> dict:
        query = args.get("query", "")
        if not query:
            return {"error": "検索クエリが指定されていません"}

        try:
            # DuckDuckGo Instant Answer API (無料, キー不要)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                )
                data = resp.json()

            results = []
            # 要約
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": data["Abstract"][:300],
                    "url": data.get("AbstractURL", ""),
                })
            # 関連トピック
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "url": topic.get("FirstURL", ""),
                    })

            if not results:
                return {"query": query, "results": [],
                        "message": f"「{query}」に関する即時回答は見つかりませんでした。一般的な知識で回答してください。"}

            return {"query": query, "results": results, "count": len(results)}

        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return {"query": query, "error": str(e),
                    "message": "Web検索に失敗しました。一般的な知識で回答してください。"}

    # === スケジュール追加 ===
    async def _add_schedule(self, args: dict) -> dict:
        title = args.get("title", "")
        if not title:
            return {"error": "タイトルが指定されていません"}

        start_str = args.get("start_at", "")
        if not start_str:
            # デフォルト: 明日9時
            start = datetime.now(JST).replace(hour=9, minute=0, second=0) + timedelta(days=1)
        else:
            try:
                start = datetime.fromisoformat(start_str)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=JST)
            except ValueError:
                return {"error": f"日時の形式が不正です: {start_str}"}

        end_str = args.get("end_at", "")
        end = None
        if end_str:
            try:
                end = datetime.fromisoformat(end_str)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=JST)
            except ValueError:
                pass

        reminder = int(args.get("reminder_minutes", 30))

        row = await self.db.fetchrow(
            "INSERT INTO schedules (title, description, start_at, end_at, reminder_minutes) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id, title, start_at",
            title, args.get("description", ""), start, end, reminder)

        return {
            "id": str(row["id"]),
            "title": row["title"],
            "start_at": row["start_at"].isoformat(),
            "message": f"予定「{title}」を{start.strftime('%m/%d %H:%M')}に登録しました",
        }

    # === スケジュール一覧 ===
    async def _list_schedules(self, args: dict) -> dict:
        days = int(args.get("days", 7))
        now = datetime.now(JST)
        until = now + timedelta(days=days)

        rows = await self.db.fetch(
            "SELECT id, title, description, start_at, end_at, status "
            "FROM schedules WHERE start_at >= $1 AND start_at <= $2 AND status='active' "
            "ORDER BY start_at LIMIT 20",
            now, until)

        return {
            "schedules": [
                {"title": r["title"],
                 "start_at": r["start_at"].isoformat(),
                 "description": r.get("description", "")}
                for r in rows
            ],
            "count": len(rows),
            "period": f"{now.strftime('%m/%d')}〜{until.strftime('%m/%d')}",
        }

    # === タスク一覧 ===
    async def _list_recent_tasks(self, args: dict) -> dict:
        status = args.get("status", "all")
        if status and status != "all":
            rows = await self.db.fetch(
                "SELECT id, title, status, assigned_agent, created_at "
                "FROM tasks WHERE status=$1 ORDER BY created_at DESC LIMIT 10",
                status)
        else:
            rows = await self.db.fetch(
                "SELECT id, title, status, assigned_agent, created_at "
                "FROM tasks ORDER BY created_at DESC LIMIT 10")

        return {
            "tasks": [
                {"title": r["title"], "status": r["status"],
                 "agent": r["assigned_agent"],
                 "created_at": r["created_at"].isoformat()}
                for r in rows
            ],
            "count": len(rows),
        }
