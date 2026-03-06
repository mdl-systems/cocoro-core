"""cocoro-core — Worker Manager"""
import logging

logger = logging.getLogger("cocoro.agent.worker")


class WorkerManager:
    def __init__(self, llm, router, db):
        self.llm = llm
        self.router = router
        self.db = db

    async def execute(self, task_id: str, task_name: str, description: str,
                      agent_type: str = None) -> dict:
        agent_type = agent_type or self.router.route(task_name, description) or "dev"
        system_prompt = self.router.get_system_prompt(agent_type)

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
            logger.info(f"Task #{task_id}: done by {agent_type}")
            return {"status": "done", "output": result, "agent": agent_type}
        except Exception as e:
            await self.db.execute(
                "UPDATE tasks SET status='failed', error=$1 WHERE id=$2::uuid",
                str(e), task_id)
            logger.error(f"Task #{task_id}: failed — {e}")
            return {"status": "failed", "error": str(e), "agent": agent_type}
