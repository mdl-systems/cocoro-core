"""cocoro-core — Personality Engine + Observation のテスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from personality.personality_engine import PersonalityEngine
from evolution.self_observation import SelfObservationEngine, OBSERVATION_TYPES


# === PersonalityEngine ===
class TestPersonalityEngine:
    def setup_method(self):
        self.db = MagicMock()
        self.engine = PersonalityEngine(self.db)

    def test_has_all_components(self):
        """6つの人格要素が全て初期化される"""
        assert self.engine.identity is not None
        assert self.engine.values is not None
        assert self.engine.beliefs is not None
        assert self.engine.history is not None
        assert self.engine.emotion is not None
        assert self.engine.goals is not None

    @pytest.mark.asyncio
    async def test_build_system_prompt_structure(self):
        """build_system_prompt が全要素を統合する"""
        self.engine.identity.to_prompt = AsyncMock(return_value="【アイデンティティ】テスト")
        self.engine.values.to_prompt = AsyncMock(return_value="【価値観】テスト")
        self.engine.beliefs.to_prompt = AsyncMock(return_value="【信念】テスト")
        self.engine.history.to_prompt = AsyncMock(return_value="【経験】テスト")
        self.engine.emotion.to_prompt = AsyncMock(return_value="【感情】テスト")
        self.engine.goals.to_prompt = AsyncMock(return_value="【目標】テスト")
        self.engine.emotion.get_state = AsyncMock(return_value=MagicMock(
            dominant=lambda: "neutral", intensity=lambda: 0.0))

        prompt = await self.engine.build_system_prompt()
        assert "【アイデンティティ】テスト" in prompt
        assert "【価値観】テスト" in prompt
        assert "【信念】テスト" in prompt
        assert "【経験】テスト" in prompt
        assert "【感情】テスト" in prompt
        assert "【目標】テスト" in prompt
        assert "人格の一貫性を最優先" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_emotion_tone(self):
        """感情が強い場合にトーン指示が追加される"""
        self.engine.identity.to_prompt = AsyncMock(return_value="")
        self.engine.values.to_prompt = AsyncMock(return_value="")
        self.engine.beliefs.to_prompt = AsyncMock(return_value="")
        self.engine.history.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.to_prompt = AsyncMock(return_value="")
        self.engine.goals.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.get_state = AsyncMock(return_value=MagicMock(
            dominant=lambda: "happiness", intensity=lambda: 0.3))

        prompt = await self.engine.build_system_prompt()
        assert "前向き" in prompt or "温かく" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_fear_tone(self):
        """fear 感情 → 慎重なトーン"""
        self.engine.identity.to_prompt = AsyncMock(return_value="")
        self.engine.values.to_prompt = AsyncMock(return_value="")
        self.engine.beliefs.to_prompt = AsyncMock(return_value="")
        self.engine.history.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.to_prompt = AsyncMock(return_value="")
        self.engine.goals.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.get_state = AsyncMock(return_value=MagicMock(
            dominant=lambda: "fear", intensity=lambda: 0.3))

        prompt = await self.engine.build_system_prompt()
        assert "慎重" in prompt or "警戒" in prompt or "リスク" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_neutral_no_tone(self):
        """neutral 感情ではトーン指示なし"""
        self.engine.identity.to_prompt = AsyncMock(return_value="")
        self.engine.values.to_prompt = AsyncMock(return_value="")
        self.engine.beliefs.to_prompt = AsyncMock(return_value="")
        self.engine.history.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.to_prompt = AsyncMock(return_value="")
        self.engine.goals.to_prompt = AsyncMock(return_value="")
        self.engine.emotion.get_state = AsyncMock(return_value=MagicMock(
            dominant=lambda: "neutral", intensity=lambda: 0.0))

        prompt = await self.engine.build_system_prompt()
        assert "【感情トーン指示】" not in prompt


# === SelfObservationEngine ===
class TestSelfObservation:
    def test_observation_types(self):
        """8カテゴリの観察タイプが定義されている"""
        assert len(OBSERVATION_TYPES) == 8
        assert "conversation" in OBSERVATION_TYPES
        assert "decision" in OBSERVATION_TYPES
        assert "task_success" in OBSERVATION_TYPES
        assert "task_failure" in OBSERVATION_TYPES
        assert "emotion_change" in OBSERVATION_TYPES

    @pytest.mark.asyncio
    async def test_observe_basic(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={
            "id": 1, "obs_type": "conversation", "summary": "test"})
        engine = SelfObservationEngine(db)
        result = await engine.observe("conversation", "テスト会話")
        assert result["obs_type"] == "conversation"

    @pytest.mark.asyncio
    async def test_observe_invalid_type_fallback(self):
        """不正なタイプは conversation にフォールバック"""
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={
            "id": 1, "obs_type": "conversation", "summary": "test"})
        engine = SelfObservationEngine(db)
        await engine.observe("invalid_type", "テスト")
        # fetchrow が呼ばれた際の第2引数(obs_type)が "conversation" であること
        call_args = db.fetchrow.call_args[0]
        assert "conversation" in call_args[1] or call_args[1] == "conversation"

    @pytest.mark.asyncio
    async def test_observe_conversation(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 1, "obs_type": "conversation", "summary": "s"})
        engine = SelfObservationEngine(db)
        result = await engine.observe_conversation("sess-123", "ユーザー入力", "AI応答", "happy")
        assert result["obs_type"] == "conversation"

    @pytest.mark.asyncio
    async def test_observe_decision(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 2, "obs_type": "decision", "summary": "s"})
        engine = SelfObservationEngine(db)
        result = await engine.observe_decision("コンテキスト", "判断内容", confidence=0.8)
        assert result["obs_type"] == "decision"

    @pytest.mark.asyncio
    async def test_observe_task_success(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 3, "obs_type": "task_success", "summary": "s"})
        engine = SelfObservationEngine(db)
        result = await engine.observe_task("task-1", "dev", success=True, duration_ms=500)
        assert result["obs_type"] == "task_success"

    @pytest.mark.asyncio
    async def test_observe_task_failure_higher_impact(self):
        """失敗タスクは impact が高い (7)、成功は低い (4)"""
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 4, "obs_type": "task_failure", "summary": "s"})
        engine = SelfObservationEngine(db)
        await engine.observe_task("task-1", "dev", success=False)
        # observe が impact=7 で呼ばれたことを確認
        call_args = db.fetchrow.call_args[0]
        assert call_args[4] == 7  # impact パラメータ

    @pytest.mark.asyncio
    async def test_observe_emotion_change(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 5, "obs_type": "emotion_change", "summary": "s"})
        engine = SelfObservationEngine(db)
        result = await engine.observe_emotion_change(
            {"happiness": 0.5}, {"happiness": 0.8}, "good news")
        assert result["obs_type"] == "emotion_change"

    @pytest.mark.asyncio
    async def test_observe_value_change(self):
        db = MagicMock()
        db.fetchrow = AsyncMock(return_value={"id": 6, "obs_type": "value_change", "summary": "s"})
        engine = SelfObservationEngine(db)
        result = await engine.observe_value_change("honesty", 0.8, 0.85)
        assert result["obs_type"] == "value_change"
