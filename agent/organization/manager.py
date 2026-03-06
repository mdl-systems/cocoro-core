"""cocoro-core — Organization Manager (v7)
AI組織管理。部門・役職・Agent登録・業務委任・実績追跡。
"""
import logging
import time

logger = logging.getLogger("cocoro.organization")


class OrganizationManager:
    """AI組織の管理エンジン"""

    def __init__(self, db, event_bus=None):
        self.db = db
        self.event_bus = event_bus

    # === 部門管理 ===
    async def list_departments(self) -> list[dict]:
        """全部門と所属Agent数を取得"""
        rows = await self.db.fetch("""
            SELECT d.*, COUNT(a.id) as agent_count
            FROM departments d
            LEFT JOIN agent_registry a ON a.department_id = d.id
            GROUP BY d.id ORDER BY d.name
        """)
        return [dict(r) for r in rows]

    async def get_department(self, name: str) -> dict | None:
        row = await self.db.fetchrow(
            "SELECT * FROM departments WHERE name=$1", name)
        if not row:
            return None
        agents = await self.db.fetch(
            "SELECT * FROM agent_registry WHERE department_id=$1 ORDER BY role, agent_type",
            row["id"])
        return {**dict(row), "agents": [dict(a) for a in agents]}

    # === Agent管理 ===
    async def list_agents(self) -> list[dict]:
        """全登録Agent情報を取得"""
        rows = await self.db.fetch("""
            SELECT a.*, d.name as department_name
            FROM agent_registry a
            LEFT JOIN departments d ON a.department_id = d.id
            ORDER BY a.role, a.agent_type
        """)
        return [dict(r) for r in rows]

    async def get_agent(self, agent_type: str) -> dict | None:
        row = await self.db.fetchrow("""
            SELECT a.*, d.name as department_name
            FROM agent_registry a
            LEFT JOIN departments d ON a.department_id = d.id
            WHERE a.agent_type=$1
        """, agent_type)
        return dict(row) if row else None

    async def register_agent(self, agent_type: str, display_name: str,
                              role: str = "worker", capabilities: list[str] = None,
                              department: str = None) -> dict:
        """新しいAgentを登録"""
        dept_id = None
        if department:
            dept = await self.db.fetchrow(
                "SELECT id FROM departments WHERE name=$1", department)
            dept_id = dept["id"] if dept else None

        row = await self.db.fetchrow(
            "INSERT INTO agent_registry (agent_type, display_name, role, capabilities, department_id) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING *",
            agent_type, display_name, role, capabilities or [], dept_id)
        logger.info(f"Agent registered: {agent_type} ({role})")
        return dict(row)

    async def update_agent_status(self, agent_type: str, status: str):
        """Agentの稼働状態を更新"""
        await self.db.execute(
            "UPDATE agent_registry SET status=$1, last_active_at=NOW() WHERE agent_type=$2",
            status, agent_type)

    # === 実績追跡 ===
    async def record_task_completion(self, agent_type: str, response_time_ms: int,
                                      success: bool = True):
        """タスク完了を記録（実績更新）"""
        if success:
            await self.db.execute("""
                UPDATE agent_registry SET
                    tasks_completed = tasks_completed + 1,
                    avg_response_time_ms = (avg_response_time_ms * tasks_completed + $1) / (tasks_completed + 1),
                    last_active_at = NOW()
                WHERE agent_type = $2
            """, response_time_ms, agent_type)
        else:
            await self.db.execute("""
                UPDATE agent_registry SET
                    tasks_failed = tasks_failed + 1,
                    last_active_at = NOW()
                WHERE agent_type = $2
            """, agent_type)

    # === 業務委任 ===
    async def delegate_task(self, task_id: str, from_agent: str,
                             to_agent: str, reason: str = "") -> dict:
        """タスクを別のAgentに委任"""
        row = await self.db.fetchrow(
            "INSERT INTO task_delegations (task_id, from_agent, to_agent, reason) "
            "VALUES ($1::uuid, $2, $3, $4) RETURNING *",
            task_id, from_agent, to_agent, reason)

        # tasks テーブルも更新
        await self.db.execute(
            "UPDATE tasks SET assigned_agent=$1, status='queued' WHERE id=$2::uuid",
            to_agent, task_id)

        logger.info(f"Task {task_id[:8]} delegated: {from_agent} → {to_agent}")

        if self.event_bus:
            await self.event_bus.publish("task.delegated", {
                "task_id": task_id, "from": from_agent,
                "to": to_agent, "reason": reason
            })

        return dict(row)

    async def get_delegation_history(self, task_id: str) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT * FROM task_delegations WHERE task_id=$1::uuid ORDER BY created_at",
            task_id)
        return [dict(r) for r in rows]

    # === 最適Agent選定 ===
    async def find_best_agent(self, task_description: str,
                               required_capabilities: list[str] = None) -> str:
        """タスクに最適なAgentを選定（能力+実績ベース）"""
        query = """
            SELECT agent_type, display_name, role, capabilities,
                   tasks_completed, tasks_failed, avg_response_time_ms, status
            FROM agent_registry
            WHERE status = 'active'
            ORDER BY
                tasks_failed ASC,
                avg_response_time_ms ASC,
                tasks_completed DESC
        """
        agents = await self.db.fetch(query)

        if required_capabilities:
            # 必要な能力を持つAgentを優先
            for agent in agents:
                caps = agent["capabilities"] or []
                if any(cap in caps for cap in required_capabilities):
                    return agent["agent_type"]

        # フォールバック: 最もパフォーマンスの良いAgent
        if agents:
            return agents[0]["agent_type"]
        return "dev"

    # === 組織レポート ===
    async def get_org_report(self) -> dict:
        """組織全体のレポートを生成"""
        agents = await self.list_agents()
        departments = await self.list_departments()

        total_completed = sum(a.get("tasks_completed", 0) for a in agents)
        total_failed = sum(a.get("tasks_failed", 0) for a in agents)
        active_agents = sum(1 for a in agents if a.get("status") == "active")

        return {
            "summary": {
                "total_agents": len(agents),
                "active_agents": active_agents,
                "departments": len(departments),
                "total_tasks_completed": total_completed,
                "total_tasks_failed": total_failed,
                "success_rate": round(
                    total_completed / max(total_completed + total_failed, 1) * 100, 1),
            },
            "departments": departments,
            "agents": agents,
        }
