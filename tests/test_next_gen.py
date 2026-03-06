"""cocoro-core — C-1/C-2/C-3/C-4/C-5/C-6/C-7/C-8 テスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from brain.tools.plugin_system import PluginRegistry, register_builtin_plugins
from personality.emotion_adapter import EmotionBehaviorAdapter
from personality.multi_user import MultiUserManager, UserSession
from personality.peer_communication import PersonalityCommunication
from brain.local_llm import LocalLLMManager
from personality.voice_interface import VoiceInterface


# === C-5: Plugin System ===
class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register(self):
        async def handler(args):
            return {"ok": True}
        result = self.registry.register("test", "desc", {}, handler)
        assert result is True
        assert len(self.registry.list_plugins()) == 1

    def test_unregister(self):
        async def handler(args):
            return {}
        self.registry.register("test", "desc", {}, handler)
        result = self.registry.unregister("test")
        assert result is True
        assert len(self.registry.list_plugins()) == 0

    def test_unregister_not_found(self):
        assert self.registry.unregister("nonexistent") is False

    def test_disable_enable(self):
        async def handler(args):
            return {}
        self.registry.register("test", "desc", {}, handler)
        self.registry.disable("test")
        plugins = self.registry.list_plugins()
        assert plugins[0]["enabled"] is False
        self.registry.enable("test")
        plugins = self.registry.list_plugins()
        assert plugins[0]["enabled"] is True

    def test_get_tool_definitions(self):
        async def handler(args):
            return {}
        self.registry.register("enabled", "desc1", {"a": "b"}, handler)
        self.registry.register("disabled", "desc2", {"c": "d"}, handler)
        self.registry.disable("disabled")
        defs = self.registry.get_tool_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "enabled"

    def test_builtin_plugins(self):
        register_builtin_plugins(self.registry)
        plugins = self.registry.list_plugins()
        names = [p["name"] for p in plugins]
        assert "echo" in names
        assert "math" in names
        assert "text_stats" in names

    def test_get_stats(self):
        register_builtin_plugins(self.registry)
        stats = self.registry.get_stats()
        assert stats["total"] == 3
        assert stats["enabled"] == 3
        assert "system" in stats["categories"]
        assert "utility" in stats["categories"]


# === C-6: Emotion Behavior Adapter ===
class MockEmotionState:
    def __init__(self, _dominant="neutral", _intensity=0.0, **kwargs):
        self._dominant = _dominant
        self._intensity = _intensity
        for k, v in kwargs.items():
            setattr(self, k, v)

    def dominant(self):
        return self._dominant

    def intensity(self):
        return self._intensity

    def to_dict(self):
        return {"dominant": self._dominant, "intensity": round(self._intensity, 3)}


class MockEmotion:
    def __init__(self, state):
        self._state = state

    async def get_state(self):
        return self._state


class MockPersonality:
    def __init__(self, emotion_state):
        self.emotion = MockEmotion(emotion_state)


import pytest

class TestEmotionBehaviorAdapter:
    @pytest.mark.asyncio
    async def test_neutral_profile(self):
        state = MockEmotionState("neutral", 0.0)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        profile = await adapter.get_behavior_profile(state)
        assert profile["response_tone"] == "balanced"
        assert profile["dominant_emotion"] == "neutral"

    @pytest.mark.asyncio
    async def test_happiness_profile(self):
        state = MockEmotionState("happiness", 0.5)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        profile = await adapter.get_behavior_profile(state)
        assert profile["response_tone"] == "positive"
        assert profile["risk_tolerance"] > 0.4

    @pytest.mark.asyncio
    async def test_fear_profile(self):
        state = MockEmotionState("fear", 0.5)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        profile = await adapter.get_behavior_profile(state)
        assert profile["response_tone"] == "cautious"
        assert profile["risk_tolerance"] < 0.3

    @pytest.mark.asyncio
    async def test_decision_threshold(self):
        state = MockEmotionState("anger", 0.6)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        threshold = await adapter.get_decision_threshold(state)
        assert "confidence_required" in threshold
        assert "risk_tolerance" in threshold
        assert "speed" in threshold

    @pytest.mark.asyncio
    async def test_response_modifiers(self):
        state = MockEmotionState("sadness", 0.4)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        mods = await adapter.get_response_modifiers(state)
        assert mods["tone"] == "gentle"
        assert "tone_directive" in mods
        assert "temperature_modifier" in mods

    @pytest.mark.asyncio
    async def test_full_adaptation(self):
        state = MockEmotionState("surprise", 0.7)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        full = await adapter.get_full_adaptation(state)
        assert "behavior" in full
        assert "decision" in full
        assert "response" in full
        assert "emotion_state" in full

    @pytest.mark.asyncio
    async def test_low_intensity_blending(self):
        state = MockEmotionState("happiness", 0.05)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        profile = await adapter.get_behavior_profile(state)
        # 低強度はニュートラルに近づく
        neutral_risk = 0.4
        assert abs(profile["risk_tolerance"] - neutral_risk) < 0.2

    @pytest.mark.asyncio
    async def test_high_intensity_amplification(self):
        state = MockEmotionState("anger", 0.9)
        adapter = EmotionBehaviorAdapter(MockPersonality(state))
        profile = await adapter.get_behavior_profile(state)
        # 高強度はリスク許容度が増幅
        assert profile["risk_tolerance"] > 0.7


# === C-2: Multi-User Manager ===
class TestMultiUserManager:
    def setup_method(self):
        self.mgr = MultiUserManager(db=None)

    def test_create_session(self):
        session = self.mgr.get_or_create_session("user1", "Alice")
        assert session.user_id == "user1"
        assert session.display_name == "Alice"
        assert session.message_count == 0

    def test_session_reuse(self):
        s1 = self.mgr.get_or_create_session("user1")
        s2 = self.mgr.get_or_create_session("user1")
        assert s1.session_id == s2.session_id
        assert s2.message_count == 1  # touch() increments

    def test_end_session(self):
        self.mgr.get_or_create_session("user1")
        assert self.mgr.end_session("user1") is True
        assert self.mgr.end_session("user1") is False

    def test_preferences(self):
        self.mgr.set_preference("user1", "tone", "casual")
        assert self.mgr.get_preference("user1", "tone") == "casual"
        assert self.mgr.get_preference("user1", "missing", "default") == "default"

    def test_stats(self):
        self.mgr.get_or_create_session("u1")
        self.mgr.get_or_create_session("u2")
        stats = self.mgr.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2

    def test_prompt_prefix(self):
        self.mgr.get_or_create_session("user1", "Alice")
        self.mgr.set_preference("user1", "tone", "formal")
        prefix = self.mgr.build_user_prompt_prefix("user1")
        assert "Alice" in prefix
        assert "formal" in prefix


# === C-3: Personality Communication ===
class TestPersonalityCommunication:
    def setup_method(self):
        self.comm = PersonalityCommunication("cocoro-test")

    def test_register_peer(self):
        result = self.comm.register_peer("peer1", "Cocoro-2")
        assert result["peer_id"] == "peer1"
        assert result["name"] == "Cocoro-2"

    def test_list_peers(self):
        self.comm.register_peer("p1", "Peer1")
        self.comm.register_peer("p2", "Peer2")
        peers = self.comm.list_peers()
        assert len(peers) == 2

    def test_unregister_peer(self):
        self.comm.register_peer("p1", "Peer1")
        assert self.comm.unregister_peer("p1") is True
        assert self.comm.unregister_peer("p1") is False

    def test_discussion_flow(self):
        disc = self.comm.start_discussion("Should we be cautious?")
        did = disc["discussion_id"]
        self.comm.add_opinion(did, "cocoro-test", "Yes, safety first", "agree")
        self.comm.add_opinion(did, "peer1", "No, be bold", "disagree")
        result = self.comm.conclude_discussion(did, "Balance caution with action")
        assert result["status"] == "concluded"
        assert result["message_count"] == 2

    def test_direct_message(self):
        self.comm.register_peer("p1", "Peer1")
        msg = self.comm.send_message("p1", "Hello!")
        assert msg["from"] == "cocoro-test"
        assert msg["to"] == "p1"

    def test_receive_message(self):
        msg = self.comm.receive_message("p1", "Hi there")
        assert msg["from"] == "p1"
        inbox = self.comm.get_inbox()
        assert len(inbox) == 1

    def test_stats(self):
        self.comm.register_peer("p1", "Peer1")
        self.comm.start_discussion("Topic")
        stats = self.comm.get_stats()
        assert stats["peer_count"] == 1
        assert stats["total_discussions"] == 1

    def test_consensus_prompt(self):
        disc = self.comm.start_discussion("Ethics question")
        did = disc["discussion_id"]
        self.comm.add_opinion(did, "cocoro-test", "Safety matters")
        prompt = self.comm.build_consensus_prompt(did)
        assert "Ethics question" in prompt
        assert "Safety matters" in prompt


# === C-4: Local LLM Manager ===
class TestLocalLLMManager:
    def test_init(self):
        mgr = LocalLLMManager("http://localhost:11434", "gemma2:2b")
        assert mgr.current_model == "gemma2:2b"
        assert mgr.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_health_check_offline(self):
        mgr = LocalLLMManager("http://localhost:99999", "test")
        health = await mgr.health_check()
        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_list_models_offline(self):
        mgr = LocalLLMManager("http://localhost:99999", "test")
        models = await mgr.list_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_get_stats_offline(self):
        mgr = LocalLLMManager("http://localhost:99999", "test")
        stats = await mgr.get_stats()
        assert stats["provider"] == "ollama"
        assert stats["healthy"] is False


# === C-8: Voice Interface ===
class TestVoiceInterface:
    def setup_method(self):
        self.voice = VoiceInterface()

    def test_default_params(self):
        params = self.voice.get_voice_params()
        assert params["rate"] == 1.0
        assert params["pitch"] == 1.0
        assert params["lang"] == "ja-JP"
        assert params["muted"] is False

    def test_happiness_params(self):
        params = self.voice.get_voice_params("happiness", 0.8)
        assert params["rate"] > 1.0
        assert params["pitch"] > 1.0

    def test_sadness_params(self):
        params = self.voice.get_voice_params("sadness", 0.7)
        assert params["rate"] < 1.0
        assert params["pitch"] < 1.0

    def test_parse_greeting(self):
        result = self.voice.parse_command("こんにちは")
        assert result["type"] == "greeting"

    def test_parse_emotion_check(self):
        result = self.voice.parse_command("今の気持ちを教えて")
        assert result["type"] == "emotion_check"

    def test_parse_unknown(self):
        result = self.voice.parse_command("今日の天気は")
        assert result["type"] == "conversation"

    def test_settings(self):
        result = self.voice.set_settings(rate=1.5, muted=True)
        assert result["rate"] == 1.5
        assert result["muted"] is True

    def test_prepare_speech(self):
        result = self.voice.prepare_speech("テストメッセージ", "happiness", 0.5)
        assert result["text"] == "テストメッセージ"
        assert result["chunk_count"] >= 1
        assert "voice_params" in result

    def test_stats(self):
        self.voice.parse_command("こんにちは")
        stats = self.voice.get_stats()
        assert stats["commands_processed"] == 1
