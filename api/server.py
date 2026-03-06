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
    growth = GrowthTracker(db_pool)
    consolidation = MemoryConsolidation(memory, personality, llm, growth=growth)
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
        # Emotion Engine: 感情ラベル → 連続値パラメータ更新
        await personality.emotion.adjust(emotion)
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
            # Function Calling: マルチツール連鎖対応（最大3回）
            system_prompt = await personality.build_system_prompt()
            # Creative Friction: 高シンクロ時にAIの独立性を維持
            friction = await growth.get_creative_friction()
            if friction:
                system_prompt += friction
                logger.info(f"[{session_id[:8]}] Creative Friction Mode activated")
            context = await memory.build_context(session_id, req.message)
            full_prompt = f"{context}\n\n【ユーザー】\n{req.message}" if context else req.message

            MAX_TOOL_CALLS = 3
            tool_history = []
            current_prompt = full_prompt

            for step in range(MAX_TOOL_CALLS):
                fc_result = await llm.generate_with_tools(current_prompt, TOOL_DEFINITIONS, system_prompt)

                if fc_result["type"] != "function_call":
                    # テキスト応答 → ループ終了
                    response_text = fc_result["content"]
                    break

                # ツール実行
                tool_name = fc_result["name"]
                tool_args = fc_result["args"]
                tool_output = await tools.execute(tool_name, tool_args)
                tool_history.append({"tool": tool_name, "args": tool_args, "result": tool_output})
                logger.info(f"[{session_id[:8]}] Tool chain step {step+1}: {tool_name}")

                # ツール結果を蓄積してプロンプト更新
                history_text = "\n".join(
                    f"[ツール{i+1}] {h['tool']}: {str(h['result'])[:500]}"
                    for i, h in enumerate(tool_history)
                )
                current_prompt = (
                    f"{full_prompt}\n\n"
                    f"【実行済みツール結果】\n{history_text}\n\n"
                    f"上記のツール結果を踏まえて、追加のツールが必要なら呼び出し、"
                    f"不要なら日本語で分かりやすくユーザーに回答してください。"
                )
            else:
                # MAX回ツールを呼んだ → 最終応答を生成
                history_text = "\n".join(
                    f"[ツール{i+1}] {h['tool']}: {str(h['result'])[:500]}"
                    for i, h in enumerate(tool_history)
                )
                final_prompt = (
                    f"{full_prompt}\n\n"
                    f"【実行済みツール結果】\n{history_text}\n\n"
                    f"上記の全てのツール結果を踏まえて、ユーザーに分かりやすく回答してください。"
                )
                response_text = await llm.generate(final_prompt, system_prompt)

            if tool_history:
                tools_used = " → ".join(h["tool"] for h in tool_history)
                logger.info(f"[{session_id[:8]}] Tool chain: {tools_used} ({len(tool_history)} calls)")

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
    report = await growth.get_growth_report()
    # 感情状態も成長レポートに含める
    emotion_state = await personality.emotion.get_state()
    report["emotion"] = emotion_state.to_dict()
    return report

@app.get("/growth/timeline")
async def growth_timeline(limit: int = 20, _=Depends(verify_api_key)):
    """人格進化のタイムライン"""
    return {"timeline": await growth.get_evolution_timeline(limit)}


# === Emotion (感情エンジン) ===
@app.get("/emotion/state")
async def emotion_state(_=Depends(verify_api_key)):
    """現在の感情状態を取得"""
    state = await personality.emotion.get_state()
    return state.to_dict()

@app.get("/emotion/history")
async def emotion_history(limit: int = 20, _=Depends(verify_api_key)):
    """感情変化の履歴"""
    return {"history": await personality.emotion.get_history(limit)}

class EmotionAdjustReq(BaseModel):
    emotion_label: str
    intensity: float = 1.0

@app.post("/emotion/adjust")
async def emotion_adjust(req: EmotionAdjustReq, _=Depends(verify_api_key)):
    """手動で感情を調整"""
    return await personality.emotion.adjust(req.emotion_label, req.intensity)

@app.post("/emotion/decay")
async def emotion_decay(_=Depends(verify_api_key)):
    """感情を中立に向かって減衰させる"""
    return await personality.emotion.decay()


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


# === Schedules (スケジュール管理) ===
class ScheduleReq(BaseModel):
    title: str
    description: str = ""
    start_at: str  # ISO8601
    end_at: str | None = None
    reminder_minutes: int = 30

@app.get("/schedules")
async def list_schedules(days: int = 7, _=Depends(verify_api_key)):
    """今後のスケジュール一覧"""
    from datetime import datetime, timedelta, timezone
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    until = now + timedelta(days=days)
    rows = await db_pool.fetch(
        "SELECT * FROM schedules WHERE start_at >= $1 AND start_at <= $2 AND status='active' "
        "ORDER BY start_at", now, until)
    return {"schedules": [dict(r) for r in rows], "count": len(rows)}

@app.post("/schedules")
async def add_schedule(req: ScheduleReq, _=Depends(verify_api_key)):
    """スケジュール追加"""
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    start = datetime.fromisoformat(req.start_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=JST)
    end = None
    if req.end_at:
        end = datetime.fromisoformat(req.end_at)
        if end.tzinfo is None:
            end = end.replace(tzinfo=JST)
    row = await db_pool.fetchrow(
        "INSERT INTO schedules (title, description, start_at, end_at, reminder_minutes) "
        "VALUES ($1,$2,$3,$4,$5) RETURNING *",
        req.title, req.description, start, end, req.reminder_minutes)
    return {"status": "created", "schedule": dict(row)}

@app.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, _=Depends(verify_api_key)):
    """スケジュール削除"""
    await db_pool.execute(
        "UPDATE schedules SET status='cancelled' WHERE id=$1::uuid", schedule_id)
    return {"status": "cancelled", "id": schedule_id}


# === Sync Rate (シンクロ率) ===
@app.get("/growth/sync")
async def growth_sync(_=Depends(verify_api_key)):
    """現在のシンクロ率を算出"""
    return await growth.calculate_sync_rate()

@app.post("/growth/sync/record")
async def growth_sync_record(_=Depends(verify_api_key)):
    """シンクロ率を計算して履歴に保存"""
    return await growth.record_sync_rate(trigger="manual")

@app.get("/growth/sync/timeline")
async def growth_sync_timeline(limit: int = 30, _=Depends(verify_api_key)):
    """シンクロ率の推移"""
    return {"timeline": await growth.get_sync_rate_timeline(limit)}


# === Identity Import / Manifest (人格シード) ===
class IdentityImportReq(BaseModel):
    identity: dict | None = None  # {owner_name, profile, philosophy}
    ideal_values: dict | None = None  # {honesty: 0.8, ...}
    mbti: str | None = None  # "INTJ" etc.
    source: str = "web_diagnosis"

# MBTI → 理想価値観のマッピング
MBTI_VALUE_MAP = {
    "INTJ": {"logic": 0.9, "efficiency": 0.9, "growth": 0.8, "courage": 0.7, "honesty": 0.8, "empathy": 0.5},
    "INTP": {"logic": 0.95, "growth": 0.85, "honesty": 0.8, "efficiency": 0.7, "empathy": 0.4, "courage": 0.6},
    "ENTJ": {"efficiency": 0.95, "courage": 0.9, "logic": 0.85, "growth": 0.8, "honesty": 0.7, "empathy": 0.5},
    "ENTP": {"growth": 0.9, "courage": 0.85, "logic": 0.8, "efficiency": 0.7, "honesty": 0.7, "empathy": 0.6},
    "INFJ": {"empathy": 0.95, "honesty": 0.9, "growth": 0.85, "logic": 0.7, "courage": 0.6, "efficiency": 0.5},
    "INFP": {"empathy": 0.95, "honesty": 0.9, "growth": 0.8, "courage": 0.5, "logic": 0.6, "efficiency": 0.4},
    "ENFJ": {"empathy": 0.9, "courage": 0.85, "honesty": 0.8, "growth": 0.8, "efficiency": 0.7, "logic": 0.6},
    "ENFP": {"empathy": 0.85, "growth": 0.9, "courage": 0.8, "honesty": 0.75, "efficiency": 0.5, "logic": 0.55},
    "ISTJ": {"honesty": 0.95, "efficiency": 0.9, "logic": 0.85, "courage": 0.6, "empathy": 0.5, "growth": 0.6},
    "ISFJ": {"empathy": 0.9, "honesty": 0.9, "efficiency": 0.8, "logic": 0.6, "courage": 0.5, "growth": 0.6},
    "ESTJ": {"efficiency": 0.95, "honesty": 0.85, "logic": 0.8, "courage": 0.75, "empathy": 0.5, "growth": 0.6},
    "ESFJ": {"empathy": 0.9, "honesty": 0.85, "efficiency": 0.8, "courage": 0.6, "logic": 0.55, "growth": 0.6},
    "ISTP": {"logic": 0.9, "efficiency": 0.8, "courage": 0.75, "growth": 0.7, "honesty": 0.7, "empathy": 0.4},
    "ISFP": {"empathy": 0.85, "honesty": 0.8, "growth": 0.75, "courage": 0.6, "logic": 0.5, "efficiency": 0.5},
    "ESTP": {"courage": 0.9, "efficiency": 0.85, "logic": 0.7, "growth": 0.7, "honesty": 0.65, "empathy": 0.5},
    "ESFP": {"empathy": 0.85, "courage": 0.8, "growth": 0.75, "honesty": 0.7, "efficiency": 0.5, "logic": 0.5},
}

@app.post("/identity/import")
async def identity_import(req: IdentityImportReq, _=Depends(verify_api_key)):
    """人格シードをインポート（MBTI or 独自診断結果）"""
    import json as _json

    # 1. 既存データのバックアップ（History保存）
    current = await db_pool.fetchrow("SELECT * FROM identity LIMIT 1")
    if current:
        await db_pool.execute(
            "INSERT INTO life_history (event_type, title, description, impact_score) "
            "VALUES ('milestone', $1, $2, 8)",
            f"人格シードインポート (source: {req.source})",
            _json.dumps({"before": {"owner_name": current["owner_name"],
                                     "profile": current["profile"],
                                     "ideal_profile": str(current.get("ideal_profile", "{}"))
                                    }}, ensure_ascii=False))

    # 2. 理想価値観の解決
    ideal_values = req.ideal_values
    if not ideal_values and req.mbti:
        mbti_upper = req.mbti.upper()
        ideal_values = MBTI_VALUE_MAP.get(mbti_upper)
        if not ideal_values:
            raise HTTPException(status_code=400, detail=f"未対応のMBTI: {req.mbti}")

    # 3. ideal_profile を更新
    ideal_profile = {"ideal_values": ideal_values or {}, "source": req.source,
                     "mbti": req.mbti}
    await db_pool.execute(
        "UPDATE identity SET ideal_profile=$1 WHERE id=(SELECT id FROM identity LIMIT 1)",
        _json.dumps(ideal_profile))

    # 4. Identity 更新（任意）
    if req.identity:
        updates = []
        params = []
        i = 1
        for key in ("owner_name", "profile", "philosophy"):
            if key in req.identity:
                updates.append(f"{key}=${i}")
                params.append(req.identity[key])
                i += 1
        if updates:
            params.append(current["id"] if current else None)
            await db_pool.execute(
                f"UPDATE identity SET {','.join(updates)} WHERE id=${i}::uuid", *params)

    # 5. 初回シンクロ率を計算・記録
    sync = await growth.record_sync_rate(trigger="import")

    return {"status": "imported", "source": req.source, "mbti": req.mbti,
            "ideal_values": ideal_values, "sync_rate": sync["sync_rate"]}


@app.get("/identity/manifest")
async def identity_manifest(_=Depends(verify_api_key)):
    """匿名化された人格ベクトルを公開（v10: AI文明間の比較用）"""
    import hashlib
    # 価値観ベクトル
    rows = await db_pool.fetch("SELECT name, weight FROM values_system ORDER BY name")
    value_vector = {r["name"]: round(float(r["weight"]), 3) for r in rows}

    # 信念ダイジェスト
    beliefs = await db_pool.fetch("SELECT statement, confidence FROM beliefs ORDER BY confidence DESC LIMIT 5")
    belief_vector = [round(float(b["confidence"]), 2) for b in beliefs]

    # 匿名ID生成（identityのハッシュ）
    identity = await db_pool.fetchrow("SELECT owner_name FROM identity LIMIT 1")
    name = identity["owner_name"] if identity else "unknown"
    anon_id = hashlib.sha256(name.encode()).hexdigest()[:16]

    # シンクロ率
    sync = await growth.calculate_sync_rate()

    # Proof of History: 成長の軌跡（偽造防止）
    conv_count = await db_pool.fetchrow("SELECT COUNT(*) as c FROM conversation_log")
    dec_count = await db_pool.fetchrow("SELECT COUNT(*) as c FROM decision_log")
    learn_count = await db_pool.fetchrow("SELECT COUNT(*) as c FROM learning_log")
    first_msg = await db_pool.fetchrow("SELECT MIN(created_at) as t FROM conversation_log")

    # 成長ハッシュ: sync_rate_history の連鎖ハッシュ
    sync_rows = await db_pool.fetch(
        "SELECT sync_rate, created_at FROM sync_rate_history ORDER BY created_at")
    chain = ""
    for sr in sync_rows:
        chain += f"{sr['sync_rate']}:{sr['created_at'].isoformat()}"
    growth_hash = hashlib.sha256(chain.encode()).hexdigest()[:32] if chain else "none"

    # Hardware Binding (miniPC固有)
    hw_fingerprint = "unknown"
    try:
        import subprocess
        mid = subprocess.run(["cat", "/etc/machine-id"],
                            capture_output=True, text=True, timeout=2)
        if mid.returncode == 0:
            hw_fingerprint = hashlib.sha256(mid.stdout.strip().encode()).hexdigest()[:32]
    except Exception:
        pass

    return {
        "manifest_version": "2.0",
        "anonymous_id": anon_id,
        "value_vector": value_vector,
        "belief_strength": belief_vector,
        "dimensions": len(value_vector),
        "sync_rate": sync["sync_rate"],
        "proof_of_history": {
            "total_conversations": conv_count["c"] if conv_count else 0,
            "total_decisions": dec_count["c"] if dec_count else 0,
            "total_learnings": learn_count["c"] if learn_count else 0,
            "growth_hash": growth_hash,
            "first_boot": first_msg["t"].isoformat() if first_msg and first_msg["t"] else None,
        },
        "hardware_bound": hw_fingerprint != "unknown",
        "device_fingerprint": hw_fingerprint,
        "protocol": "cocoro-core/v10-compatible",
    }
