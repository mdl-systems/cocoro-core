"""cocoro-core — E2E API テスト (FastAPI TestClient)
全APIエンドポイントをDB/Redis/LLMのモックなしで
HTTP層レベルでテストし、ルーティング・認証・入出力形式を検証する。
"""
import sys, os, types, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# --- テスト用にlifespanをバイパスしてappをインポート ---
# lifespan内のDB接続をスキップするため、
# asyncpg.create_pool をモックしてからインポートする

_mock_pool = AsyncMock()
_mock_pool.fetchrow = AsyncMock(return_value=None)
_mock_pool.fetch = AsyncMock(return_value=[])
_mock_pool.execute = AsyncMock(return_value="INSERT 0 1")
_mock_pool.close = AsyncMock()

# Emotion State モック
class MockEmotionState:
    happiness = 0.5
    sadness = 0.1
    anger = 0.0
    fear = 0.1
    trust = 0.6
    surprise = 0.2
    dominant = "neutral"
    intensity = 0.0
    def to_dict(self):
        return {
            "happiness": 0.5, "sadness": 0.1, "anger": 0.0,
            "fear": 0.1, "trust": 0.6, "surprise": 0.2,
            "dominant": "neutral", "intensity": 0.0,
        }

# Memory モック
class MockShortTerm:
    async def save(self, sid, role, content): return True
    async def get_context(self, sid, limit=20): return []

class MockLongTerm:
    async def save(self, content, **kw): return True
    async def search(self, query, limit=5): return []
    async def search_learnings(self, category=None): return []
    async def apply_learning(self, lesson, cat, imp): return True
    async def get_context_window(self, n=5): return []

class MockVectorMemory:
    async def search(self, query, limit=5): return []

class MockMemoryEngine:
    short = MockShortTerm()
    long = MockLongTerm()
    vector = MockVectorMemory()

# Emotion Engine モック
class MockEmotionEngine:
    async def get_state(self): return MockEmotionState()
    async def to_prompt(self): return ""
    async def adjust(self, label, intensity=0.5): return MockEmotionState().to_dict()
    def decay(self): pass
    async def get_history(self, limit=20): return []

# Personality Engine モック
class MockPersonality:
    emotion = MockEmotionEngine()
    identity = MagicMock()
    values = MagicMock()
    beliefs = MagicMock()
    goals = MagicMock()
    
    def build_system_prompt(self): return "You are AI."
    def get_creative_friction(self, sync_rate): return ""
    async def build_context(self, session_id): return ""
    def get_full_profile(self): return {"identity": {}, "values": [], "beliefs": []}

# Decision Engine モック
class MockDecision:
    def get_pipeline_info(self): return {"stages": ["memory", "value", "emotion", "decision"]}
    def build_classify_prompt(self, msg): return "classify"
    def parse_classification(self, r): return {"action": "chat", "confidence": 0.9}
    def build_decision_prompt(self, q, ctx): return "decide"
    def parse_decision(self, r): return {"decision": "ok"}
    async def record_decision(self, cat, q, r): pass

# Reasoning Engine モック
class MockReasoning:
    def build_reasoning_prompt(self, q): return "reason"
    def parse_reasoning(self, r): return {"reasoning": "because"}
    async def record_thought(self, q, r): pass

# Growth Tracker モック
class MockGrowth:
    async def get_growth_report(self): return {"personality_changes": 0}
    async def get_evolution_timeline(self, limit=20): return []
    async def calculate_sync_rate(self): return {"sync_rate": 75.0}
    async def record_sync_rate(self, rate): pass
    async def get_sync_rate_timeline(self, limit=20): return []


# === パッチを適用してappをインポート ===
with patch("asyncpg.create_pool", new_callable=AsyncMock, return_value=_mock_pool):
    from api.server import app, verify_api_key
    import api.server as server_module

# 認証をバイパス
async def _no_auth():
    return None

app.dependency_overrides[verify_api_key] = _no_auth

# グローバル変数にモックを設定
server_module.db_pool = _mock_pool
server_module.personality = MockPersonality()
server_module.memory = MockMemoryEngine()
server_module.reasoning = MockReasoning()
server_module.decision = MockDecision()
server_module.growth = MockGrowth()

# consolidation モック
server_module.consolidation = MagicMock()
server_module.consolidation.consolidate = AsyncMock(return_value={"status": "ok"})

# observer/evaluator/improver/meta_cognition
server_module.observer = MagicMock()
server_module.observer.get_recent = MagicMock(return_value=[])
server_module.observer.get_stats = MagicMock(return_value={"total": 0})
server_module.observer.observe_conversation = AsyncMock()
server_module.observer.observe_decision = AsyncMock()

server_module.evaluator = MagicMock()
server_module.evaluator.evaluate = AsyncMock(return_value={"score": 0.8})

server_module.improver = MagicMock()
server_module.improver.generate_plan = MagicMock(return_value={"plan": "improve"})
server_module.improver.execute_plan = AsyncMock(return_value={"status": "done"})
server_module.improver.get_plans = MagicMock(return_value=[])

server_module.meta_cognition = MagicMock()
server_module.meta_cognition.get_self_awareness = MagicMock(return_value={"level": "basic"})
server_module.meta_cognition.generate_strategy = MagicMock(return_value={"strategy": "learn"})
server_module.meta_cognition.get_long_term_plan = MagicMock(return_value={"plan": "grow"})

server_module.value_scoring = MagicMock()
server_module.value_scoring.score_response = MagicMock(return_value={"score": 0.9})
server_module.value_scoring.score_options = MagicMock(return_value={"scores": []})

server_module.intelligence = MagicMock()
server_module.intelligence.add_knowledge = MagicMock(return_value={"status": "added"})
server_module.intelligence.search_knowledge = MagicMock(return_value=[])
server_module.intelligence.get_skills = MagicMock(return_value=[])
server_module.intelligence.register_skill = MagicMock(return_value={"status": "registered"})
server_module.intelligence.get_tool_stats = MagicMock(return_value={"tools": 10})
server_module.intelligence.get_intelligence_report = MagicMock(return_value={"iq": 100})

server_module.safety = MagicMock()
server_module.safety.check_alignment = MagicMock(return_value={"aligned": True})
server_module.safety.check_modification_allowed = MagicMock(return_value={"allowed": True})
server_module.safety.get_safety_report = MagicMock(return_value={"safe": True})
server_module.safety.validate_and_rewrite = MagicMock(return_value={"text": "ok"})

server_module.cognitive = MagicMock()
server_module.cognitive.analyze = MagicMock(return_value={"profile": "analytical"})

server_module.calibration = MagicMock()
server_module.calibration.start_calibration = MagicMock(return_value={"question": "test?"})
server_module.calibration.submit_answers = MagicMock(return_value={"result": "ok"})
server_module.calibration.get_calibration_history = MagicMock(return_value=[])

server_module.clone_engine = MagicMock()
server_module.clone_engine.backup = AsyncMock(return_value={"backup_id": "abc"})
server_module.clone_engine.restore = AsyncMock(return_value={"status": "restored"})
server_module.clone_engine.get_diff = AsyncMock(return_value={"diff": []})

server_module.migration_runner = MagicMock()
server_module.migration_runner.get_status = AsyncMock(return_value={"current_version": 1})
server_module.migration_runner.migrate = AsyncMock(return_value={"status": "ok"})

server_module.org = MagicMock()
server_module.org.get_org_report = AsyncMock(return_value={"departments": 3})
server_module.org.list_departments = MagicMock(return_value=[])
server_module.org.list_agents = MagicMock(return_value=[])
server_module.org.register_agent = AsyncMock(return_value={"agent_id": "a1"})
server_module.org.delegate_task = AsyncMock(return_value={"task_id": "t1"})

server_module.governance = MagicMock()
server_module.governance.check_input = MagicMock(return_value={"allowed": True, "reason": "ok"})

server_module.tools = MagicMock()

# Boot wizard / sampling / test_bench are module-level
server_module.boot_wizard = MagicMock()
server_module.boot_wizard.start_session = MagicMock(return_value={"question": "hello?"})
server_module.boot_wizard.answer = MagicMock(return_value={"next": "q2"})
server_module.boot_wizard.get_progress = MagicMock(return_value={"progress": 50})
server_module.boot_wizard.get_result = MagicMock(return_value={"personality": {}})

server_module.sampling = MagicMock()
server_module.sampling.start = MagicMock(return_value={"question": "scenario?"})
server_module.sampling.answer = MagicMock(return_value={"next": "s2"})
server_module.sampling.get_result = MagicMock(return_value={"analysis": "ok"})

server_module.test_bench = MagicMock()
server_module.test_bench.start = MagicMock(return_value={"question": "q1?"})
server_module.test_bench.answer = MagicMock(return_value={"next": "q2"})
server_module.test_bench.get_score = MagicMock(return_value={"score": 85})

server_module.task_queue = MagicMock()
server_module.task_queue.execute_async = AsyncMock(return_value="task-123")
server_module.task_queue.get_result = AsyncMock(return_value=None)
server_module.task_queue.queue_length = AsyncMock(return_value=0)

server_module.event_bus = MagicMock()
server_module.worker = MagicMock()

# emotion_adapter / memory_archiver / plugin_registry
server_module.emotion_adapter = MagicMock()
server_module.emotion_adapter.get_full_adaptation = MagicMock(return_value={"creativity_boost": 0.5})
server_module.emotion_adapter.get_decision_threshold = MagicMock(return_value={"threshold": 0.7})
server_module.emotion_adapter.get_response_modifiers = MagicMock(return_value={"tone": "neutral"})

server_module.memory_archiver = MagicMock()
server_module.memory_archiver.get_stats = MagicMock(return_value={"total": 100})
server_module.memory_archiver.run_full_archive = AsyncMock(return_value={"archived": 5})
server_module.memory_archiver.get_archive_history = MagicMock(return_value=[])

server_module.plugin_registry = MagicMock()
server_module.plugin_registry.list_plugins = MagicMock(return_value=[])
server_module.plugin_registry.get_stats = MagicMock(return_value={"total": 4})
server_module.plugin_registry.execute = MagicMock(return_value={"result": 14})
server_module.plugin_registry.get_tool_definitions = MagicMock(return_value=[])

server_module.local_llm = MagicMock()
server_module.local_llm.list_models = AsyncMock(return_value=[])
server_module.local_llm.health_check = AsyncMock(return_value={"status": "ok"})
server_module.local_llm.switch_model = AsyncMock(return_value={"model": "gemma2:2b"})
server_module.local_llm.model_info = AsyncMock(return_value={"name": "gemma2:2b"})
server_module.local_llm.get_stats = AsyncMock(return_value={"provider": "ollama"})

server_module.user_manager = MagicMock()
server_module.user_manager.get_or_create_session = MagicMock(return_value=MagicMock(
    user_id="alice", session_id="sess-abc", display_name="Alice",
    message_count=0, to_dict=lambda: {"user_id": "alice", "session_id": "sess-abc"}
))
server_module.user_manager.end_session = MagicMock(return_value=True)
server_module.user_manager.list_active_sessions = MagicMock(return_value=[])
server_module.user_manager.set_preference = MagicMock()
server_module.user_manager.get_user_preferences = MagicMock(return_value={})
server_module.user_manager.get_stats = MagicMock(return_value={"active_sessions": 0})

server_module.peer_comm = MagicMock()
server_module.peer_comm.register_peer = MagicMock(return_value={"peer_id": "p1"})
server_module.peer_comm.list_peers = MagicMock(return_value=[])
server_module.peer_comm.start_discussion = MagicMock(return_value={"discussion_id": "d1"})
server_module.peer_comm.add_opinion = MagicMock(return_value={"added": True})
server_module.peer_comm.self_id = "cocoro-main"
server_module.peer_comm.conclude_discussion = MagicMock(return_value={"conclusion": "agreed"})
server_module.peer_comm.list_discussions = MagicMock(return_value=[])
server_module.peer_comm.send_message = MagicMock(return_value={"sent": True})
server_module.peer_comm.get_inbox = MagicMock(return_value=[])
server_module.peer_comm.get_stats = MagicMock(return_value={"peers": 0})


# === httpx の AsyncClient を使用 ===
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ╔══════════════════════════════════════════════════════════════════╗
# ║  E2E Tests — 全APIカテゴリ                                       ║
# ╚══════════════════════════════════════════════════════════════════╝

# === Health ===
class TestHealthE2E:
    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

# === Dashboard ===
class TestDashboardE2E:
    @pytest.mark.asyncio
    async def test_dashboard_returns_html(self, client):
        r = await client.get("/dashboard")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "cocoro" in r.text.lower()

# === Decision Pipeline ===
class TestDecisionPipelineE2E:
    @pytest.mark.asyncio
    async def test_pipeline_info(self, client):
        r = await client.get("/decide/pipeline")
        assert r.status_code == 200
        data = r.json()
        assert "stages" in data

# === Emotion ===
class TestEmotionE2E:
    @pytest.mark.asyncio
    async def test_emotion_current(self, client):
        r = await client.get("/emotion")
        assert r.status_code == 200
        data = r.json()
        assert "dominant" in data
        assert "happiness" in data

    @pytest.mark.asyncio
    async def test_emotion_state(self, client):
        r = await client.get("/emotion/state")
        assert r.status_code == 200
        data = r.json()
        assert data["dominant"] == "neutral"

    @pytest.mark.asyncio
    async def test_emotion_history(self, client):
        r = await client.get("/emotion/history")
        assert r.status_code == 200
        assert "history" in r.json()

    @pytest.mark.asyncio
    async def test_emotion_adaptation(self, client):
        r = await client.get("/emotion/adaptation")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_emotion_decision_threshold(self, client):
        r = await client.get("/emotion/decision-threshold")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_emotion_response_modifiers(self, client):
        r = await client.get("/emotion/response-modifiers")
        assert r.status_code == 200

# === Growth & Sync ===
class TestGrowthE2E:
    @pytest.mark.asyncio
    async def test_growth_report(self, client):
        r = await client.get("/growth/report")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_growth_timeline(self, client):
        r = await client.get("/growth/timeline")
        assert r.status_code == 200
        assert "timeline" in r.json()

    @pytest.mark.asyncio
    async def test_sync_rate(self, client):
        r = await client.get("/sync/rate")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_sync_timeline(self, client):
        r = await client.get("/sync/timeline")
        assert r.status_code == 200

# === Evolution ===
class TestEvolutionE2E:
    @pytest.mark.asyncio
    async def test_observe_recent(self, client):
        r = await client.get("/observe/recent")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_observe_stats(self, client):
        r = await client.get("/observe/stats")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_evolve_evaluate(self, client):
        r = await client.post("/evolve/evaluate")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_evolve_dashboard(self, client):
        r = await client.get("/evolve/dashboard")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_evolve_metacognition(self, client):
        r = await client.get("/evolve/metacognition")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_evolve_intelligence(self, client):
        r = await client.get("/evolve/intelligence")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_evolve_safety(self, client):
        r = await client.get("/evolve/safety")
        assert r.status_code == 200

# === Personality Testing ===
class TestPersonalityTestingE2E:
    @pytest.mark.asyncio
    async def test_boot_start(self, client):
        r = await client.post("/boot/start")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_boot_progress(self, client):
        r = await client.get("/boot/progress")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_calibrate_start(self, client):
        r = await client.post("/calibrate/start")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_calibrate_report(self, client):
        r = await client.get("/calibrate/report")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_test_bench_start(self, client):
        r = await client.post("/test/bench/start")
        assert r.status_code == 200

# === Cognitive Profile ===
class TestCognitiveE2E:
    @pytest.mark.asyncio
    async def test_cognitive_profile(self, client):
        r = await client.get("/cognitive/profile")
        assert r.status_code == 200

# === Clone ===
class TestCloneE2E:
    @pytest.mark.asyncio
    async def test_clone_backup(self, client):
        r = await client.get("/clone/backup")
        assert r.status_code == 200

# === Migration ===
class TestMigrationE2E:
    @pytest.mark.asyncio
    async def test_migrate_status(self, client):
        r = await client.get("/migrate/status")
        assert r.status_code == 200

# === Plugins (C-5) ===
class TestPluginsE2E:
    @pytest.mark.asyncio
    async def test_plugins_list(self, client):
        r = await client.get("/plugins")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_plugins_execute(self, client):
        r = await client.post("/plugins/execute",
            json={"name": "math", "args": {"expression": "2+3"}})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_plugins_tools(self, client):
        r = await client.get("/plugins/tools")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_plugins_stats(self, client):
        r = await client.get("/plugins/stats")
        assert r.status_code == 200

# === Local LLM (C-4) ===
class TestLocalLLME2E:
    @pytest.mark.asyncio
    async def test_llm_models(self, client):
        r = await client.get("/llm/local/models")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_llm_health(self, client):
        r = await client.get("/llm/local/health")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_llm_stats(self, client):
        r = await client.get("/llm/local/stats")
        assert r.status_code == 200

# === Multi-User (C-2) ===
class TestMultiUserE2E:
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        r = await client.post("/users/session",
            json={"user_id": "alice", "display_name": "Alice"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_sessions(self, client):
        r = await client.get("/users/sessions")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_user_stats(self, client):
        r = await client.get("/users/stats")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_set_preference(self, client):
        r = await client.post("/users/preference",
            json={"user_id": "alice", "key": "tone", "value": "casual"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences(self, client):
        r = await client.get("/users/preferences/alice")
        assert r.status_code == 200

# === Peer Communication (C-3) ===
class TestPeerCommE2E:
    @pytest.mark.asyncio
    async def test_register_peer(self, client):
        r = await client.post("/comm/peer",
            json={"name": "peer-1", "endpoint": "http://peer:8000", "personality_summary": "kind AI"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_peers(self, client):
        r = await client.get("/comm/peers")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_start_discussion(self, client):
        r = await client.post("/comm/discussion",
            json={"topic": "Should we be creative?", "participants": ["peer-1"]})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_discussions(self, client):
        r = await client.get("/comm/discussions")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_send_message(self, client):
        r = await client.post("/comm/message",
            json={"to": "peer-1", "content": "Hello!", "msg_type": "general"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_inbox(self, client):
        r = await client.get("/comm/inbox")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_comm_stats(self, client):
        r = await client.get("/comm/stats")
        assert r.status_code == 200

# === Voice Interface (C-8) ===
class TestVoiceE2E:
    @pytest.mark.asyncio
    async def test_voice_parse(self, client):
        r = await client.post("/voice/parse", json={"text": "こんにちは"})
        assert r.status_code == 200
        assert "type" in r.json()

    @pytest.mark.asyncio
    async def test_voice_speak(self, client):
        r = await client.post("/voice/speak",
            json={"text": "テスト", "emotion": "happiness", "intensity": 0.5})
        assert r.status_code == 200
        data = r.json()
        assert "voice_params" in data
        assert "chunks" in data

    @pytest.mark.asyncio
    async def test_voice_settings_get(self, client):
        r = await client.get("/voice/settings")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_voice_settings_update(self, client):
        r = await client.post("/voice/settings", json={"rate": 1.2})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_voice_stats(self, client):
        r = await client.get("/voice/stats")
        assert r.status_code == 200

# === Organization ===
class TestOrganizationE2E:
    @pytest.mark.asyncio
    async def test_org_report(self, client):
        r = await client.get("/org/report")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_org_departments(self, client):
        r = await client.get("/org/departments")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_list(self, client):
        r = await client.get("/agent/list")
        assert r.status_code == 200

# === Memory (C-7) ===
class TestMemoryE2E:
    @pytest.mark.asyncio
    async def test_memory_stats(self, client):
        r = await client.get("/memory/stats")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_memory_archive_history(self, client):
        r = await client.get("/memory/archive/history")
        assert r.status_code == 200

# === Value Scoring ===
class TestValueScoringE2E:
    @pytest.mark.asyncio
    async def test_score_response(self, client):
        r = await client.post("/value/score",
            json={"response": "I think we should help.", "context": "question about charity"})
        assert r.status_code == 200

# === Intelligence Engine ===
class TestIntelligenceE2E:
    @pytest.mark.asyncio
    async def test_intelligence_report(self, client):
        r = await client.get("/evolve/intelligence")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_knowledge_search(self, client):
        r = await client.get("/intelligence/knowledge/search?query=test")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_skills_list(self, client):
        r = await client.get("/intelligence/skills")
        assert r.status_code == 200

# === Safety ===
class TestSafetyE2E:
    @pytest.mark.asyncio
    async def test_safety_alignment(self, client):
        r = await client.post("/safety/alignment",
            json={"text": "hello world"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_safety_report(self, client):
        r = await client.get("/evolve/safety")
        assert r.status_code == 200

# === Queue Status ===
class TestQueueE2E:
    @pytest.mark.asyncio
    async def test_queue_status(self, client):
        r = await client.get("/queue/status")
        assert r.status_code == 200


# === 認証テスト ===
class TestAuthE2E:
    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client):
        """healthは認証不要"""
        r = await client.get("/health")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_no_auth_required(self, client):
        """dashboardは認証不要"""
        r = await client.get("/dashboard")
        assert r.status_code == 200


# === エラーケーステスト ===
class TestErrorCasesE2E:
    @pytest.mark.asyncio
    async def test_404_not_found(self, client):
        r = await client.get("/nonexistent/endpoint")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_json_body(self, client):
        r = await client.post("/voice/parse", content=b"not json",
            headers={"content-type": "application/json"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_voice_parse(self, client):
        r = await client.post("/voice/parse", json={"text": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "conversation"

# === レスポンス形式テスト ===
class TestResponseFormatE2E:
    @pytest.mark.asyncio
    async def test_json_content_type(self, client):
        """APIはJSON形式で応答する"""
        r = await client.get("/emotion/state")
        assert "application/json" in r.headers["content-type"]

    @pytest.mark.asyncio
    async def test_dashboard_html_content_type(self, client):
        """ダッシュボードはHTML形式で応答する"""
        r = await client.get("/dashboard")
        assert "text/html" in r.headers["content-type"]
