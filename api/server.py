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
from fastapi.middleware.cors import CORSMiddleware
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
from governance.governance_engine import GovernanceManager
from personality.setup.boot_wizard import BootWizard
from personality.test.decision_sampling import DecisionSamplingEngine
from personality.test.test_bench import PersonalityTestBench
from evolution.self_observation import SelfObservationEngine
from evolution.self_evaluation import SelfEvaluationEngine
from evolution.improvement import ImprovementEngine
from evolution.meta_cognition import MetaCognitionEngine
from evolution.value_scoring import ValueScoringEngine
from evolution.intelligence import IntelligenceExpansionEngine
from evolution.safety import SafetyLayer
from personality.cognitive_profile import CognitiveProfileEngine
from personality.calibration import PersonalityCalibrationEngine
from personality.clone_engine import PersonalityCloneEngine
from personality.emotion_adapter import EmotionBehaviorAdapter
from memory.memory_archiver import MemoryArchiver
from memory.user_memories import UserMemoryEngine
from brain.multimodal import MultimodalEngine
from brain.autonomous_thinker import AutonomousThinker
from personality.sync_engine import SyncRateEngine
from brain.tools.plugin_system import PluginRegistry, register_builtin_plugins
from brain.local_llm import LocalLLMManager
from personality.multi_user import MultiUserManager
from personality.peer_communication import PersonalityCommunication
from personality.voice_interface import VoiceInterface
from infra.migration import MigrationRunner
from brain.ollama_test import OllamaTestRunner
from agent.integrations import IntegrationManager
from personality.templates import PersonalityTemplateManager
from infra.monitoring import MonitoringManager
from infra.i18n import I18nManager
from personality.personality_vector import PersonalityVector
from personality.models.personality_profile import PersonalityProfile
from personality.animal_personality import list_animals
from personality.quick_questions import get_questions, apply_answers
from personality.personality_learning import PersonalityLearning
from compatibility.compatibility_engine import CompatibilityEngine

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
handlers = []

# コンソールハンドラ
console_handler = logging.StreamHandler()
if log_format == "json":
    console_handler.setFormatter(JsonFormatter())
else:
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
handlers.append(console_handler)

# A-6: ファイルログハンドラ (RotatingFileHandler)
if settings.LOG_FILE:
    try:
        from logging.handlers import RotatingFileHandler
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.LOG_FILE, maxBytes=50*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")

logging.root.handlers = handlers
logging.root.setLevel(settings.LOG_LEVEL)
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
governance = None
boot_wizard = None
sampling = None
test_bench = None
observer = None
evaluator = None
improver = None
meta_cognition = None
value_scoring = None
intelligence = None
safety = None
cognitive = None
calibration = None
clone_engine = None
migration_runner = None
emotion_adapter = None
memory_archiver = None
plugin_registry = None
local_llm = None
user_manager = None
peer_comm = None
voice = None
ollama_test = None
integrations = None
templates = None
monitoring = None
i18n = None
ws_connections: list = []
personality_profiles: dict = {}
personality_learning_engine = None
compat_engine = None
user_memories = None
multimodal: MultimodalEngine | None = None
auto_thinker: AutonomousThinker | None = None
sync_engine: SyncRateEngine | None = None
email_engine = None
audit_logger = None  # SecurityMiddlewareの監査ロガー


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, personality, memory, reasoning, decision, worker, consolidation, growth, task_queue, event_bus, org, tools, governance, boot_wizard, sampling, test_bench, observer, evaluator, improver, meta_cognition, value_scoring, intelligence, safety, cognitive, calibration, clone_engine, migration_runner, emotion_adapter, memory_archiver, plugin_registry, local_llm, user_manager, peer_comm, voice, ollama_test, integrations, templates, monitoring, i18n, personality_profiles, personality_learning_engine, compat_engine, user_memories, multimodal, auto_thinker, sync_engine, email_engine, audit_logger
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)

    # 監査ロガーをDBプールに接続
    from api.security_middleware import audit_logger as _audit_logger
    audit_logger = _audit_logger
    audit_logger.set_pool(db_pool)

    # A-5: 自動マイグレーション
    migration_runner = MigrationRunner(db_pool)
    try:
        migrate_result = await migration_runner.migrate()
        logger.info(f"Migration: {migrate_result.get('status', 'unknown')} (v{migrate_result.get('current_version', '?')})")
    except Exception as e:
        logger.warning(f"Migration warning: {e}")
    personality = PersonalityEngine(db_pool)
    memory = MemoryEngine(db_pool, settings.REDIS_URL)
    user_memories = UserMemoryEngine(db_pool)
    multimodal = MultimodalEngine()
    auto_thinker = AutonomousThinker(db_pool, llm, personality, memory)
    sync_engine = SyncRateEngine(db_pool, growth_tracker=growth)
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
    governance = GovernanceManager(db_pool)
    boot_wizard = BootWizard(db_pool, llm)
    sampling = DecisionSamplingEngine(db_pool)
    test_bench = PersonalityTestBench(db_pool, llm)
    observer = SelfObservationEngine(db_pool)
    evaluator = SelfEvaluationEngine(db_pool)
    improver = ImprovementEngine(db_pool, llm)
    meta_cognition = MetaCognitionEngine(db_pool, llm)
    value_scoring = ValueScoringEngine(db_pool, llm)
    intelligence = IntelligenceExpansionEngine(db_pool)
    safety = SafetyLayer(db_pool)
    cognitive = CognitiveProfileEngine(db_pool)
    calibration = PersonalityCalibrationEngine(db_pool, llm)
    clone_engine = PersonalityCloneEngine(db_pool)

    # C-6/C-7: 感情行動アダプター + 記憶アーカイバー
    emotion_adapter = EmotionBehaviorAdapter(personality)
    memory_archiver = MemoryArchiver(db_pool)

    # C-5: プラグインシステム
    plugin_registry = PluginRegistry()
    register_builtin_plugins(plugin_registry)

    # C-4: ローカルLLM管理
    local_llm = LocalLLMManager(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        default_model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
    )

    # C-2: マルチユーザー管理
    user_manager = MultiUserManager(db_pool)

    # C-3: 人格間コミュニケーション
    peer_comm = PersonalityCommunication("cocoro-main")

    # D-2: Ollama 実機テストランナー
    ollama_test = OllamaTestRunner(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
    )

    # D-3: Discord / LINE 連携
    integrations = IntegrationManager()

    # D-6: 人格テンプレート
    templates = PersonalityTemplateManager()

    # D-7: 監視・アラート
    monitoring = MonitoringManager()

    # D-8: 多言語対応
    i18n = I18nManager(default_lang=os.getenv("DEFAULT_LANG", "ja"))

    # 人格ベクトル32次元 + 相性エンジン
    personality_learning_engine = PersonalityLearning()
    compat_engine = CompatibilityEngine()

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

    # B-7: 統合スケジューラ（Consolidation + Emotion Decay + Sync Rate）
    scheduler_tasks = []
    interval_hours = int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "6"))
    if interval_hours > 0:
        scheduler_tasks.append(asyncio.create_task(
            _consolidation_scheduler(interval_hours)))
        logger.info(f"Scheduler: consolidation every {interval_hours}h")

    # 感情自動 decay（1時間ごと）
    decay_interval = int(os.getenv("EMOTION_DECAY_INTERVAL_HOURS", "1"))
    if decay_interval > 0:
        scheduler_tasks.append(asyncio.create_task(
            _emotion_decay_scheduler(decay_interval)))
        logger.info(f"Scheduler: emotion decay every {decay_interval}h")

    # シンクロ率定期記録（12時間ごと）
    sync_interval = int(os.getenv("SYNC_RECORD_INTERVAL_HOURS", "12"))
    if sync_interval > 0:
        scheduler_tasks.append(asyncio.create_task(
            _sync_rate_scheduler(sync_interval)))
        logger.info(f"Scheduler: sync rate record every {sync_interval}h")

    # 自己観察レポート（24時間ごと）
    observe_interval = int(os.getenv("OBSERVATION_REPORT_INTERVAL_HOURS", "24"))
    if observe_interval > 0:
        scheduler_tasks.append(asyncio.create_task(
            _observation_report_scheduler(observe_interval)))
        logger.info(f"Scheduler: observation report every {observe_interval}h")

    # メモリアーカイブ（24時間ごと）
    archive_interval = int(os.getenv("MEMORY_ARCHIVE_INTERVAL_HOURS", "24"))
    if archive_interval > 0:
        scheduler_tasks.append(asyncio.create_task(
            _memory_archive_scheduler(archive_interval)))
        logger.info(f"Scheduler: memory archive every {archive_interval}h")

    # 自律思考（1時間ごとデフォルト）
    think_interval = int(os.getenv("AUTO_THINK_INTERVAL_HOURS", "1"))
    if think_interval > 0 and auto_thinker is not None:
        scheduler_tasks.append(asyncio.create_task(
            auto_thinker.run_hourly_scheduler(think_interval)))
        logger.info(f"Scheduler: autonomous thinking every {think_interval}h")

    # ノード死活監視（30秒ごと）
    node_monitor_interval = int(os.getenv("NODE_MONITOR_INTERVAL_SECONDS", "30"))
    if node_monitor_interval > 0:
        scheduler_tasks.append(asyncio.create_task(
            _node_monitor_scheduler(db_pool, node_monitor_interval)))
        logger.info(f"Scheduler: node health monitor every {node_monitor_interval}s")

    # メール通知エンジン初期化 (Resend)
    try:
        from agent.email_engine import EmailEngine
        email_engine = EmailEngine(
            db_pool=db_pool,
            api_key=settings.RESEND_API_KEY,
            from_email=settings.FROM_EMAIL,
        )
        # デイリーブリーフィング（毎朝9時）
        daily_brief_hour = int(os.getenv("DAILY_BRIEF_HOUR", "9"))
        if daily_brief_hour >= 0:
            scheduler_tasks.append(asyncio.create_task(
                email_engine.run_daily_brief_scheduler(daily_brief_hour)))
            logger.info(f"Scheduler: daily brief at {daily_brief_hour}:00")
        logger.info(f"Email engine: initialized (enabled={settings.EMAIL_ENABLED})")
    except Exception as e:
        logger.warning(f"Email engine init failed: {e}")

    logger.info("=== cocoro-core started ===")
    yield
    await event_bus.stop()
    for t in scheduler_tasks:
        t.cancel()
    await db_pool.close()
    logger.info("=== cocoro-core stopped ===")


async def _node_monitor_scheduler(db_pool, interval_seconds: int = 30):
    """登録済みノードを定期的にpingして死活監視 — オフライン時はDBステータスを更新"""
    from api.routes.nodes import _ping_node, _update_status
    await asyncio.sleep(30)  # 起動30秒後から開始
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            if db_pool is None:
                continue
            rows = await db_pool.fetch("SELECT node_id, ip, port FROM cocoro_nodes")
            if not rows:
                continue

            async def _check_one(row):
                online = await _ping_node(row["ip"], row["port"], timeout=3.0)
                await _update_status(db_pool, row["node_id"], online)
                if not online:
                    logger.warning(
                        f"[NodeMonitor] {row['node_id']} ({row['ip']}:{row['port']}) is OFFLINE"
                    )
                return row["node_id"], online

            results = await asyncio.gather(*[_check_one(r) for r in rows], return_exceptions=True)
            online_count = sum(1 for r in results if isinstance(r, tuple) and r[1])
            logger.debug(
                f"[NodeMonitor] checked {len(rows)} nodes: {online_count} online"
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[NodeMonitor] Error: {e}")


async def _consolidation_scheduler(interval_hours: int):
    """定期的に記憶定着を実行（人格の自動成長）"""
    await asyncio.sleep(60)  # 起動後1分待ってから開始
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            logger.info("[Scheduler] Consolidation starting...")
            result = await consolidation.consolidate()
            logger.info(f"[Scheduler] Consolidation done: {result.get('status', 'unknown')}")
            _update_scheduler_state("consolidation", result.get("status", "unknown"))
            await webhook.notify_consolidation(result)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Consolidation failed: {e}")
            await webhook.notify_error("consolidation", str(e))


async def _emotion_decay_scheduler(interval_hours: int):
    """定期的に感情を自然減衰させる"""
    await asyncio.sleep(120)  # 起動2分後から
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            state = personality.emotion.get_state()
            if state.intensity > 0.05:
                personality.emotion.decay()
                new_state = personality.emotion.get_state()
                logger.info(f"[Scheduler] Emotion decay: {state.dominant}({state.intensity:.2f}) → {new_state.dominant}({new_state.intensity:.2f})")
                _update_scheduler_state("emotion_decay", f"{state.dominant}→{new_state.dominant}")
                await webhook.notify("emotion_decay", {
                    "summary": f"感情自然減衰: {state.dominant} → {new_state.dominant}",
                    "before_intensity": round(state.intensity, 3),
                    "after_intensity": round(new_state.intensity, 3),
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Emotion decay failed: {e}")


async def _sync_rate_scheduler(interval_hours: int):
    """定期的にシンクロ率を記録"""
    await asyncio.sleep(180)  # 起動3分後から
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            sync_data = await growth.calculate_sync_rate()
            await growth.record_sync_rate(sync_data.get("sync_rate", 0))
            logger.info(f"[Scheduler] Sync rate recorded: {sync_data.get('sync_rate', 0):.1f}%")
            _update_scheduler_state("sync_rate", f"{sync_data.get('sync_rate', 0):.1f}%")
            await webhook.notify("sync_rate", {
                "summary": f"シンクロ率記録: {sync_data.get('sync_rate', 0):.1f}%",
                "sync_rate": sync_data.get("sync_rate", 0),
            })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Sync rate recording failed: {e}")


async def _observation_report_scheduler(interval_hours: int):
    """定期的に自己観察レポートをWebhookに送信"""
    await asyncio.sleep(300)  # 起動5分後から
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            stats = await observer.get_stats()
            total = stats.get("total_observations", 0)
            if total > 0:
                await webhook.notify("observation_report", {
                    "summary": f"自己観察レポート: {total}件の観察",
                    "total": total,
                    "by_type": stats.get("by_type", {}),
                })
                logger.info(f"[Scheduler] Observation report sent: {total} observations")
                _update_scheduler_state("observation", f"{total} observations")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Observation report failed: {e}")


async def _memory_archive_scheduler(interval_hours: int):
    """定期的に古い記憶を自動アーカイブ"""
    await asyncio.sleep(600)  # 起動10分後から
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            logger.info("[Scheduler] Memory archive starting...")
            result = await memory_archiver.run_full_archive()
            archived = result.get("archived", 0) if isinstance(result, dict) else 0
            logger.info(f"[Scheduler] Memory archive done: {archived} records archived")
            _update_scheduler_state("memory_archive", f"{archived} archived")
            await webhook.notify("memory_archive", {
                "summary": f"メモリアーカイブ完了: {archived}件整理",
                "archived": archived,
            })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Scheduler] Memory archive failed: {e}")

import time as _time

# === OpenAPI タグ定義 ===
OPENAPI_TAGS = [
    {"name": "health",      "description": "ヘルスチェック・システム状態"},
    {"name": "chat",        "description": "会話・チャットストリーミング"},
    {"name": "setup",       "description": "Boot Wizard・初期設定"},
    {"name": "memory",      "description": "記憶管理（短期・長期・ベクトル）"},
    {"name": "emotion",     "description": "感情状態・感情履歴"},
    {"name": "sync",        "description": "シンクロ率（ユーザー↔AI一致度）"},
    {"name": "think",       "description": "自律思考・デイリーブリーフィング"},
    {"name": "personality", "description": "人格・価値観・信念・目標"},
    {"name": "growth",      "description": "成長トラッカー・シンクロ率履歴"},
    {"name": "agent",       "description": "エージェントロール・タスク実行"},
    {"name": "node",        "description": "分散ノード登録・ヘルス確認"},
    {"name": "voice",       "description": "音声転写・スクリーンコンテキスト分析"},
    {"name": "admin",       "description": "管理者操作（メモリリセット等）"},
    {"name": "debug",       "description": "デバッグ・システム内部確認"},
    {"name": "scheduler",   "description": "スケジューラ管理・手動トリガー"},
]

OPENAPI_DESCRIPTION = """
# cocoro-core API

**Personality AI Operating System** のコアエンジン REST API です。

## 認証

すべてのエンドポイント（`/health` を除く）は **Bearer Token** 認証が必要です:

```
Authorization: Bearer <COCORO_API_KEY>
```

Swagger UI の **🔒 Authorize** ボタンからトークンを設定できます。

## アーキテクチャ（11層構造）

| Layer | 役割 |
|-------|------|
| Memory | 短期(Redis) / 長期(PostgreSQL) / ベクトル(pgvector) |
| Values | 価値観ベクトル + 理想との余弦類似度 |
| Emotion | 6次元感情モデル (happiness / sadness / anger / fear / trust / surprise) |
| Decision | Reasoning → Values → Emotion → Decision の順序付きパイプライン |
| Sync Rate | ユーザー↔AI シンクロ率 (0–100%, Divergence Ceiling=92%) |

## シンクロ率の学習制御

| シンクロ率 | 学習率 |
|---|---|
| < 70% | 加速 (1.5x) |
| 70–85% | 通常 (1.0x) |
| 85–92% | 減速 (0.3x / Creative Friction) |
| > 92% | 停止 (Divergence Ceiling) |
"""

app = FastAPI(
    title="cocoro-core",
    version="1.0.0",
    description=OPENAPI_DESCRIPTION,
    summary="Personality AI Operating System — Core API",
    contact={
        "name": "MDL Systems",
        "url": "https://github.com/mdl-systems/cocoro-core",
    },
    license_info={
        "name": "AGPL-3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
    },
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
        "filter": True,
        "tagsSorter": "alpha",
    },
    lifespan=lifespan,
)

# Swagger UI に Bearer 認証ボタンを追加
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "COCORO_API_KEY を入力してください",
        }
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi  # type: ignore

# アプリ起動時刻を記録（uptime計算用）
_APP_START_TIME = _time.time()

# === A-4: CORS Middleware ===
cors_origins = settings.CORS_ORIGINS
if cors_origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === D-10: Security Middleware ===
from api.security import SecurityMiddleware, ip_filter, login_throttle, rate_limiter
from api.routes.agent_roles import router as agent_roles_router, get_role_system_prompt
from api.routes.nodes import router as nodes_router, find_node_for_role, forward_to_node, forward_task_to_agent
from api.routes.public import router as public_router
from api.routes.admin_keys import router as admin_keys_router
from api.routes.notify import router as notify_router
from api.routes.language_settings import router as language_settings_router
from api.routes.admin_security import router as admin_security_router

app.include_router(agent_roles_router)
app.include_router(nodes_router)
app.include_router(public_router)
app.include_router(admin_keys_router)
app.include_router(notify_router)
app.include_router(language_settings_router)
app.include_router(admin_security_router)

# SecurityMiddleware (監査ログ + IPフィルタ) — api.security_middleware
from api.security_middleware import (
    SecurityMiddleware as AuditSecurityMiddleware,
    audit_logger as _sec_audit_logger,
    RATE_LIMITING_AVAILABLE, limiter, get_ratelimit_handler,
    get_client_ip,
)
if settings.ENABLE_IP_FILTER or settings.AUDIT_LOG_ENABLED:
    app.add_middleware(
        AuditSecurityMiddleware,
        audit_logger=_sec_audit_logger,
        enable_ip_filter=settings.ENABLE_IP_FILTER,
    )
    logger.info(f"SecurityMiddleware(audit) enabled: ip_filter={settings.ENABLE_IP_FILTER} audit={settings.AUDIT_LOG_ENABLED}")

# slowapi レートリミッター
if RATE_LIMITING_AVAILABLE and settings.RATE_LIMIT_ENABLED:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("slowapi rate limiting enabled")

# IP Filter 設定
ip_filter.configure(
    whitelist_csv=settings.IP_WHITELIST,
    blacklist_csv=settings.IP_BLACKLIST,
)

# Login Throttle 設定
login_throttle.max_failures = settings.LOGIN_MAX_FAILURES
login_throttle.lockout_seconds = settings.LOGIN_LOCKOUT_SECONDS

# SecurityMiddleware (HTTPS強制 + Rate Limit + Security Headers) — api.security
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(SecurityMiddleware, force_https=settings.FORCE_HTTPS)
    logger.info(f"SecurityMiddleware(https) enabled (HTTPS={settings.FORCE_HTTPS}, IP whitelist={bool(settings.IP_WHITELIST)})")


from fastapi.responses import JSONResponse
import traceback as _tb

@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """LLM系エラー → 503"""
    logger.error(f"LLM error on {request.url.path}: {exc}")
    return JSONResponse(status_code=503, content={
        "error": f"AI応答エラー: {exc}",
        "type": "llm_error",
        "path": str(request.url.path),
    })

@app.exception_handler(asyncpg.PostgresError)
async def db_error_handler(request: Request, exc: asyncpg.PostgresError):
    """DB系エラー → 503"""
    logger.error(f"DB error on {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=503, content={
        "error": f"データベースエラー: {type(exc).__name__}",
        "type": "db_error",
        "path": str(request.url.path),
    })

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    """未処理例外 → 500 JSON（HTML 500を防止）"""
    logger.error(f"Unhandled error on {request.url.path}: {type(exc).__name__}: {exc}\n{_tb.format_exc()}")
    return JSONResponse(status_code=500, content={
        "error": f"内部エラー: {type(exc).__name__}",
        "type": "internal_error",
        "path": str(request.url.path),
    })


# === Auth (A-4: JWT + API Key デュアル認証) ===
security = HTTPBearer(auto_error=False)


def _verify_jwt(token: str) -> dict | None:
    """JWT トークンを検証。成功時は payload を返す。失敗時は None。"""
    if not settings.JWT_SECRET:
        return None  # JWT未設定
    try:
        import hashlib, hmac, base64, json as _json, time
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # HS256 署名検証
        signing_input = f"{parts[0]}.{parts[1]}".encode()
        signature = hmac.new(settings.JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
        # base64url decode
        def b64_decode(s):
            s += "=" * (4 - len(s) % 4)
            return base64.urlsafe_b64decode(s)
        if not hmac.compare_digest(signature, b64_decode(parts[2])):
            return None
        payload = _json.loads(b64_decode(parts[1]))
        # 有効期限チェック
        if payload.get("exp") and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """認証: JWT → API Key → 未設定時スキップ（開発用）"""
    if not credentials:
        # 認証情報なし: キー未設定なら通過
        if not settings.COCORO_API_KEY and not settings.JWT_SECRET:
            return
        raise HTTPException(status_code=401, detail="認証が必要です")

    token = credentials.credentials

    # 1. JWT認証を試行
    if settings.JWT_SECRET:
        payload = _verify_jwt(token)
        if payload:
            return payload  # JWT認証成功 → payloadを返す

    # 2. API Key認証にフォールバック
    if settings.COCORO_API_KEY and token == settings.COCORO_API_KEY:
        return  # API Key認証成功

    # 3. 両方未設定なら通過（開発環境）
    if not settings.COCORO_API_KEY and not settings.JWT_SECRET:
        return

    raise HTTPException(status_code=401, detail="無効な認証トークンです")


# === JWT Token 発行エンドポイント ===
# SDKは POST /auth/token に X-API-Key ヘッダーで送信し、
# レスポンスの access_token を Bearer トークンとして使う。
# JWT_SECRET が未設定の場合は API Key 自体をトークンとして返す
# （verify_api_key が Bearer <COCORO_API_KEY> を受け付けるため動作する）

@app.post("/auth/token")
async def issue_token(request: Request):
    """API Key を検証してトークンを発行（SDK互換）

    入力: X-API-Key ヘッダー or JSON body {"api_key": "..."}
    出力: {"access_token": "...", "token_type": "bearer", "expires_in": 3600}
    """
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown").split(",")[0].strip()

    # API Key を取得（X-API-Key ヘッダー優先 / body fallback）
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        try:
            body = await request.json()
            api_key = body.get("api_key", "")
        except Exception:
            pass

    # API Key 検証
    if settings.COCORO_API_KEY and api_key != settings.COCORO_API_KEY:
        login_throttle.record_failure(client_ip)
        logger.warning(f"Auth failure from {client_ip}")
        raise HTTPException(status_code=401, detail="無効なAPI Key")

    login_throttle.record_success(client_ip)

    # JWT_SECRET が設定されていれば JWT を発行、なければ API Key をそのまま返す
    if settings.JWT_SECRET:
        import hashlib, hmac, base64, json as _json, time
        now = int(time.time())
        payload = {"sub": "cocoro", "iat": now, "exp": now + settings.JWT_EXPIRE_HOURS * 3600}
        def b64_encode(data):
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        header = b64_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = b64_encode(_json.dumps(payload).encode())
        signing_input = f"{header}.{body}".encode()
        signature = b64_encode(hmac.new(settings.JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
        token = f"{header}.{body}.{signature}"
        expires_in = settings.JWT_EXPIRE_HOURS * 3600
    else:
        # JWT_SECRET未設定: API Key をそのまま Bearer トークンとして返す
        # verify_api_key は Bearer <COCORO_API_KEY> を受け付けるため機能する
        token = api_key or settings.COCORO_API_KEY
        expires_in = 3600

    return {
        "access_token": token,   # SDK が期待するフィールド名
        "token": token,          # 後方互換
        "token_type": "bearer",
        "expires_in": expires_in,
    }


# === D-10: Security Management API ===
@app.get("/security/status")
async def security_status(_=Depends(verify_api_key)):
    """セキュリティ状況"""
    return {
        "rate_limiting": settings.RATE_LIMIT_ENABLED,
        "force_https": settings.FORCE_HTTPS,
        "ip_filter": ip_filter.get_config(),
        "login_throttle": login_throttle.get_stats(),
        "auth_mode": "jwt+apikey" if settings.JWT_SECRET else ("apikey" if settings.COCORO_API_KEY else "open"),
    }


# === D-5: Scheduler Management API ===
_scheduler_state = {
    "consolidation": {"last_run": None, "next_run": None, "run_count": 0, "last_status": None,
                      "interval_hours": int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "6"))},
    "emotion_decay": {"last_run": None, "next_run": None, "run_count": 0, "last_status": None,
                      "interval_hours": int(os.getenv("EMOTION_DECAY_INTERVAL_HOURS", "1"))},
    "sync_rate": {"last_run": None, "next_run": None, "run_count": 0, "last_status": None,
                  "interval_hours": int(os.getenv("SYNC_RECORD_INTERVAL_HOURS", "12"))},
    "observation": {"last_run": None, "next_run": None, "run_count": 0, "last_status": None,
                    "interval_hours": int(os.getenv("OBSERVATION_REPORT_INTERVAL_HOURS", "24"))},
    "memory_archive": {"last_run": None, "next_run": None, "run_count": 0, "last_status": None,
                       "interval_hours": int(os.getenv("MEMORY_ARCHIVE_INTERVAL_HOURS", "24"))},
}


def _update_scheduler_state(name: str, status: str):
    """スケジューラー実行記録を更新"""
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    _scheduler_state[name]["last_run"] = now.isoformat()
    _scheduler_state[name]["run_count"] += 1
    _scheduler_state[name]["last_status"] = status
    interval = _scheduler_state[name]["interval_hours"]
    _scheduler_state[name]["next_run"] = (now + timedelta(hours=interval)).isoformat()


@app.get("/scheduler/status")
async def scheduler_status(_=Depends(verify_api_key)):
    """全スケジューラーの稼働状況"""
    return {
        "schedulers": _scheduler_state,
        "total_active": sum(1 for s in _scheduler_state.values() if s["interval_hours"] > 0),
    }


@app.post("/scheduler/trigger/{name}")
async def scheduler_trigger(name: str, _=Depends(verify_api_key)):
    """スケジューラーを手動トリガー"""
    if name == "consolidation":
        result = await consolidation.consolidate()
        _update_scheduler_state("consolidation", result.get("status", "unknown"))
        return {"triggered": "consolidation", "result": result}
    elif name == "emotion_decay":
        personality.emotion.decay()
        _update_scheduler_state("emotion_decay", "decayed")
        return {"triggered": "emotion_decay", "status": "decayed"}
    elif name == "sync_rate":
        sync = await growth.calculate_sync_rate()
        await growth.record_sync_rate(sync.get("sync_rate", 0))
        _update_scheduler_state("sync_rate", f"{sync.get('sync_rate', 0):.1f}%")
        return {"triggered": "sync_rate", "sync_rate": sync}
    elif name == "memory_archive":
        result = await memory_archiver.run_full_archive()
        _update_scheduler_state("memory_archive", "archived")
        return {"triggered": "memory_archive", "result": result}
    else:
        raise HTTPException(status_code=404, detail=f"Unknown scheduler: {name}")



# === Health (認証不要) ===
@app.get(
    "/health",
    tags=["health"],
    summary="ヘルスチェック",
    response_description="システムの状態・バージョン・各サービスの接続状況",
    responses={
        200: {"description": "正常稼働中"},
        503: {"description": "サービス利用不可"},
    },
)
async def health():
    """システムヘルスチェックエンドポイント。

    PostgreSQL / Redis / LLM の接続状態と、
    サーバー起動からの経過秒数（uptime）を返します。
    このエンドポイントは認証不要でアクセスできます。
    """
    # LLM ステータス
    try:
        llm_status = await llm.health()
        llm_ok = "ok"
        llm_model = llm_status.get("model", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
    except Exception:
        llm_ok = "error"
        llm_model = os.getenv("GEMINI_MODEL", "unknown")

    # PostgreSQL ステータス
    pg_status = "unknown"
    try:
        if db_pool:
            await db_pool.fetchval("SELECT 1")
            pg_status = "connected"
        else:
            pg_status = "not_initialized"
    except Exception:
        pg_status = "error"

    # Redis ステータス（メモリエンジン経由）
    redis_status = "unknown"
    try:
        if memory and hasattr(memory, 'short') and hasattr(memory.short, 'redis'):
            r = memory.short.redis
            if r:
                await r.ping()
                redis_status = "connected"
            else:
                redis_status = "not_initialized"
        else:
            redis_status = "not_initialized"
    except Exception:
        redis_status = "unavailable"

    # エンドポイント数 (routes数)
    endpoints_count = sum(
        1 for r in app.routes
        if hasattr(r, "methods") and r.methods  # type: ignore
    )

    uptime_seconds = int(_time.time() - _APP_START_TIME)

    return {
        "status": "healthy" if (pg_status == "connected" and llm_ok == "ok") else "degraded",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "services": {
            "postgres": pg_status,
            "redis": redis_status,
            "llm": f"{llm_ok} ({llm_model})",
        },
        "endpoints_count": endpoints_count,
        # Cloudflare Tunnel 情報
        "tunnel_enabled": settings.TUNNEL_ENABLED,
        "tunnel_url": settings.TUNNEL_URL if settings.TUNNEL_ENABLED else None,
        "local_url": settings.LOCAL_URL,
    }


@app.post("/admin/reset-memory")
async def reset_memory(_=Depends(verify_api_key)):
    """全メモリテーブルをTRUNCATE（田中太郎問題など汚染データを完全クリア）
    人格データ（identity/values_system/beliefs/goals）は保持する。
    """
    tables = [
        "conversation_log", "thought_log", "decision_log",
        "learning_log", "knowledge_store", "knowledge_base",
        "self_observations", "improvement_plans", "emotion_history",
        "sync_rate_history", "tool_usage_log", "tasks",
        "task_delegations", "governance_log", "skills",
    ]
    truncated = []
    errors = []
    for tbl in tables:
        try:
            await db_pool.execute(f"TRUNCATE TABLE {tbl} CASCADE")
            truncated.append(tbl)
        except Exception as e:
            errors.append({"table": tbl, "error": str(e)})

    # emotion_state を初期値にリセット
    try:
        await db_pool.execute(
            """UPDATE emotion_state SET
               happiness=0.5, sadness=0.1, anger=0.0, fear=0.1,
               trust=0.6, surprise=0.2, dominant_emotion='neutral',
               updated_at=NOW()"""
        )
    except Exception as e:
        errors.append({"table": "emotion_state", "error": str(e)})

    logger.info(f"Admin: reset-memory executed. truncated={truncated}")
    return {
        "status": "ok",
        "truncated": truncated,
        "errors": errors,
        "message": "メモリテーブルをリセットしました。人格データは保持されています。",
    }


@app.get("/debug/system-prompt")
async def debug_system_prompt(_=Depends(verify_api_key)):
    """デバッグ用: LLMに渡すシステムプロンプトを返す（田中太郎問題調査用）"""
    system_prompt = await personality.build_system_prompt()
    identity_data = await personality.identity.get()
    return {
        "identity_in_db": {
            "owner_name": identity_data.get("owner_name"),
            "profile":    identity_data.get("profile", "")[:100],
        },
        "system_prompt": system_prompt,
        "system_prompt_length": len(system_prompt),
    }



class ChatReq(BaseModel):
    message: str
    session_id: str | None = None
    role_id: str | None = None  # 専門職エージェントロールID（例: "lawyer", "engineer"）

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

        # Governance: 入力の倫理チェック
        gov_check = await governance.check_input(req.message)
        if not gov_check.passed:
            logger.warning(f"[{session_id[:8]}] Governance blocked input: {gov_check.reason}")
            return ChatRes(response=gov_check.suggestion or "そのリクエストにはお応えできません。",
                           session_id=session_id, action="blocked", emotion="neutral", task_id=None)

        # 2. 入力を分類 (chat/think/decide/delegate/learn)
        classify_prompt = decision.build_classify_prompt(req.message)
        raw = await llm.generate(classify_prompt)
        classification = decision.parse_classification(raw)
        action = classification.get("action", "chat")
        emotion = classification.get("emotion", "neutral")
        # Emotion Engine: 感情ラベル → 連続値パラメータ更新
        await personality.emotion.adjust(emotion)
        # 感情キャッシュをクリア → build_system_prompt で最新状態を使う
        personality.emotion._cache = None
        logger.info(f"[{session_id[:8]}] action={action} emotion={emotion}")

        # 現在の感情状態を取得（応答メタデータ用）
        emotion_state = await personality.emotion.get_state()
        dominant_emotion = emotion_state.dominant()

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
        await memory.long.save_message(session_id, "cocoro", response_text, emotion=dominant_emotion)

        # 4. 自己観察: 会話を記録
        try:
            await observer.observe_conversation(session_id, req.message, response_text, dominant_emotion)
            if action == "decide":
                await observer.observe_decision(req.message, response_text[:200], confidence=0.7)
        except Exception:
            pass  # 観察の失敗はchat応答に影響させない

        # 5. 感情の自動減衰（会話ごとに少しずつ中立に戻る）
        try:
            await personality.emotion.decay()
        except Exception:
            pass

        return ChatRes(response=response_text, session_id=session_id, action=action, emotion=dominant_emotion, task_id=task_id)

    except LLMError as e:
        logger.error(f"[{session_id[:8]}] LLM error: {e}")
        raise HTTPException(status_code=503, detail=f"AI応答エラー: {e}")
    except Exception as e:
        logger.error(f"[{session_id[:8]}] Chat error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"内部エラー: {type(e).__name__}")


# === Chat Stream (SSEストリーミング版) ===
from fastapi.responses import StreamingResponse as _StreamingResponse
import json as _json

@app.post("/chat/stream")
async def chat_stream(req: ChatReq, _=Depends(verify_api_key)):
    """SSEストリーミングチャット（cocoro-sdk ChatStream互換）

    SSE形式:
      チャンク: data: {"text": "..."}\n\n
      最終:    data: {"type": "final", "sessionId": "...", "action": "...", "emotion": {"dominant": "..."}}\n\n
    """
    session_id = req.session_id or str(uuid.uuid4())

    async def _stream_generator():
        try:
            # 即座にキープアライブを送信（クライアントのタイムアウト防止）
            yield ": ping\n\n"

            # role_id が指定されている場合、リモートノードへ転送する
            if req.role_id:
                remote_node = await find_node_for_role(db_pool, req.role_id)
                if remote_node:
                    # agent_port が設定されていれば cocoro-agent の /tasks に転送
                    # 未設定なら cocoro-core の /chat/stream に転送（フォールバック）
                    if remote_node.get("agent_port"):
                        logger.info(
                            f"[{session_id[:8]}] Routing role={req.role_id} "
                            f"→ agent {remote_node['node_id']} "
                            f"({remote_node['ip']}:{remote_node['agent_port']})"
                        )
                        async for chunk in forward_task_to_agent(
                            remote_node, req.message, session_id, req.role_id
                        ):
                            yield chunk
                    else:
                        logger.info(
                            f"[{session_id[:8]}] Forwarding role={req.role_id} "
                            f"→ core {remote_node['node_id']} "
                            f"({remote_node['ip']}:{remote_node['port']})"
                        )
                        async for chunk in forward_to_node(
                            remote_node, req.message, session_id, req.role_id
                        ):
                            yield chunk
                    return

            # 1. ユーザーメッセージを記憶
            await memory.short.add_message(session_id, "user", req.message)
            await memory.long.save_message(session_id, "user", req.message, emotion="neutral")

            # Governance チェック
            gov_check = await governance.check_input(req.message)
            if not gov_check.passed:
                error_text = gov_check.suggestion or "そのリクエストにはお応えできません。"
                yield f'data: {_json.dumps({"text": error_text})}\n\n'
                yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "blocked", "emotion": {"dominant": "neutral"}})}\n\n'
                return

            # 2. 分類（高速・非ストリーミング）- LLM呼び出し前にkeepalive
            yield ": thinking\n\n"
            classify_prompt = decision.build_classify_prompt(req.message)
            raw = await llm.generate(classify_prompt)
            classification = decision.parse_classification(raw)
            action = classification.get("action", "chat")
            emotion = classification.get("emotion", "neutral")
            await personality.emotion.adjust(emotion)
            personality.emotion._cache = None

            emotion_state = await personality.emotion.get_state()
            dominant_emotion = emotion_state.dominant()

            # delegateはストリーミング非対応 → /chat フォールバック
            if action == "delegate":
                agent_type = classification.get("agent") or router.route(req.message)
                task_name = req.message[:80]
                row = await db_pool.fetchrow(
                    "INSERT INTO tasks (title, description, assigned_agent) VALUES ($1,$2,$3) RETURNING id",
                    task_name, req.message, agent_type)
                task_id = str(row["id"])
                result = await worker.execute(task_id, task_name, req.message, agent_type)
                response_text = result.get("output", result.get("error", "実行失敗"))
                yield f'data: {_json.dumps({"text": response_text})}\n\n'
                yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": action, "emotion": {"dominant": dominant_emotion}})}\n\n'
                return

            # 3. システムプロンプト + コンテキスト構築
            # role_id 指定時はそのロールのsystem_promptを使用
            role_prompt = get_role_system_prompt(req.role_id)
            if role_prompt:
                system_prompt = role_prompt
            else:
                system_prompt = await personality.build_system_prompt()
                friction = await growth.get_creative_friction()
                if friction:
                    system_prompt += friction

            # ユーザー記憶をsystem promptに注入
            if user_memories is not None:
                try:
                    mem_section = await user_memories.build_prompt_section()
                    if mem_section:
                        system_prompt = mem_section + "\n\n" + system_prompt
                except Exception:
                    pass

            if action in ("think", "chat"):
                context = await memory.build_context(session_id, req.message)
                full_prompt = f"{context}\n\n【ユーザー】\n{req.message}" if context else req.message
            elif action == "decide":
                category = classification.get("category", "general")
                full_prompt = await decision.build_decision_prompt(req.message, category)
            else:
                # learn など
                context = await memory.build_context(session_id, req.message)
                full_prompt = f"{context}\n\n【ユーザー】\n{req.message}" if context else req.message

            # 4. Geminiストリーミング → SSEチャンク送信
            full_response = ""
            async for chunk_text in llm.generate_stream(full_prompt, system_prompt):
                full_response += chunk_text
                yield f'data: {_json.dumps({"text": chunk_text})}\n\n'

            # 5. 応答を記憶に保存
            await memory.short.add_message(session_id, "cocoro", full_response)
            await memory.long.save_message(session_id, "cocoro", full_response, emotion=dominant_emotion)

            # 5b. 会話内容から感情を自動更新
            try:
                await personality.emotion.analyze_and_adjust(req.message)
                await personality.emotion.analyze_and_adjust(full_response)
            except Exception:
                pass

            # 5c. ユーザー発言から記憶を自動抽出
            try:
                if user_memories is not None:
                    await user_memories.auto_extract(req.message, full_response)
            except Exception:
                pass

            # 6. 自己観察
            try:
                await observer.observe_conversation(session_id, req.message, full_response, dominant_emotion)
            except Exception:
                pass

            # 7. 最終イベント
            yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": action, "emotion": {"dominant": dominant_emotion}})}\n\n'

        except LLMError as e:
            logger.error(f"[{session_id[:8]}] chat_stream LLMError: {e}")
            yield f'data: {_json.dumps({"text": f"AI応答エラー: {e}"})}\n\n'
            yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
        except Exception as e:
            logger.error(f"[{session_id[:8]}] chat_stream error: {type(e).__name__}: {e}")
            yield f'data: {_json.dumps({"text": "応答の生成中にエラーが発生しました。"})}\n\n'
            yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'

    return _StreamingResponse(
        _stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


@app.get("/decide/pipeline")
async def decide_pipeline_info(_=Depends(verify_api_key)):
    """Decision Graph パイプライン情報"""
    return decision.get_pipeline_info()


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


# === User Memory (自動学習記憶) ===
@app.get("/memory/list")
async def memory_list(
    memory_type: str = None,
    limit: int = 50,
    _=Depends(verify_api_key)
):
    """保存された記憶一覧を返す。memory_type で絞り込み可能"""
    if user_memories is None:
        return {"memories": [], "count": 0}
    try:
        memories = await user_memories.list_all(memory_type=memory_type, limit=limit)
    except Exception as e:
        logger.warning(f"memory_list error ({type(e).__name__}): {e} — returning empty list")
        memories = []
    return {"memories": memories, "count": len(memories)}


@app.get("/memory/search")
async def memory_search_user(q: str, limit: int = 10, _=Depends(verify_api_key)):
    """キーワードで記憶を検索（user_memory + conversation_log 両方）"""
    results = []
    # user_memories テーブル検索
    if user_memories is not None:
        results = await user_memories.search(q, limit)
    # フォールバック: conversation_log 検索
    if not results:
        rows = await db_pool.fetch(
            "SELECT id, session_id, role, content, emotion, created_at "
            "FROM conversation_log "
            "WHERE content ILIKE $1 "
            "ORDER BY created_at DESC LIMIT $2",
            f"%{q}%", limit
        )
        results = [
            {
                "id": str(r["id"]),
                "type": "conversation",
                "type_label": "会話ログ",
                "topic": r["role"],
                "content": r["content"],
                "confidence": 1.0,
                "created_at": str(r["created_at"])[:10],
            }
            for r in rows
        ]
    return {"results": results, "count": len(results), "query": q}


@app.delete("/memory/{memory_id}")
async def memory_delete(memory_id: str, _=Depends(verify_api_key)):
    """特定の記憶を削除"""
    if user_memories is None:
        raise HTTPException(status_code=503, detail="Memory engine not ready")
    deleted = await user_memories.delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "id": memory_id}


@app.post("/memory/add")
async def memory_add_manual(
    topic: str,
    content: str,
    memory_type: str = "general",
    confidence: float = 0.8,
    _=Depends(verify_api_key)
):
    """記憶を手動追加"""
    if user_memories is None:
        raise HTTPException(status_code=503, detail="Memory engine not ready")
    mem_id = await user_memories.add(topic, content, memory_type, confidence)
    return {"id": mem_id, "topic": topic, "type": memory_type}


# ============================================================
# 🧠 Autonomous Thinking & Daily Briefing
# ============================================================

@app.post("/think/start")
async def think_start(_=Depends(verify_api_key)):
    """自律思考セッションを今すぐ開始する。

    直近の会話・記憶・感情状態を振り返り、
    洞察をthought_logに保存して返す。
    """
    if auto_thinker is None:
        raise HTTPException(status_code=503, detail="AutonomousThinker not ready")
    try:
        result = await auto_thinker.run_thinking_session()
        return result
    except Exception as e:
        logger.error(f"Think session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/think/insights")
async def think_insights(limit: int = 10, _=Depends(verify_api_key)):
    """最新の自律思考から洞察一覧を返す。

    Args:
        limit: 返す洞察の最大件数（デフォルト10）
    """
    if auto_thinker is None:
        raise HTTPException(status_code=503, detail="AutonomousThinker not ready")
    insights = await auto_thinker.get_latest_insights(limit=limit)
    return {
        "insights": insights,
        "count": len(insights),
    }


@app.get("/brief/daily")
async def brief_daily_get(date: str = None, _=Depends(verify_api_key)):
    """保存済みデイリーブリーフィングを返す。

    Args:
        date: YYYY-MM-DD形式（省略時は最新）
    """
    if auto_thinker is None:
        raise HTTPException(status_code=503, detail="AutonomousThinker not ready")
    brief = await auto_thinker.get_daily_briefing(date=date)
    if not brief:
        # なければ今すぐ生成
        brief = await auto_thinker.generate_daily_briefing()
    return brief


@app.post("/brief/daily")
async def brief_daily_generate(_=Depends(verify_api_key)):
    """デイリーブリーフィングを今すぐ生成して保存・返却する。"""
    if auto_thinker is None:
        raise HTTPException(status_code=503, detail="AutonomousThinker not ready")
    try:
        result = await auto_thinker.generate_daily_briefing()
        return result
    except Exception as e:
        logger.error(f"Daily briefing generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 📊 Sync Rate (シンクロ率)
# ============================================================

@app.get("/sync/rate")
async def sync_rate_get(_=Depends(verify_api_key)):
    """現在の4要素シンクロ率を返す。

    計算要素（重み）:
      - values_match   (40%): 価値観ベクトルの余弦類似度
      - empathy        (30%): 会話の共感度
      - emotion_stab   (20%): 感情状態の安定度
      - memory_usage   (10%): 記憶の活用度
    """
    if sync_engine is None:
        raise HTTPException(status_code=503, detail="SyncEngine not ready")
    try:
        result = await sync_engine.compute_full_sync_rate(save=True)
        return result
    except Exception as e:
        logger.error(f"Sync rate compute failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/history")
async def sync_rate_history(days: int = 30, _=Depends(verify_api_key)):
    """過去n日間のシンクロ率推移を返す。

    Args:
        days: 取得する日数（デフォルト30日）
    """
    if sync_engine is None:
        raise HTTPException(status_code=503, detail="SyncEngine not ready")
    try:
        history = await sync_engine.get_history(days=days)
        return {
            "days": days,
            "count": len(history),
            "history": history,
        }
    except Exception as e:
        logger.error(f"Sync history fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🎤 Voice & Screen Context (Gemini Multimodal)
# ============================================================

class VoiceTranscribeReq(BaseModel):
    audio_base64: str          # base64エンコードされた音声データ
    language: str = "ja"       # 言語コード（デフォルト日本語）
    audio_format: str = "wav"  # 音声フォーマット


class ContextAnalyzeReq(BaseModel):
    image_base64: str                                    # base64エンコードされた画像データ
    question: str = "この画面について説明してください。"    # 解析の質問
    image_format: str = "png"                            # 画像フォーマット


@app.post("/voice/transcribe")
async def voice_transcribe(req: VoiceTranscribeReq, _=Depends(verify_api_key)):
    """音声データをテキストに転写する。
    
    Gemini のネイティブ Audio 対応を使用。
    対応フォーマット: wav, mp3, ogg, webm, flac, aac, m4a
    """
    if multimodal is None:
        raise HTTPException(status_code=503, detail="Multimodal engine not ready")
    try:
        result = await multimodal.transcribe_audio(
            req.audio_base64,
            language=req.language,
            audio_format=req.audio_format,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/analyze")
async def context_analyze(req: ContextAnalyzeReq, _=Depends(verify_api_key)):
    """画面キャプチャや画像を解析して提案を返す。
    
    Perplexity の「画面コンテキスト認識」相当の機能。
    Gemini Vision API を使用。
    対応フォーマット: png, jpg, jpeg, gif, webp, bmp
    """
    if multimodal is None:
        raise HTTPException(status_code=503, detail="Multimodal engine not ready")
    try:
        result = await multimodal.analyze_image(
            req.image_base64,
            question=req.question,
            image_format=req.image_format,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
@app.get("/emotion")
async def emotion_current(_=Depends(verify_api_key)):
    """現在の感情状態（詳細）"""
    state = await personality.emotion.get_state()
    prompt = await personality.emotion.to_prompt()
    return {**state.to_dict(), "prompt": prompt}

@app.get("/emotion/state")
async def emotion_state(_=Depends(verify_api_key)):
    """現在の感情状態を取得（description 付き強化版）"""
    state = await personality.emotion.get_state()
    d = state.to_dict()
    d["description"] = state.description()
    d["intensity"] = round(state.intensity(), 3)
    return d

@app.get("/emotion/history")
async def emotion_history(limit: int = 20, days: int = 0, _=Depends(verify_api_key)):
    """感情変化の履歴。days=7 で過去7日間のみ返す"""
    if days > 0:
        history = await personality.emotion.get_history_7days()
        return {"history": history, "period_days": days, "count": len(history)}
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


# === Goals (目標管理) ===
@app.get("/goals")
async def list_goals(_=Depends(verify_api_key)):
    """全目標を取得"""
    return {"goals": await personality.goals.get_all()}

class GoalReq(BaseModel):
    title: str
    description: str = ""
    goal_type: str = "short_term"
    priority: int = 5

@app.post("/goals")
async def add_goal(req: GoalReq, _=Depends(verify_api_key)):
    """目標を追加"""
    goal = await personality.goals.add(req.title, req.description, req.goal_type, req.priority)
    return {"status": "created", "goal": goal}

class GoalUpdateReq(BaseModel):
    title: str | None = None
    description: str | None = None
    goal_type: str | None = None
    priority: int | None = None
    status: str | None = None

@app.put("/goals/{goal_id}")
async def update_goal(goal_id: str, req: GoalUpdateReq, _=Depends(verify_api_key)):
    """目標を更新"""
    goal = await personality.goals.update(goal_id, **req.model_dump(exclude_none=True))
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "updated", "goal": goal}

@app.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, _=Depends(verify_api_key)):
    """目標を削除"""
    deleted = await personality.goals.delete(goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "deleted"}


# === Governance (ガバナンス) ===
@app.get("/governance/report")
async def governance_report(_=Depends(verify_api_key)):
    """ガバナンス総合レポート"""
    return await governance.get_full_report()

@app.get("/governance/log")
async def governance_log(limit: int = 20, _=Depends(verify_api_key)):
    """ガバナンスログ"""
    rows = await db_pool.fetch(
        "SELECT * FROM governance_log ORDER BY created_at DESC LIMIT $1", limit)
    return {"log": [dict(r) for r in rows]}

class GovernanceCheckReq(BaseModel):
    text: str

@app.post("/governance/check")
async def governance_check(req: GovernanceCheckReq, _=Depends(verify_api_key)):
    """テキストの倫理チェック"""
    result = await governance.check_input(req.text)
    return result.to_dict()


# === Setup (人格形成) ===
class SetupStartReq(BaseModel):
    mode: str = "boot"  # "boot" (40問) or "deep" (80問)
    lang: str = "ja"   # ja / en / zh

@app.post("/setup/start",
          summary="人格形成ウィザード開始",
          description="""Boot Wizardセッションを開始します。

**langパラメータ:**
- `ja` — 日本語 (default)
- `en` — English
- `zh` — 中文

`GET /setup/start?lang=en` でURLパラメータ指定も可能。""",
          tags=["setup"])
async def setup_start(req: SetupStartReq = SetupStartReq(), _=Depends(verify_api_key)):
    """人格形成セッションを開始"""
    return boot_wizard.start_session(req.mode, lang=req.lang)

class SetupAnswerReq(BaseModel):
    session_id: str
    question_id: str | None = None  # 指定時はそのIDの質問にジャンプ（戻る操作対応）
    answer: str

@app.post("/setup/answer")
async def setup_answer(req: SetupAnswerReq, _=Depends(verify_api_key)):
    """質問に回答（question_id 指定で任意の問にジャンプ可能）"""
    return boot_wizard.answer(req.session_id, req.answer, req.question_id)

@app.get("/setup/progress/{session_id}")
async def setup_progress(session_id: str, _=Depends(verify_api_key)):
    """進捗を確認"""
    return boot_wizard.get_progress(session_id)

@app.get("/setup/result/{session_id}")
async def setup_result(session_id: str, _=Depends(verify_api_key)):
    """分析結果を取得"""
    return await boot_wizard.get_result(session_id)


# === Decision Sampling (意思決定テスト) ===
@app.post("/test/sampling/start")
async def sampling_start(_=Depends(verify_api_key)):
    """Decision Sampling セッション開始"""
    return sampling.start()

class SamplingAnswerReq(BaseModel):
    session_id: str
    option_index: int

@app.post("/test/sampling/answer")
async def sampling_answer(req: SamplingAnswerReq, _=Depends(verify_api_key)):
    """シナリオに回答"""
    return sampling.answer(req.session_id, req.option_index)

@app.get("/test/sampling/result/{session_id}")
async def sampling_result(session_id: str, _=Depends(verify_api_key)):
    """Decision Vector 算出"""
    return await sampling.get_result(session_id)


# === Test Bench (人格一致率テスト) ===
@app.post("/test/bench/start")
async def bench_start(_=Depends(verify_api_key)):
    """Test Bench セッション開始"""
    return test_bench.start()

class BenchAnswerReq(BaseModel):
    session_id: str
    choice: int

@app.post("/test/bench/answer")
async def bench_answer(req: BenchAnswerReq, _=Depends(verify_api_key)):
    """質問に回答"""
    return test_bench.answer(req.session_id, req.choice)

@app.get("/test/bench/score/{session_id}")
async def bench_score(session_id: str, _=Depends(verify_api_key)):
    """一致率スコアを取得"""
    return await test_bench.get_score(session_id)


# === Self Evolution (自己進化) ===
@app.get("/evolution/observations")
async def get_observations(limit: int = 50, _=Depends(verify_api_key)):
    """自己観察ログ取得"""
    return {"observations": observer.get_recent(limit)}

@app.get("/evolution/observations/stats")
async def get_observation_stats(hours: int = 24, _=Depends(verify_api_key)):
    """観察統計"""
    return observer.get_stats(hours)

@app.get("/evolution/evaluate")
async def self_evaluate(hours: int = 24, _=Depends(verify_api_key)):
    """自己評価実行"""
    return await evaluator.evaluate(hours)

@app.post("/evolution/improve")
async def generate_improvement(hours: int = 24, _=Depends(verify_api_key)):
    """改善計画生成"""
    evaluation = await evaluator.evaluate(hours)
    plan = improver.generate_plan(evaluation)
    return plan

@app.post("/evolution/improve/{plan_id}/execute")
async def execute_improvement(plan_id: str, _=Depends(verify_api_key)):
    """改善計画実行"""
    return improver.execute_plan(plan_id)

@app.get("/evolution/plans")
async def get_improvement_plans(limit: int = 10, _=Depends(verify_api_key)):
    """改善計画一覧"""
    plans = improver.get_plans(limit)
    return {"plans": plans}

@app.get("/evolution/report")
async def evolution_report(hours: int = 24, _=Depends(verify_api_key)):
    """自己進化総合レポート"""
    stats = observer.get_stats(hours)
    evaluation = await evaluator.evaluate(hours)
    plans = improver.get_plans(5)
    return {
        "observation_stats": stats,
        "self_evaluation": evaluation,
        "recent_plans": plans,
        "evolution_version": "1.0",
    }


# === Meta Cognition (メタ認知) ===
@app.get("/meta/awareness")
async def self_awareness(_=Depends(verify_api_key)):
    """自己認識状態"""
    return meta_cognition.get_self_awareness()

@app.post("/meta/strategy")
async def generate_strategy(objective: str = "", _=Depends(verify_api_key)):
    """戦略立案"""
    return meta_cognition.generate_strategy(objective)

@app.get("/meta/plan")
async def long_term_plan(_=Depends(verify_api_key)):
    """長期計画"""
    return meta_cognition.get_long_term_plan()


# === Value Scoring (2層スコアリング) ===
class ScoreReq(BaseModel):
    response: str
    context: str = ""

class OptionsReq(BaseModel):
    options: list[str]
    context: str = ""

@app.post("/scoring/response")
async def score_response(req: ScoreReq, _=Depends(verify_api_key)):
    """応答の価値観整合性スコア"""
    return value_scoring.score_response(req.response, req.context)

@app.post("/scoring/options")
async def score_options(req: OptionsReq, _=Depends(verify_api_key)):
    """複数選択肢のValuesスコアリング"""
    return value_scoring.score_options(req.options, req.context)

@app.post("/scoring/validate")
async def validate_response(req: ScoreReq, _=Depends(verify_api_key)):
    """応答検証＆必要ならリライト"""
    return value_scoring.validate_and_rewrite(req.response, req.context)


# === Intelligence Expansion (知能拡張) ===
class KnowledgeReq(BaseModel):
    topic: str
    content: str
    source: str = "manual"
    confidence: float = 0.7

@app.post("/intelligence/knowledge")
async def add_knowledge(req: KnowledgeReq, _=Depends(verify_api_key)):
    """知識追加"""
    return intelligence.add_knowledge(req.topic, req.content, req.source, req.confidence)

@app.get("/intelligence/knowledge/search")
async def search_knowledge(query: str, limit: int = 10, _=Depends(verify_api_key)):
    """知識検索"""
    return {"results": intelligence.search_knowledge(query, limit)}

@app.get("/intelligence/skills")
async def get_skills(category: str = "", _=Depends(verify_api_key)):
    """スキル一覧"""
    return {"skills": intelligence.get_skills(category or None)}

class SkillReq(BaseModel):
    name: str
    category: str = "general"
    proficiency: float = 0.1

@app.post("/intelligence/skills")
async def register_skill(req: SkillReq, _=Depends(verify_api_key)):
    """スキル登録"""
    return intelligence.register_skill(req.name, req.category, req.proficiency)

@app.get("/intelligence/tools")
async def get_tool_stats(_=Depends(verify_api_key)):
    """ツール使用統計"""
    return intelligence.get_tool_stats()

@app.get("/intelligence/report")
async def intelligence_report(_=Depends(verify_api_key)):
    """知能拡張レポート"""
    return intelligence.get_intelligence_report()


# === Safety Layer (安全性) ===
@app.get("/safety/alignment")
async def check_alignment(_=Depends(verify_api_key)):
    """アライメントチェック"""
    return safety.check_alignment()

@app.get("/safety/modification")
async def check_modification(mod_type: str = "value", _=Depends(verify_api_key)):
    """自己変更許可チェック"""
    return safety.check_modification_allowed(mod_type)

@app.get("/safety/report")
async def safety_report(_=Depends(verify_api_key)):
    """安全性レポート"""
    return safety.get_safety_report()

@app.get("/v5/report")
async def v5_full_report(_=Depends(verify_api_key)):
    """v5 自己進化総合レポート"""
    evolution = observer.get_stats(24)
    evaluation = await evaluator.evaluate(24)
    intel = intelligence.get_intelligence_report()
    safe = safety.get_safety_report()
    awareness = meta_cognition.get_self_awareness()
    return {
        "version": "5.0",
        "observation_stats": evolution,
        "self_evaluation": evaluation,
        "intelligence": intel,
        "safety": safe,
        "self_awareness": awareness,
    }


# === Cognitive Profile (v2: 認知スタイル + リスク) ===
@app.get("/personality/cognitive")
async def get_cognitive_profile(_=Depends(verify_api_key)):
    """認知プロファイル (Cognitive Style + Risk Profile)"""
    return cognitive.analyze()


# === Personality Calibration (v2.5: 人格一致率テスト) ===
@app.post("/calibration/start")
async def start_calibration(_=Depends(verify_api_key)):
    """キャリブレーション開始 (50問)"""
    return calibration.start_calibration()

class CalibrationAnswers(BaseModel):
    session_id: str
    answers: dict

@app.post("/calibration/submit")
async def submit_calibration(req: CalibrationAnswers, _=Depends(verify_api_key)):
    """キャリブレーション回答提出"""
    int_answers = {int(k): int(v) for k, v in req.answers.items()}
    return calibration.submit_answers(req.session_id, int_answers)

@app.get("/calibration/history")
async def calibration_history(_=Depends(verify_api_key)):
    """キャリブレーション履歴"""
    return {"history": calibration.get_calibration_history()}

@app.get("/v2/status")
async def v2_status(_=Depends(verify_api_key)):
    """v2/v2.5 人格形成ステータス"""
    cog = cognitive.analyze()
    cal_history = calibration.get_calibration_history()
    return {
        "version": "2.5",
        "cognitive_profile": cog,
        "calibration_history": cal_history[:3],
        "eight_elements": {
            "identity": True,
            "values": True,
            "beliefs": True,
            "goals": True,
            "cognitive_style": cog["cognitive_style"]["style"],
            "risk_profile": cog["risk_profile"]["profile"],
            "emotional_profile": True,
            "life_narrative": True,
        },
    }


# === Personality Clone (v4: Identity Layer) ===
@app.get("/clone/backup")
async def clone_backup(_=Depends(verify_api_key)):
    """人格の完全バックアップ"""
    return await clone_engine.backup()

@app.post("/clone/restore")
async def clone_restore(req: Request, _=Depends(verify_api_key)):
    """バックアップからの人格復元"""
    data = await req.json()
    return await clone_engine.restore(data)

@app.post("/clone/diff")
async def clone_diff(req: Request, _=Depends(verify_api_key)):
    """現在の人格とバックアップの差分"""
    data = await req.json()
    return await clone_engine.get_diff(data)


# === A-5: Database Migration ===
@app.get("/migrate/status")
async def migrate_status(_=Depends(verify_api_key)):
    """マイグレーション状態"""
    return await migration_runner.get_status()

@app.post("/migrate/run")
async def migrate_run(_=Depends(verify_api_key)):
    """マイグレーション実行"""
    return await migration_runner.migrate()


# === C-6: Emotion Behavior Adaptation ===
@app.get("/emotion/adaptation")
async def emotion_adaptation(_=Depends(verify_api_key)):
    """現在の感情に基づく行動適応パラメータ"""
    return emotion_adapter.get_full_adaptation()

@app.get("/emotion/decision-threshold")
async def emotion_decision_threshold(_=Depends(verify_api_key)):
    """感情に基づく判断閾値"""
    return emotion_adapter.get_decision_threshold()

@app.get("/emotion/response-modifiers")
async def emotion_response_modifiers(_=Depends(verify_api_key)):
    """応答生成時の感情修飾パラメータ"""
    return emotion_adapter.get_response_modifiers()


# === C-7: Memory Archive ===
@app.get("/memory/stats")
async def memory_stats(_=Depends(verify_api_key)):
    """記憶テーブルの統計"""
    return await memory_archiver.get_stats()  # fix: was missing await

@app.post("/memory/archive")
async def memory_archive(_=Depends(verify_api_key)):
    """全テーブルのアーカイブ実行"""
    return await memory_archiver.run_full_archive()  # fix: was missing await

@app.get("/memory/archive/history")
async def memory_archive_history(_=Depends(verify_api_key)):
    """アーカイブ履歴"""
    return await memory_archiver.get_archive_history()  # fix: was missing await


@app.get("/memory/search")
async def memory_search(q: str, limit: int = 10, _=Depends(verify_api_key)):
    """長期記憶（会話ログ）をテキスト検索"""
    rows = await db_pool.fetch(
        "SELECT id, session_id, role, content, emotion, created_at "
        "FROM conversation_log "
        "WHERE content ILIKE $1 "
        "ORDER BY created_at DESC LIMIT $2",
        f"%{q}%", limit
    )
    results = [
        {
            "id": str(r["id"]),
            "session_id": str(r["session_id"]),
            "role": r["role"],
            "content": r["content"],
            "emotion": r["emotion"],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]
    return {"results": results, "count": len(results), "query": q}


@app.get("/memory/conversations")
async def memory_conversations(limit: int = 20, _=Depends(verify_api_key)):
    """会話セッション一覧（直近N件）"""
    rows = await db_pool.fetch(
        "SELECT session_id, COUNT(*) as msg_count, "
        "MIN(created_at) as started_at, MAX(created_at) as last_at, "
        "MAX(emotion) as last_emotion "
        "FROM conversation_log "
        "GROUP BY session_id "
        "ORDER BY last_at DESC LIMIT $1",
        limit
    )
    sessions = [
        {
            "session_id": str(r["session_id"]),
            "message_count": r["msg_count"],
            "started_at": str(r["started_at"]),
            "last_at": str(r["last_at"]),
            "last_emotion": r["last_emotion"],
        }
        for r in rows
    ]
    return {"sessions": sessions, "count": len(sessions)}


# === C-5: Plugin System ===
@app.get("/plugins")
async def list_plugins(_=Depends(verify_api_key)):
    """プラグイン一覧"""
    return {"plugins": plugin_registry.list_plugins(), **plugin_registry.get_stats()}

@app.post("/plugins/execute")
async def execute_plugin(req: dict, _=Depends(verify_api_key)):
    """プラグイン実行"""
    name = req.get("name", "")
    args = req.get("args", {})
    return plugin_registry.execute(name, args)

@app.get("/plugins/tools")
async def plugin_tool_definitions(_=Depends(verify_api_key)):
    """プラグインのツール定義 (Function Calling用)"""
    return plugin_registry.get_tool_definitions()

@app.get("/plugins/stats")
async def plugin_stats(_=Depends(verify_api_key)):
    """プラグイン統計"""
    return plugin_registry.get_stats()


# === C-4: ローカルLLM管理 ===
@app.get("/llm/local/models")
async def llm_local_models(_=Depends(verify_api_key)):
    """ローカルLLMモデル一覧"""
    return {"models": await local_llm.list_models()}

@app.get("/llm/local/health")
async def llm_local_health(_=Depends(verify_api_key)):
    """ローカルLLMヘルスチェック"""
    return await local_llm.health_check()

@app.post("/llm/local/switch")
async def llm_local_switch(body: dict, _=Depends(verify_api_key)):
    """ローカルLLMモデル切り替え"""
    return await local_llm.switch_model(body.get("model", ""))

@app.get("/llm/local/info")
async def llm_local_info(model: str = None, _=Depends(verify_api_key)):
    """モデル詳細情報"""
    return await local_llm.model_info(model)

@app.get("/llm/local/stats")
async def llm_local_stats(_=Depends(verify_api_key)):
    """ローカルLLM統計"""
    return await local_llm.get_stats()


# === C-2: マルチユーザー管理 ===
@app.post("/users/session")
async def user_session(body: dict, _=Depends(verify_api_key)):
    """セッション取得/作成"""
    session = user_manager.get_or_create_session(
        body.get("user_id", "default"),
        body.get("display_name", ""),
    )
    return session.to_dict()

@app.delete("/users/session/{user_id}")
async def user_session_end(user_id: str, _=Depends(verify_api_key)):
    """セッション終了"""
    return {"ended": user_manager.end_session(user_id)}

@app.get("/users/sessions")
async def user_sessions(_=Depends(verify_api_key)):
    """アクティブセッション一覧"""
    return {"sessions": user_manager.list_active_sessions()}

@app.post("/users/preference")
async def user_preference(body: dict, _=Depends(verify_api_key)):
    """ユーザー設定の保存"""
    user_manager.set_preference(
        body.get("user_id", "default"),
        body.get("key", ""),
        body.get("value", ""),
    )
    return {"saved": True}

@app.get("/users/preferences/{user_id}")
async def user_preferences(user_id: str, _=Depends(verify_api_key)):
    """ユーザー設定一覧"""
    return user_manager.get_user_preferences(user_id)

@app.get("/users/stats")
async def user_stats(_=Depends(verify_api_key)):
    """ユーザー統計"""
    return user_manager.get_stats()


# === C-3: 人格間コミュニケーション ===
@app.post("/comm/peer")
async def comm_register_peer(body: dict, _=Depends(verify_api_key)):
    """通信相手を登録"""
    return peer_comm.register_peer(
        body.get("peer_id", ""),
        body.get("name", ""),
        body.get("endpoint", ""),
        body.get("personality_summary", ""),
    )

@app.get("/comm/peers")
async def comm_list_peers(_=Depends(verify_api_key)):
    """通信相手一覧"""
    return {"peers": peer_comm.list_peers()}

@app.post("/comm/discussion")
async def comm_start_discussion(body: dict, _=Depends(verify_api_key)):
    """協議セッション開始"""
    return peer_comm.start_discussion(
        body.get("topic", ""),
        body.get("participants", []),
    )

@app.post("/comm/discussion/{discussion_id}/opinion")
async def comm_add_opinion(discussion_id: str, body: dict, _=Depends(verify_api_key)):
    """協議に意見追加"""
    return peer_comm.add_opinion(
        discussion_id,
        body.get("peer_id", peer_comm.self_id),
        body.get("content", ""),
        body.get("stance", "neutral"),
    )

@app.post("/comm/discussion/{discussion_id}/conclude")
async def comm_conclude(discussion_id: str, body: dict, _=Depends(verify_api_key)):
    """協議を結論付ける"""
    return peer_comm.conclude_discussion(
        discussion_id, body.get("conclusion", ""),
    )

@app.get("/comm/discussions")
async def comm_list_discussions(status: str = None, _=Depends(verify_api_key)):
    """協議一覧"""
    return {"discussions": peer_comm.list_discussions(status)}

@app.post("/comm/message")
async def comm_send_message(body: dict, _=Depends(verify_api_key)):
    """ダイレクトメッセージ送信"""
    return peer_comm.send_message(
        body.get("to", ""),
        body.get("content", ""),
        body.get("type", "general"),
    )

@app.get("/comm/inbox")
async def comm_inbox(limit: int = 20, _=Depends(verify_api_key)):
    """受信メッセージ"""
    return {"messages": peer_comm.get_inbox(limit)}

@app.get("/comm/stats")
async def comm_stats(_=Depends(verify_api_key)):
    """通信統計"""
    return peer_comm.get_stats()


# === C-8: 音声インターフェース ===
voice = VoiceInterface()

@app.post("/voice/parse")
async def voice_parse(body: dict, _=Depends(verify_api_key)):
    """音声コマンド解析"""
    return voice.parse_command(body.get("text", ""))

@app.post("/voice/speak")
async def voice_speak(body: dict, _=Depends(verify_api_key)):
    """テキスト読み上げ準備"""
    return voice.prepare_speech(
        body.get("text", ""),
        body.get("emotion", "neutral"),
        body.get("intensity", 0.0),
    )

@app.get("/voice/settings")
async def voice_settings(_=Depends(verify_api_key)):
    """音声設定取得"""
    return voice.get_settings()

@app.post("/voice/settings")
async def voice_settings_update(body: dict, _=Depends(verify_api_key)):
    """音声設定変更"""
    return voice.set_settings(**body)

@app.get("/voice/stats")
async def voice_stats(_=Depends(verify_api_key)):
    """音声統計"""
    return voice.get_stats()


# === C-1: ダッシュボードUI ===
import pathlib
from fastapi.responses import HTMLResponse

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """ダッシュボードUI"""
    html_path = pathlib.Path(__file__).parent / "static" / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/org/report")
async def org_report(_=Depends(verify_api_key)):
    """組織レポート"""
    return await org.get_org_report()

@app.get("/org/departments")
async def org_departments(_=Depends(verify_api_key)):
    """部門一覧"""
    return {"departments": org.list_departments()}

@app.get("/org/agents")
async def org_agents(_=Depends(verify_api_key)):
    """Agent一覧（詳細）"""
    return {"agents": org.list_agents()}

class AgentRegReq(BaseModel):
    agent_type: str
    display_name: str
    role: str = "worker"
    capabilities: list[str] = []
    department: str | None = None
    parent_agent_id: str | None = None   # 親エージェントの agent_type
    level: int = 1                        # 0=CEO, 1=Director, 2=Manager, 3=Worker
    max_subordinates: int = 5             # 最大直属部下数

@app.post("/org/agents/register")
async def register_agent(req: AgentRegReq, _=Depends(verify_api_key)):
    """新しいAgentを組織に登録（階層情報付き）"""
    try:
        agent = await org.register_agent(
            agent_type=req.agent_type, display_name=req.display_name,
            role=req.role, capabilities=req.capabilities,
            department=req.department)
        # 階層カラムを DB に直接更新
        if db_pool:
            await db_pool.execute(
                """
                UPDATE agent_registry
                SET parent_agent_id = $1,
                    level            = $2,
                    max_subordinates = $3
                WHERE agent_type = $4
                """,
                req.parent_agent_id,
                req.level,
                req.max_subordinates,
                req.agent_type,
            )
        return {"status": "registered", "agent": agent,
                "hierarchy": {"level": req.level,
                               "parent_agent_id": req.parent_agent_id,
                               "max_subordinates": req.max_subordinates}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class DelegateReq(BaseModel):
    task_id: str
    from_agent: str
    to_agent: str = ""           # 空の場合は階層自動振り分け (CEO→Director)
    reason: str = ""
    auto_cascade: bool = True     # CEOからの器示はDirectorに自動振り分け

@app.post("/org/delegate")
async def delegate_task(req: DelegateReq, _=Depends(verify_api_key)):
    """タスクを別Agentに委任。CEOからの器示は適切なDirectorに自動振り分け。"""
    try:
        to_agent = req.to_agent

        # 階層自動振り分け: from_agent が CEO (level=0) で to_agent 未指定の場合
        if req.auto_cascade and (not to_agent) and db_pool:
            # タスク内容から適切な Director を選拦
            task_row = await db_pool.fetchrow(
                "SELECT title, description FROM agent_tasks WHERE id=$1::uuid",
                req.task_id
            )
            title = (task_row["title"] if task_row else "").lower()
            desc  = (task_row["description"] if task_row else "").lower()
            text  = title + " " + desc

            # キーワードマッチングで Director を推定
            if any(k in text for k in ["コード", "code", "プログラム", "バグ", "bug", "レビュー", "api", "テスト"]):
                to_agent = "dev"
            elif any(k in text for k in ["マーケティング", "広告", "sns", "キャンペーン", "ブランド"]):
                to_agent = "marketing"
            elif any(k in text for k in ["営業", "販売", "出荷", "原価", "契約", "sales", "顧客"]):
                to_agent = "sales"
            else:
                # デフォルト: 最もアイドルな Directorへ
                director_row = await db_pool.fetchrow(
                    "SELECT agent_type FROM agent_registry WHERE level=1 "
                    "AND status='active' ORDER BY RANDOM() LIMIT 1"
                )
                to_agent = director_row["agent_type"] if director_row else "dev"

            logger.info(f"[Delegate] Auto-routed to Director: {to_agent} (task={req.task_id[:8]})")

        if not to_agent:
            raise HTTPException(status_code=400, detail="to_agent を指定するか auto_cascade=true にしてください")

        result = await org.delegate_task(
            task_id=req.task_id, from_agent=req.from_agent,
            to_agent=to_agent, reason=req.reason)
        return {"status": "delegated", "delegation": result, "routed_to": to_agent}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/org/hierarchy", tags=["org"], summary="組織階層ツリー")
async def org_hierarchy(_=Depends(verify_api_key)):
    """組織階層構造をツリー形式で返す。

    レイヤー定義:
      0 = CEO   (最上位)
      1 = Director (部長)
      2 = Manager  (マネージャー)
      3 = Worker   (作業員)
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="DB not ready")

    LEVEL_LABELS = {0: "CEO", 1: "Director", 2: "Manager", 3: "Worker"}

    # 全エージェントを取得
    rows = await db_pool.fetch(
        """
        SELECT agent_type, display_name, role, status, department,
               COALESCE(level, 0)            AS level,
               parent_agent_id,
               COALESCE(max_subordinates, 5) AS max_subordinates
        FROM agent_registry
        ORDER BY level, agent_type
        """
    )
    agents = {r["agent_type"]: dict(r) for r in rows}

    def _build_node(agent_type: str, visited: set) -> dict:
        if agent_type in visited:
            return {}  # 循環参照防止
        visited.add(agent_type)
        a = agents.get(agent_type, {})
        level = a.get("level", 0)
        node = {
            "id":              agent_type,
            "name":            a.get("display_name", agent_type),
            "role":            a.get("role", ""),
            "status":          a.get("status", "unknown"),
            "department":      a.get("department"),
            "level":           level,
            "level_label":     LEVEL_LABELS.get(level, f"Level{level}"),
            "max_subordinates": a.get("max_subordinates", 5),
        }
        # 直属部下を再帰的に構築
        children_key = {
            0: "directors",
            1: "managers",
            2: "workers",
        }.get(level)
        if children_key:
            children = [
                _build_node(at, visited)
                for at, ag in agents.items()
                if ag.get("parent_agent_id") == agent_type
            ]
            node[children_key] = children
        return node

    # CEO ノードを前展
    ceo_agents = [a for a in agents.values() if a.get("level", 0) == 0]

    # CEO なし → デフォルト CEO ノードを容用
    if ceo_agents:
        ceo = ceo_agents[0]
        ceo_node = _build_node(ceo["agent_type"], set())
    else:
        # CEO 登録なしの場合: level=1 をディレクターとして CEO 代用ノードを容用
        directors = [
            _build_node(at, set())
            for at, ag in agents.items()
            if ag.get("level", 1) == 1
        ]
        ceo_node = {
            "id":          "ceo",
            "name":        "CEO (You)",
            "level":       0,
            "level_label": "CEO",
            "directors":   directors,
        }

    # level 別サマリー
    summary = {}
    for a in agents.values():
        lv = a.get("level", 0)
        lbl = LEVEL_LABELS.get(lv, f"Level{lv}")
        summary[lbl] = summary.get(lbl, 0) + 1

    return {
        "ceo":     ceo_node,
        "summary": summary,
        "total":   len(agents),
    }


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


# ===================== D-2: Ollama 実機テスト =====================

@app.get("/ollama/test", tags=["ollama"])
async def ollama_run_tests(_=Depends(verify_api_key)):
    """Ollama 全テスト実行"""
    return await ollama_test.run_all()

@app.get("/ollama/test/connection", tags=["ollama"])
async def ollama_test_connection(_=Depends(verify_api_key)):
    """Ollama 接続テスト"""
    return await ollama_test.test_connection()

@app.get("/ollama/test/models", tags=["ollama"])
async def ollama_test_models(_=Depends(verify_api_key)):
    """Ollama モデル一覧テスト"""
    return await ollama_test.test_list_models()

@app.get("/ollama/test/generate", tags=["ollama"])
async def ollama_test_generate(_=Depends(verify_api_key)):
    """Ollama 推論テスト"""
    return await ollama_test.test_generate()


# ===================== D-3: Discord / LINE 連携 =====================

@app.get("/integrations/status", tags=["integrations"])
async def integration_status(_=Depends(verify_api_key)):
    """連携プラットフォーム ステータス"""
    return integrations.get_all_status()

@app.post("/integrations/discord/send", tags=["integrations"])
async def discord_send(request: Request, _=Depends(verify_api_key)):
    """Discord メッセージ送信"""
    body = await request.json()
    return await integrations.discord.send_message(
        body.get("content", ""), body.get("username", "cocoro"))

@app.post("/integrations/discord/interaction", tags=["integrations"])
async def discord_interaction(request: Request):
    """Discord Interaction Webhook"""
    body = await request.json()
    parsed = integrations.discord.parse_interaction(body)
    if parsed["type"] == "ping":
        return parsed["response"]
    return parsed

@app.post("/integrations/line/webhook", tags=["integrations"])
async def line_webhook(request: Request):
    """LINE Webhook 受信"""
    body = await request.json()
    events = integrations.line.parse_webhook(body)
    return {"events": events, "count": len(events)}

@app.post("/integrations/line/reply", tags=["integrations"])
async def line_reply(request: Request, _=Depends(verify_api_key)):
    """LINE 返信送信"""
    body = await request.json()
    return await integrations.line.reply(
        body.get("reply_token", ""), body.get("text", ""))


# ===================== D-4: WebSocket リアルタイム =====================

from starlette.websockets import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket リアルタイム接続"""
    await ws.accept()
    ws_connections.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            event_type = data.get("type", "ping")
            if event_type == "ping":
                await ws.send_json({"type": "pong"})
            elif event_type == "subscribe":
                await ws.send_json({"type": "subscribed",
                                    "channel": data.get("channel", "all")})
            else:
                await ws.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_connections:
            ws_connections.remove(ws)

@app.get("/ws/connections", tags=["websocket"])
async def ws_connection_count(_=Depends(verify_api_key)):
    """WebSocket 接続数"""
    return {"active_connections": len(ws_connections)}


# ===================== D-6: 人格テンプレート =====================

@app.get("/templates", tags=["templates"])
async def list_templates(_=Depends(verify_api_key)):
    """テンプレート一覧"""
    return {"templates": templates.list_templates()}

@app.get("/templates/categories", tags=["templates"])
async def template_categories(_=Depends(verify_api_key)):
    """テンプレートカテゴリ一覧"""
    return {"categories": templates.list_categories()}

@app.get("/templates/{template_id}", tags=["templates"])
async def get_template(template_id: str, _=Depends(verify_api_key)):
    """テンプレート詳細"""
    result = templates.get_template(template_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/templates/{template_id}/apply", tags=["templates"])
async def apply_template(template_id: str, request: Request,
                          _=Depends(verify_api_key)):
    """テンプレート適用"""
    body = await request.json()
    result = templates.apply_template(template_id, body.get("overrides"))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/templates/custom", tags=["templates"])
async def register_custom_template(request: Request,
                                     _=Depends(verify_api_key)):
    """カスタムテンプレート登録"""
    body = await request.json()
    tid = body.pop("id", "custom_" + str(uuid.uuid4())[:8])
    return templates.register_custom(tid, body)


# ===================== D-7: 監視・アラート =====================

@app.get("/monitor/dashboard", tags=["monitoring"])
async def monitor_dashboard(_=Depends(verify_api_key)):
    """監視ダッシュボード"""
    return monitoring.get_health_dashboard()

@app.get("/monitor/metrics", tags=["monitoring"])
async def monitor_metrics(_=Depends(verify_api_key)):
    """メトリクス一覧"""
    return monitoring.metrics.get_all()

@app.get("/monitor/metrics/prometheus", tags=["monitoring"])
async def monitor_prometheus():
    """Prometheus テキスト形式メトリクス"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        monitoring.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4")

@app.get("/monitor/alerts", tags=["monitoring"])
async def monitor_alerts(_=Depends(verify_api_key)):
    """アラートチェック"""
    fired = monitoring.check_alerts()
    return {"alerts": fired, "total_rules": len(monitoring._alerts)}

@app.get("/monitor/alerts/history", tags=["monitoring"])
async def monitor_alert_history(_=Depends(verify_api_key)):
    """アラート履歴"""
    return {"history": monitoring.get_alert_history()}

@app.post("/monitor/alerts", tags=["monitoring"])
async def add_alert_rule(request: Request, _=Depends(verify_api_key)):
    """カスタムアラートルール追加"""
    body = await request.json()
    return monitoring.add_alert(
        body["name"], body["metric"], body["condition"],
        body["threshold"], body.get("severity", "warning"))


# ===================== D-8: 多言語対応 =====================

@app.get("/i18n/languages", tags=["i18n"])
async def i18n_languages(_=Depends(verify_api_key)):
    """サポート言語一覧"""
    return {"languages": i18n.supported_languages,
            "default": i18n.default_lang}

@app.get("/i18n/messages", tags=["i18n"])
async def i18n_messages(lang: str = None, _=Depends(verify_api_key)):
    """メッセージ辞書"""
    return {"messages": i18n.get_all_messages(lang), "language": lang or i18n.default_lang}

@app.post("/i18n/user/language", tags=["i18n"])
async def set_user_language(request: Request, _=Depends(verify_api_key)):
    """ユーザー言語設定"""
    body = await request.json()
    return i18n.set_user_language(body.get("user_id", "default"),
                                  body.get("language", "ja"))

@app.get("/i18n/translate/{key}", tags=["i18n"])
async def translate_message(key: str, lang: str = None, _=Depends(verify_api_key)):
    """メッセージ翻訳"""
    return {"key": key,
            "message": i18n.get_message(key, lang),
            "language": lang or i18n.default_lang}

# ============================================================
# 人格ベクトル 32次元システム
# ============================================================

@app.post("/personality/init", tags=["personality-vector"])
async def personality_init(request: Request, _=Depends(verify_api_key)):
    """生年月日・血液型・動物タイプから人格プロファイルを生成"""
    from datetime import date as dt_date
    body = await request.json()
    birthdate = dt_date.fromisoformat(body["birthdate"])
    blood_type = body.get("blood_type", "O")
    animal_type = body.get("animal_type", "wolf")

    profile = PersonalityProfile(
        birthdate=birthdate,
        blood_type=blood_type,
        animal_type=animal_type,
    )
    seed_result = profile.generate_seed()
    personality_profiles[profile.id] = profile
    return {"status": "created", "profile": seed_result}

@app.get("/personality/profile/{profile_id}", tags=["personality-vector"])
async def personality_get(profile_id: str, _=Depends(verify_api_key)):
    """人格プロファイル取得"""
    profile = personality_profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.to_dict()

@app.get("/personality/animals", tags=["personality-vector"])
async def personality_animals(_=Depends(verify_api_key)):
    """動物アーキタイプ一覧"""
    return {"animals": list_animals()}

@app.get("/personality/questions", tags=["personality-vector"])
async def personality_questions(count: int = None, _=Depends(verify_api_key)):
    """簡易質問リスト取得"""
    return {"questions": get_questions(count)}

@app.post("/personality/questions/apply/{profile_id}", tags=["personality-vector"])
async def personality_apply_answers(profile_id: str, request: Request,
                                     _=Depends(verify_api_key)):
    """質問回答からプロファイルを補正"""
    profile = personality_profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    body = await request.json()
    answers = body.get("answers", {})
    modifiers = apply_answers(answers)
    result = profile.apply_question_modifiers(modifiers)
    return {"status": "applied", "result": result,
            "updated_profile": profile.to_dict()}

@app.post("/personality/learn/{profile_id}", tags=["personality-vector"])
async def personality_learn(profile_id: str, request: Request,
                             _=Depends(verify_api_key)):
    """フィードバックから人格を学習"""
    profile = personality_profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    body = await request.json()
    feedback_type = body.get("feedback_type", "neutral")
    traits = body.get("traits", {})
    record = personality_learning_engine.learn_from_feedback(
        profile.vector, feedback_type, traits
    )
    return {"status": "learned", "record": record}

@app.get("/personality/learning/stats", tags=["personality-vector"])
async def personality_learning_stats(_=Depends(verify_api_key)):
    """学習統計"""
    return personality_learning_engine.get_stats()

# ============================================================
# 相性診断エンジン
# ============================================================

@app.post("/compatibility/check", tags=["compatibility"])
async def compatibility_check(request: Request, _=Depends(verify_api_key)):
    """2つの人格ベクトル間の相性をチェック"""
    body = await request.json()
    profile_a_id = body.get("profile_a_id")
    profile_b_id = body.get("profile_b_id")
    relationship_type = body.get("relationship_type", "general")

    # プロファイルIDが指定された場合はストアから取得
    if profile_a_id and profile_b_id:
        profile_a = personality_profiles.get(profile_a_id)
        profile_b = personality_profiles.get(profile_b_id)
        if not profile_a or not profile_b:
            raise HTTPException(status_code=404, detail="Profile not found")
        vec_a = profile_a.vector
        vec_b = profile_b.vector
    else:
        # 直接ベクトルが渡された場合
        vec_a = PersonalityVector(body.get("vector_a", {}))
        vec_b = PersonalityVector(body.get("vector_b", {}))

    result = compat_engine.check(vec_a, vec_b, relationship_type)
    return result

@app.post("/compatibility/report", tags=["compatibility"])
async def compatibility_report(request: Request, _=Depends(verify_api_key)):
    """相性レポートを生成"""
    body = await request.json()
    vec_a = PersonalityVector(body.get("vector_a", {}))
    vec_b = PersonalityVector(body.get("vector_b", {}))
    relationship_type = body.get("relationship_type", "general")

    result = compat_engine.check(vec_a, vec_b, relationship_type)
    report = compat_engine.get_report(result)
    return report
