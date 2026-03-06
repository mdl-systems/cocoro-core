"""
cocoro-core — API Server
Personality AI Operating System
"""
import os
import sys
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from infra.configs.settings import settings
from brain.llm_runtime import LLMRuntime
from brain.reasoning.reasoning_engine import ReasoningEngine
from brain.decision_engine.decision_graph import DecisionGraph
from brain.planner.planner import Planner
from personality.personality_engine import PersonalityEngine
from memory.memory_engine import MemoryEngine
from agent.task_router.router import TaskRouter
from agent.worker_manager.manager import WorkerManager
from memory.consolidation import MemoryConsolidation
from personality.growth_tracker import GrowthTracker

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, personality, memory, reasoning, decision, worker, consolidation, growth
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    personality = PersonalityEngine(db_pool)
    memory = MemoryEngine(db_pool, settings.REDIS_URL)
    reasoning = ReasoningEngine(personality, memory)
    decision = DecisionGraph(personality, memory)
    worker = WorkerManager(llm, router, db_pool)
    consolidation = MemoryConsolidation(memory, personality, llm)
    growth = GrowthTracker(db_pool)
    logger.info("=== cocoro-core started ===")
    yield
    await db_pool.close()
    logger.info("=== cocoro-core stopped ===")


app = FastAPI(title="cocoro-core", version="1.0.0",
              description="Personality AI Operating System", lifespan=lifespan)


# === Health ===
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
    task_id: str | None = None

@app.post("/chat", response_model=ChatRes)
async def chat(req: ChatReq):
    session_id = req.session_id or str(uuid.uuid4())

    # 1. 記憶に保存
    await memory.short.add_message(session_id, "user", req.message)
    await memory.long.save_message(session_id, "user", req.message)

    # 2. 入力を分類 (chat/think/decide/delegate/learn)
    classify_prompt = decision.build_classify_prompt(req.message)
    raw = await llm.generate(classify_prompt)
    classification = decision.parse_classification(raw)
    action = classification.get("action", "chat")
    logger.info(f"[{session_id[:8]}] action={action}")

    task_id = None

    if action == "think":
        # 深い思考
        think_prompt = await reasoning.build_reasoning_prompt(req.message)
        system_prompt = await personality.build_system_prompt()
        response = await llm.generate(think_prompt, system_prompt)
        result = reasoning.parse_reasoning(response)
        await reasoning.record_thought(req.message, result, session_id)
        response_text = result.get("conclusion", response)

    elif action == "decide":
        # 意思決定
        category = classification.get("category", "general")
        decide_prompt = await decision.build_decision_prompt(req.message, category)
        system_prompt = await personality.build_system_prompt()
        response = await llm.generate(decide_prompt, system_prompt)
        result = decision.parse_decision(response)
        await decision.record_decision(category, req.message, result)
        response_text = result.get("decision", response)

    elif action == "delegate":
        # Agent実行
        agent_type = classification.get("agent") or router.route(req.message)
        task_name = req.message[:80]
        row = await db_pool.fetchrow(
            "INSERT INTO tasks (title, description, assigned_agent) VALUES ($1,$2,$3) RETURNING id",
            task_name, req.message, agent_type)
        task_id = str(row["id"])
        result = await worker.execute(task_id, task_name, req.message, agent_type)
        response_text = result.get("output", result.get("error", "実行失敗"))

    elif action == "learn":
        # 学習記録
        await memory.long.save_learning("conversation", req.message, classification.get("category", "general"))
        await personality.apply_learning(req.message)
        response_text = f"学習しました: {req.message[:100]}"

    else:
        # 通常会話
        system_prompt = await personality.build_system_prompt()
        context = await memory.build_context(session_id, req.message)
        full_prompt = f"{context}\n\n【ユーザー】\n{req.message}" if context else req.message
        response_text = await llm.generate(full_prompt, system_prompt)

    # 3. 応答を記憶
    await memory.short.add_message(session_id, "cocoro", response_text)
    await memory.long.save_message(session_id, "cocoro", response_text)

    return ChatRes(response=response_text, session_id=session_id, action=action, task_id=task_id)


# === Think (思考API) ===
class ThinkReq(BaseModel):
    question: str

@app.post("/think")
async def think(req: ThinkReq):
    prompt = await reasoning.build_reasoning_prompt(req.question)
    system_prompt = await personality.build_system_prompt()
    raw = await llm.generate(prompt, system_prompt)
    result = reasoning.parse_reasoning(raw)
    await reasoning.record_thought(req.question, result)
    return result


# === Decide (判断API) ===
class DecideReq(BaseModel):
    question: str
    category: str = "general"

@app.post("/decide")
async def decide(req: DecideReq):
    prompt = await decision.build_decision_prompt(req.question, req.category)
    system_prompt = await personality.build_system_prompt()
    raw = await llm.generate(prompt, system_prompt)
    result = decision.parse_decision(raw)
    await decision.record_decision(req.category, req.question, result)
    return result


# === Identity ===
@app.get("/identity")
async def get_identity():
    return await personality.identity.get()

class IdentityUpdate(BaseModel):
    owner_name: str | None = None
    profile: str | None = None
    philosophy: str | None = None

@app.put("/identity")
async def update_identity(req: IdentityUpdate):
    return await personality.identity.update(**req.model_dump(exclude_none=True))


# === Values ===
@app.get("/values")
async def get_values():
    return {"values": await personality.values.get_all()}

class ValueReq(BaseModel):
    name: str
    description: str
    weight: float = 0.5
    category: str = "general"

@app.post("/values")
async def add_value(req: ValueReq):
    return await personality.values.add(req.name, req.description, req.weight, req.category)


# === Beliefs ===
@app.get("/beliefs")
async def get_beliefs():
    return {"beliefs": await personality.beliefs.get_all()}

class BeliefReq(BaseModel):
    statement: str
    confidence: float = 0.5

@app.post("/beliefs")
async def add_belief(req: BeliefReq):
    return await personality.beliefs.add(req.statement, req.confidence)


# === Memory ===
@app.get("/memory/decisions")
async def get_decisions(category: str = None, limit: int = 20):
    return {"decisions": await memory.long.get_past_decisions(category, limit)}

@app.get("/memory/learnings")
async def get_learnings(limit: int = 20):
    return {"learnings": await memory.long.get_learnings(limit)}


# === Tasks ===
class TaskReq(BaseModel):
    title: str
    description: str = ""
    priority: int = 5
    agent: str | None = None

@app.post("/task")
async def create_task(req: TaskReq):
    agent = req.agent or router.route(req.title, req.description)
    row = await db_pool.fetchrow(
        "INSERT INTO tasks (title, description, priority, assigned_agent) VALUES ($1,$2,$3,$4) RETURNING id,status",
        req.title, req.description, req.priority, agent)
    return {"id": str(row["id"]), "status": row["status"], "agent": agent}

@app.get("/tasks")
async def list_tasks(status: str = None):
    if status:
        rows = await db_pool.fetch("SELECT * FROM tasks WHERE status=$1 ORDER BY priority,created_at", status)
    else:
        rows = await db_pool.fetch("SELECT * FROM tasks ORDER BY priority,created_at LIMIT 50")
    return {"tasks": [dict(r) for r in rows]}


# === Agents ===
@app.get("/agents")
async def list_agents():
    return {"agents": router.list_agents()}

# === Profile (全人格情報) ===
@app.get("/profile")
async def get_profile():
    return await personality.get_full_profile()


# === Consolidation (記憶定着 — GPTレビュー指摘) ===
@app.post("/consolidate")
async def consolidate_memories(session_id: str = None):
    """最近の経験を分析し、人格に反映する（記憶定着）"""
    result = await consolidation.consolidate(session_id)
    return result


# === Growth (成長追跡) ===
@app.get("/growth/report")
async def growth_report():
    """人格の成長レポート"""
    return await growth.get_growth_report()

@app.get("/growth/timeline")
async def growth_timeline(limit: int = 20):
    """人格進化のタイムライン"""
    return {"timeline": await growth.get_evolution_timeline(limit)}
