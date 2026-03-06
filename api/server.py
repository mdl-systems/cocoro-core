"""
cocoro-core — API Server
Personality AI Operating System
"""
import os
import sys
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from infra.configs.settings import settings
from brain.llm_runtime import LLMRuntime, LLMError
from brain.reasoning.reasoning_engine import ReasoningEngine
from brain.decision_engine.decision_graph import DecisionGraph
from brain.planner.planner import Planner
from personality.personality_engine import PersonalityEngine
from memory.memory_engine import MemoryEngine
from agent.task_router.router import TaskRouter
from agent.worker_manager.manager import WorkerManager
from memory.consolidation import MemoryConsolidation
from personality.growth_tracker import GrowthTracker
from agent.webhook.notifier import WebhookNotifier
from agent.task_queue import TaskQueue
from agent.event_bus import EventBus
from agent.organization.manager import OrganizationManager
from brain.tools.tool_registry import ToolExecutor, TOOL_DEFINITIONS

class JsonFormatter(logging.Formatter):
    """JSON構造化ログフォーマッタ"""
    def format(self, record):
        import json as _json
        log = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log["error"] = self.formatException(record.exc_info)
        return _json.dumps(log, ensure_ascii=False)


log_format = os.getenv("LOG_FORMAT", "json")
if log_format == "json":
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(settings.LOG_LEVEL)
else:
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("cocoro")

# Globals
db_pool = None
llm = LLMRuntime()
personality = None
memory = None
reasoning = None
decision = None
planner = Planner()
router = TaskRouter()
worker = None
consolidation = None
growth = None
webhook = WebhookNotifier()
task_queue = None
event_bus = None
org = None
tools = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, personality, memory, reasoning, decision, worker, consolidation, growth, task_queue, event_bus, org, tools
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    personality = PersonalityEngine(db_pool)
    memory = MemoryEngine(db_pool, settings.REDIS_URL)
    reasoning = ReasoningEngine(personality, memory)
    decision = DecisionGraph(personality, memory)

    # Task Queue & Event Bus
    task_queue = TaskQueue(settings.REDIS_URL)
    event_bus = EventBus(settings.REDIS_URL)
    worker = WorkerManager(llm, router, db_pool, task_queue=task_queue, event_bus=event_bus)
    consolidation = MemoryConsolidation(memory, personality, llm)
    growth = GrowthTracker(db_pool)
    org = OrganizationManager(db_pool, event_bus)
    tools = ToolExecutor(memory=memory, worker=worker, org=org,
                         personality=personality, db=db_pool, router=router)

    # イベントハンドラ登録
    async def _on_task_completed(data):
        logger.info(f"Event: task completed — {data.get('task_id', '')[:8]}")
        await webhook.notify("task_completed", data)

    async def _on_task_failed(data):
        logger.warning(f"Event: task failed — {data.get('task_id', '')[:8]}")
        await webhook.notify_error("task_failed", data.get('error', 'unknown'))

    async def _on_task_done_track(data):
        agent = data.get('agent', 'dev')
        await org.record_task_completion(agent, 0, success=True)

    async def _on_task_fail_track(data):
        agent = data.get('agent', 'dev')
        await org.record_task_completion(agent, 0, success=False)

    event_bus.subscribe("task.completed", _on_task_completed)
    event_bus.subscribe("task.completed", _on_task_done_track)
    event_bus.subscribe("task.failed", _on_task_failed)
    event_bus.subscribe("task.failed", _on_task_fail_track)
    await event_bus.start_listener()

    # バックグラウンドWorker開始
    await worker.start_worker(num_workers=2)
    logger.info("Task workers: 2 started")

    # Consolidation定期実行スケジューラ
    scheduler_task = None
    interval_hours = int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "6"))
    if interval_hours > 0:
        scheduler_task = asyncio.create_task(_consolidation_scheduler(interval_hours))
        logger.info(f"Consolidation scheduler: every {interval_hours}h")

    logger.info("=== cocoro-core started ===")
    yield
    await event_bus.stop()
    if scheduler_task:
        scheduler_task.cancel()
    await db_pool.close()
    logger.info("=== cocoro-core stopped ===")


async def _consolidation_scheduler(interval_hours: int):
    """定期的に記憶定着を実行（人格の自動成長）"""
    await asyncio.sleep(60)  # 起動後1分待ってから開始
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            logger.info("[Scheduler] Consolidation starting...")
            result = await consolidation.consolidate()
            logger.info(f"[Scheduler] Consolidation done: {result.get('status', 'unknown')}")
            await webhook.notify_consolidation(result)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Consolidation failed: {e}")
            await webhook.notify_error("consolidation", str(e))


app = FastAPI(title="cocoro-core", version="1.0.0",
              description="Personality AI Operating System", lifespan=lifespan)


# === Auth ===
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """APIキー認証。COCORO_API_KEY未設定時は認証スキップ（開発用）"""
    api_key = settings.COCORO_API_KEY
    if not api_key:
        return  # キー未設定 = 認証なし（開発環境）
    if not credentials or credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


# === Health (認証不要) ===
@app.get("/health")
async def health():
    llm_status = await llm.health()
    return {"status": "ok", "version": "1.0.0", "llm": llm_status}


# === Chat (メイン対話) ===
class ChatReq(BaseModel):
    message: str
    session_id: str | None = None

class ChatRes(BaseModel):
    response: str
    session_id: str
    action: str = "chat"
    emotion: str = "neutral"
    task_id: str | None = None

@app.post("/chat", response_model=ChatRes)
async def chat(req: ChatReq, _=Depends(verify_api_key)):
    session_id = req.session_id or str(uuid.uuid4())

    try:
        # 1. 記憶に保存
        await memory.short.add_message(session_id, "user", req.message)
        await memory.long.save_message(session_id, "user", req.message, emotion="neutral")

        # 2. 入力を分類 (chat/think/decide/delegate/learn)
        classify_prompt = decision.build_classify_prompt(req.message)
        raw = await llm.generate(classify_prompt)
        classification = decision.parse_classification(raw)
        action = classification.get("action", "chat")
        emotion = classification.get("emotion", "neutral")
        logger.info(f"[{session_id[:8]}] action={action} emotion={emotion}")

        task_id = None

        if action == "think":
            think_prompt = await reasoning.build_reasoning_prompt(req.message)
            system_prompt = await personality.build_system_prompt()
            response = await llm.generate(think_prompt, system_prompt)
            result = reasoning.parse_reasoning(response)
            await reasoning.record_thought(req.message, result, session_id)
            response_text = result.get("conclusion", response)

        elif action == "decide":
            category = classification.get("category", "general")
            decide_prompt = await decision.build_decision_prompt(req.message, category)
            system_prompt = await personality.build_system_prompt()
            response = await llm.generate(decide_prompt, system_prompt)
            result = decision.parse_decision(response)
            await decision.record_decision(category, req.message, result)
            response_text = result.get("decision", response)

        elif action == "delegate":
            agent_type = classification.get("agent") or router.route(req.message)
            task_name = req.message[:80]
            row = await db_pool.fetchrow(
                "INSERT INTO tasks (title, description, assigned_agent) VALUES ($1,$2,$3) RETURNING id",
                task_name, req.message, agent_type)
            task_id = str(row["id"])
            result = await worker.execute(task_id, task_name, req.message, agent_type)
            response_text = result.get("output", result.get("error", "実行失敗"))

        elif action == "learn":
            await memory.long.save_learning("conversation", req.message, classification.get("category", "general"))
            await personality.apply_learning(req.message)
            response_text = f"学習しました: {req.message[:100]}"

        else:
            # Function Calling: AIがツールを呼ぶか判断
            system_prompt = await personality.build_system_prompt()
            context = await memory.build_context(session_id, req.message)
            full_prompt = f"{context}\n\n【ユーザー】\n{req.message}" if context else req.message

            fc_result = await llm.generate_with_tools(full_prompt, TOOL_DEFINITIONS, system_prompt)

            if fc_result["type"] == "function_call":
                # ツール実行
                tool_name = fc_result["name"]
                tool_args = fc_result["args"]
                tool_output = await tools.execute(tool_name, tool_args)

                # ツール結果をLLMに渡して最終応答を生成
                tool_prompt = (
                    f"{full_prompt}\n\n"
                    f"【ツール実行結果】\n"
                    f"ツール: {tool_name}\n"
                    f"結果: {str(tool_output)[:1000]}\n\n"
                    f"上記のツール結果を踏まえて、ユーザーに分かりやすく回答してください。"
                )
                response_text = await llm.generate(tool_prompt, system_prompt)
                logger.info(f"[{session_id[:8]}] Tool used: {tool_name}")
            else:
                response_text = fc_result["content"]

        # 3. 応答を記憶（感情付き）
        await memory.short.add_message(session_id, "cocoro", response_text)
        await memory.long.save_message(session_id, "cocoro", response_text, emotion=emotion)

        return ChatRes(response=response_text, session_id=session_id, action=action, emotion=emotion, task_id=task_id)

    except LLMError as e:
        logger.error(f"[{session_id[:8]}] LLM error: {e}")
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"[{session_id[:8]}] Chat error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Think (思考API) ===
class ThinkReq(BaseModel):
    question: str

@app.post("/think")
async def think(req: ThinkReq, _=Depends(verify_api_key)):
    try:
        prompt = await reasoning.build_reasoning_prompt(req.question)
        system_prompt = await personality.build_system_prompt()
        raw = await llm.generate(prompt, system_prompt)
        result = reasoning.parse_reasoning(raw)
        await reasoning.record_thought(req.question, result)
        return result
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"Think error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Decide (判断API) ===
class DecideReq(BaseModel):
    question: str
    category: str = "general"

@app.post("/decide")
async def decide(req: DecideReq, _=Depends(verify_api_key)):
    try:
        prompt = await decision.build_decision_prompt(req.question, req.category)
        system_prompt = await personality.build_system_prompt()
        raw = await llm.generate(prompt, system_prompt)
        result = decision.parse_decision(raw)
        await decision.record_decision(req.category, req.question, result)
        return result
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"Decide error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Identity ===
@app.get("/identity")
async def get_identity(_=Depends(verify_api_key)):
    return await personality.identity.get()

class IdentityUpdate(BaseModel):
    owner_name: str | None = None
    profile: str | None = None
    philosophy: str | None = None

@app.put("/identity")
async def update_identity(req: IdentityUpdate, _=Depends(verify_api_key)):
    return await personality.identity.update(**req.model_dump(exclude_none=True))


# === Values ===
@app.get("/values")
async def get_values(_=Depends(verify_api_key)):
    return {"values": await personality.values.get_all()}

class ValueReq(BaseModel):
    name: str
    description: str
    weight: float = 0.5
    category: str = "general"

@app.post("/values")
async def add_value(req: ValueReq, _=Depends(verify_api_key)):
    return await personality.values.add(req.name, req.description, req.weight, req.category)


# === Beliefs ===
@app.get("/beliefs")
async def get_beliefs(_=Depends(verify_api_key)):
    return {"beliefs": await personality.beliefs.get_all()}

class BeliefReq(BaseModel):
    statement: str
    confidence: float = 0.5

@app.post("/beliefs")
async def add_belief(req: BeliefReq, _=Depends(verify_api_key)):
    return await personality.beliefs.add(req.statement, req.confidence)


# === Memory ===
@app.get("/memory/decisions")
async def get_decisions(category: str = None, limit: int = 20, _=Depends(verify_api_key)):
    return {"decisions": await memory.long.get_past_decisions(category, limit)}

@app.get("/memory/learnings")
async def get_learnings(limit: int = 20, _=Depends(verify_api_key)):
    return {"learnings": await memory.long.get_learnings(limit)}


# === Decision Outcome（判断の振り返り） ===
class OutcomeReq(BaseModel):
    outcome: str  # success, failure, unknown
    reflection: str = ""

@app.put("/memory/decisions/{decision_id}/outcome")
async def record_outcome(decision_id: str, req: OutcomeReq, _=Depends(verify_api_key)):
    """過去の判断に結果と振り返りを記録"""
    try:
        # 1. 判断を更新
        row = await db_pool.fetchrow(
            "UPDATE decision_log SET outcome=$1, reflection=$2 WHERE id=$3::uuid "
            "RETURNING id, question, decision, outcome, reflection",
            req.outcome, req.reflection, decision_id)
        if not row:
            raise HTTPException(status_code=404, detail="判断が見つかりません")

        # 2. 学習として自動保存
        lesson = f"判断「{row['decision'][:60]}」の結果: {req.outcome}"
        if req.reflection:
            lesson += f" / 振り返り: {req.reflection[:100]}"
        await memory.long.save_learning(
            source="decision_reflection", lesson=lesson,
            category="decision", importance=7 if req.outcome == "failure" else 5,
            source_id=decision_id)

        logger.info(f"Decision {decision_id[:8]} outcome={req.outcome}")
        return {"status": "recorded", "decision": dict(row)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Outcome error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Tasks ===
class TaskReq(BaseModel):
    title: str
    description: str = ""
    priority: int = 5
    agent: str | None = None

@app.post("/task")
async def create_task(req: TaskReq, _=Depends(verify_api_key)):
    agent = req.agent or router.route(req.title, req.description)
    row = await db_pool.fetchrow(
        "INSERT INTO tasks (title, description, priority, assigned_agent) VALUES ($1,$2,$3,$4) RETURNING id,status",
        req.title, req.description, req.priority, agent)
    return {"id": str(row["id"]), "status": row["status"], "agent": agent}

@app.get("/tasks")
async def list_tasks(status: str = None, _=Depends(verify_api_key)):
    if status:
        rows = await db_pool.fetch("SELECT * FROM tasks WHERE status=$1 ORDER BY priority,created_at", status)
    else:
        rows = await db_pool.fetch("SELECT * FROM tasks ORDER BY priority,created_at LIMIT 50")
    return {"tasks": [dict(r) for r in rows]}

@app.post("/tasks/async")
async def create_async_task(req: TaskReq, _=Depends(verify_api_key)):
    """タスクをキューに投入して非同期実行"""
    try:
        task_id = await worker.execute_async(
            task_name=req.title,
            description=req.description,
            agent_type=req.agent,
            priority=req.priority,
        )
        return {"task_id": task_id, "status": "queued", "agent": req.agent or "auto"}
    except Exception as e:
        logger.error(f"Async task error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"タスク投入エラー: {type(e).__name__}")

@app.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, _=Depends(verify_api_key)):
    """タスク結果をポーリング取得"""
    # Redis（キュー結果）から確認
    result = await task_queue.get_result(task_id)
    if result:
        return {"task_id": task_id, **result}
    # DBから確認
    row = await db_pool.fetchrow("SELECT * FROM tasks WHERE id=$1::uuid", task_id)
    if not row:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")
    return {"task_id": task_id, "status": row["status"], "result": row.get("result"),
            "error": row.get("error"), "agent": row.get("assigned_agent")}

@app.get("/queue/status")
async def queue_status(_=Depends(verify_api_key)):
    """キュー状態を確認"""
    length = await task_queue.queue_length()
    return {"queue_length": length, "workers": 2}

# === Plan（タスク計画 + 実行） ===
class PlanReq(BaseModel):
    task: str
    description: str = ""
    execute: bool = False  # Trueなら計画後にそのまま実行

@app.post("/plan")
async def create_plan(req: PlanReq, _=Depends(verify_api_key)):
    """タスクを計画に分解し、オプションで実行"""
    try:
        # 1. 計画を生成
        plan_prompt = planner.build_plan_prompt(req.task, req.description)
        system_prompt = await personality.build_system_prompt()
        raw = await llm.generate(plan_prompt, system_prompt)
        plan = planner.parse_plan(raw)

        # 2. 実行しない場合は計画だけ返す
        if not req.execute:
            return {"status": "planned", "plan": plan}

        # 3. 実行：推奨Agentでタスク作成
        agent_type = plan.get("recommended_agent") or router.route(req.task)
        row = await db_pool.fetchrow(
            "INSERT INTO tasks (title, description, assigned_agent) VALUES ($1,$2,$3) RETURNING id",
            req.task[:80], req.description or req.task, agent_type)
        task_id = str(row["id"])

        # 4. Agent実行
        result = await worker.execute(task_id, req.task, req.description or req.task, agent_type)

        return {
            "status": "executed",
            "plan": plan,
            "task_id": task_id,
            "agent": agent_type,
            "result": result,
        }

    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"Plan error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Agents ===
@app.get("/agents")
async def list_agents(_=Depends(verify_api_key)):
    return {"agents": router.list_agents()}

# === Profile (全人格情報) ===
@app.get("/profile")
async def get_profile(_=Depends(verify_api_key)):
    return await personality.get_full_profile()


# === Consolidation (記憶定着 — GPTレビュー指摘) ===
@app.post("/consolidate")
async def consolidate_memories(session_id: str = None, _=Depends(verify_api_key)):
    """最近の経験を分析し、人格に反映する（記憶定着）"""
    try:
        result = await consolidation.consolidate(session_id)
        return result
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"Consolidation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Growth (成長追跡) ===
@app.get("/growth/report")
async def growth_report(_=Depends(verify_api_key)):
    """人格の成長レポート"""
    return await growth.get_growth_report()

@app.get("/growth/timeline")
async def growth_timeline(limit: int = 20, _=Depends(verify_api_key)):
    """人格進化のタイムライン"""
    return {"timeline": await growth.get_evolution_timeline(limit)}


# === v7: Organization (AI組織) ===
@app.get("/org/report")
async def org_report(_=Depends(verify_api_key)):
    """組織レポート"""
    return await org.get_org_report()

@app.get("/org/departments")
async def org_departments(_=Depends(verify_api_key)):
    """部門一覧"""
    return {"departments": await org.list_departments()}

@app.get("/org/agents")
async def org_agents(_=Depends(verify_api_key)):
    """Agent一覧（詳細）"""
    return {"agents": await org.list_agents()}

class AgentRegReq(BaseModel):
    agent_type: str
    display_name: str
    role: str = "worker"
    capabilities: list[str] = []
    department: str | None = None

@app.post("/org/agents/register")
async def register_agent(req: AgentRegReq, _=Depends(verify_api_key)):
    """新しいAgentを組織に登録"""
    try:
        agent = await org.register_agent(
            agent_type=req.agent_type, display_name=req.display_name,
            role=req.role, capabilities=req.capabilities,
            department=req.department)
        return {"status": "registered", "agent": agent}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class DelegateReq(BaseModel):
    task_id: str
    from_agent: str
    to_agent: str
    reason: str = ""

@app.post("/org/delegate")
async def delegate_task(req: DelegateReq, _=Depends(verify_api_key)):
    """タスクを別Agentに委任"""
    try:
        result = await org.delegate_task(
            task_id=req.task_id, from_agent=req.from_agent,
            to_agent=req.to_agent, reason=req.reason)
        return {"status": "delegated", "delegation": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
