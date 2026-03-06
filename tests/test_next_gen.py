"""cocoro-core — C-5/C-6/C-7 テスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from brain.tools.plugin_system import PluginRegistry, register_builtin_plugins
from personality.emotion_adapter import EmotionBehaviorAdapter


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

