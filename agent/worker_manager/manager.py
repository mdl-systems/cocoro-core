"""cocoro-core — Worker Manager (v3: 非同期タスク実行)
バックグラウンドでキューからタスクを取り出し、適切なAgentに割り当てて実行。
結果をDB + EventBusに通知。
"""
import asyncio
import logging

logger = logging.getLogger("cocoro.agent.worker")


# === Agent専門プロンプト ===
AGENT_PROMPTS = {
    "dev": """あなたはDev Agent（開発専門AI）です。
あなたの専門:
- ソフトウェア設計・コードレビュー
- API設計・データベース設計
- バグ分析・デバッグ
- 技術的な問題解決

回答ルール:
- 具体的なコード例やコマンドを含める
- ベストプラクティスを意識する
- 実行可能な手順を示す""",

    "sales": """あなたはSales Agent（営業専門AI）です。
あなたの専門:
- 顧客対応・商談戦略
- 提案書・見積書の作成
- 競合分析・市場調査
- 売上予測・KPI分析

回答ルール:
- 数字と根拠を重視する
- 顧客の課題に焦点を当てる
- 具体的なアクションプランを提示する""",

    "marketing": """あなたはMarketing Agent（マーケティング専門AI）です。
あなたの専門:
- コンテンツ企画・SNS戦略
- 広告運用・SEO最適化
- ブランディング・PR
- データ分析・効果測定

回答ルール:
- ターゲット層を明確にする
- クリエイティブな提案を含める
- 効果測定の方法も提示する""",
}


class WorkerManager:
    """非同期Worker — キューからタスクを処理"""

    def __init__(self, llm, router, db, task_queue=None, event_bus=None):
        self.llm = llm
        self.router = router
        self.db = db
        self.task_queue = task_queue
        self.event_bus = event_bus
        self._worker_task = None

    def get_system_prompt(self, agent_type: str) -> str:
        """Agent専門プロンプトを取得"""
        return AGENT_PROMPTS.get(agent_type,
            "あなたは汎用AIアシスタントです。専門的かつ具体的に回答してください。")

    async def execute(self, task_id: str, task_name: str, description: str,
                      agent_type: str = None) -> dict:
        """タスクを同期実行（直接API呼び出し用）"""
        agent_type = agent_type or self.router.route(task_name) or "dev"
        system_prompt = self.get_system_prompt(agent_type)

        await self.db.execute(
            "UPDATE tasks SET status='running', assigned_agent=$1 WHERE id=$2::uuid",
            agent_type, task_id)

        try:
            result = await self.llm.generate(
                prompt=f"タスク: {task_name}\n詳細: {description}",
                system_prompt=system_prompt,
            )
            await self.db.execute(
                "UPDATE tasks SET status='done', result=$1 WHERE id=$2::uuid",
                result, task_id)
            logger.info(f"Task #{task_id[:8]}: done by {agent_type}")

            # イベント通知
            if self.event_bus:
                await self.event_bus.publish("task.completed", {
                    "task_id": task_id, "agent": agent_type, "status": "done"
                })

            return {"status": "done", "output": result, "agent": agent_type}
        except Exception as e:
            await self.db.execute(
                "UPDATE tasks SET status='failed', error=$1 WHERE id=$2::uuid",
                str(e), task_id)
            logger.error(f"Task #{task_id[:8]}: failed — {e}")

            if self.event_bus:
                await self.event_bus.publish("task.failed", {
                    "task_id": task_id, "agent": agent_type, "error": str(e)
                })

            return {"status": "failed", "error": str(e), "agent": agent_type}

    async def execute_async(self, task_name: str, description: str,
                            agent_type: str = None, priority: int = 5) -> str:
        """タスクをキューに投入（非同期実行）"""
        if not self.task_queue:
            raise RuntimeError("TaskQueue not configured")

        task_id = await self.task_queue.enqueue(
            task_type=agent_type or "auto",
            payload={"task_name": task_name, "description": description,
                     "agent_type": agent_type},
            priority=priority,
        )

        # DBにもタスク記録
        await self.db.execute(
            "INSERT INTO tasks (id, title, description, priority, status, assigned_agent) "
            "VALUES ($1::uuid, $2, $3, $4, 'queued', $5)",
            task_id, task_name[:80], description, priority,
            agent_type or "auto")

        return task_id

    async def start_worker(self, num_workers: int = 2):
        """バックグラウンドWorkerを開始"""
        if not self.task_queue:
            logger.warning("TaskQueue not configured, worker not started")
            return

        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            logger.info(f"Worker {i} started")

    async def _worker_loop(self, worker_name: str):
        """Workerループ — キューからタスクを取り出して実行"""
        logger.info(f"[{worker_name}] Starting...")
        while True:
            try:
                job = await self.task_queue.dequeue(timeout=5)
                if not job:
                    continue

                task_id = job["task_id"]
                payload = job["payload"]
                task_name = payload.get("task_name", "")
                description = payload.get("description", "")
                agent_type = payload.get("agent_type")

                logger.info(f"[{worker_name}] Processing: {task_name[:40]}")

                result = await self.execute(task_id, task_name, description, agent_type)

                # 結果をRedisにも保存（ポーリング用）
                await self.task_queue.set_result(task_id, result)

            except asyncio.CancelledError:
                logger.info(f"[{worker_name}] Stopped")
                break
            except Exception as e:
                logger.error(f"[{worker_name}] Error: {type(e).__name__}: {e}")
                await asyncio.sleep(1)
