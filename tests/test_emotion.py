"""cocoro-core — Emotion Engine のテスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock, MagicMock

from personality.emotion.emotion_engine import (
    EmotionState, EmotionEngine,
    EMOTION_LABEL_MAP, NEUTRAL_VALUES, DECAY_RATE, EMOTION_FIELDS,
)


# === EmotionState (純粋データクラス) ===
class TestEmotionState:
    def test_default_values(self):
        s = EmotionState()
        assert s.happiness == 0.5
        assert s.sadness == 0.1
        assert s.anger == 0.0
        assert s.fear == 0.1
        assert s.trust == 0.6
        assert s.surprise == 0.2

    def test_dominant_neutral(self):
        """デフォルト状態は neutral"""
        s = EmotionState()
        assert s.dominant() == "neutral"

    def test_dominant_happiness(self):
        """happiness を高くすると dominant が happiness になる"""
        s = EmotionState(happiness=0.9)
        assert s.dominant() == "happiness"

    def test_dominant_anger(self):
        """anger を高くすると dominant が anger になる"""
        s = EmotionState(anger=0.5)
        assert s.dominant() == "anger"

    def test_dominant_sadness(self):
        s = EmotionState(sadness=0.6)
        assert s.dominant() == "sadness"

    def test_dominant_fear(self):
        s = EmotionState(fear=0.5)
        assert s.dominant() == "fear"

    def test_dominant_trust(self):
        s = EmotionState(trust=0.95)
        assert s.dominant() == "trust"

    def test_dominant_surprise(self):
        s = EmotionState(surprise=0.7)
        assert s.dominant() == "surprise"

    def test_dominant_threshold(self):
        """偏差 < 0.15 の場合は neutral"""
        s = EmotionState(happiness=0.6)  # delta=0.1 < 0.15
        assert s.dominant() == "neutral"

    def test_to_dict_contains_dominant(self):
        s = EmotionState()
        d = s.to_dict()
        assert "dominant" in d
        assert d["dominant"] == "neutral"

    def test_to_dict_rounds_floats(self):
        """to_dict は float を 3桁に丸める"""
        s = EmotionState(happiness=0.123456789)
        d = s.to_dict()
        assert d["happiness"] == 0.123

    def test_to_dict_all_fields(self):
        d = EmotionState().to_dict()
        for f in EMOTION_FIELDS:
            assert f in d

    def test_intensity_neutral(self):
        """中立状態の intensity はほぼ 0"""
        s = EmotionState()
        assert s.intensity() < 0.01

    def test_intensity_high(self):
        """極端な感情は intensity が高い"""
        s = EmotionState(happiness=1.0, anger=1.0, fear=1.0)
        assert s.intensity() > 0.3


# === EMOTION_LABEL_MAP ===
class TestEmotionLabelMap:
    def test_happy_mapping(self):
        deltas = EMOTION_LABEL_MAP["happy"]
        assert deltas["happiness"] > 0
        assert "sadness" in deltas

    def test_sad_mapping(self):
        deltas = EMOTION_LABEL_MAP["sad"]
        assert deltas["sadness"] > 0
        assert deltas["happiness"] < 0

    def test_neutral_no_change(self):
        deltas = EMOTION_LABEL_MAP["neutral"]
        assert deltas == {}

    def test_all_labels_valid_fields(self):
        """全ラベルのフィールドが EmotionState の属性と一致"""
        for label, deltas in EMOTION_LABEL_MAP.items():
            for field in deltas:
                assert field in EMOTION_FIELDS, f"{label} has invalid field: {field}"


# === EmotionEngine (DB モック) ===
class TestEmotionEngine:
    def setup_method(self):
        self.db = MagicMock()
        self.engine = EmotionEngine(self.db)

    @pytest.mark.asyncio
    async def test_get_state_default(self):
        """DB に行が無い場合はデフォルト状態"""
        self.db.fetchrow = AsyncMock(return_value=None)
        state = await self.engine.get_state()
        assert state.happiness == 0.5
        assert state.dominant() == "neutral"

    @pytest.mark.asyncio
    async def test_get_state_from_db(self):
        """DB から感情状態を復元"""
        self.db.fetchrow = AsyncMock(return_value={
            "happiness": 0.8, "sadness": 0.2, "anger": 0.1,
            "fear": 0.05, "trust": 0.7, "surprise": 0.3,
        })
        state = await self.engine.get_state()
        assert state.happiness == 0.8
        assert state.trust == 0.7

    @pytest.mark.asyncio
    async def test_adjust_happy(self):
        """happy ラベルで happiness が上がる"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        result = await self.engine.adjust("happy")
        assert result["after"]["happiness"] > result["before"]["happiness"]
        assert "adjustments" in result

    @pytest.mark.asyncio
    async def test_adjust_sad(self):
        """sad ラベルで sadness が上がり happiness が下がる"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        result = await self.engine.adjust("sad")
        assert result["after"]["sadness"] > result["before"]["sadness"]
        assert result["after"]["happiness"] < result["before"]["happiness"]

    @pytest.mark.asyncio
    async def test_adjust_unknown_label(self):
        """未知のラベルは変化なし"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        result = await self.engine.adjust("unknown_label")
        assert result["adjustments"] == {}
        assert result["before"] == result["after"]

    @pytest.mark.asyncio
    async def test_adjust_intensity_amplifies(self):
        """intensity > 1.0 で変化が増幅される"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        r1 = await self.engine.adjust("happy", intensity=1.0)
        # reset cache
        self.engine._cache = None
        r2 = await self.engine.adjust("happy", intensity=2.0)
        # intensity=2.0 の delta は 1.0 の 2倍
        delta1 = r1["adjustments"]["happiness"]["delta"]
        delta2 = r2["adjustments"]["happiness"]["delta"]
        assert abs(delta2 - delta1 * 2) < 0.001

    @pytest.mark.asyncio
    async def test_adjust_clamps_to_range(self):
        """値は 0.0-1.0 にクランプされる"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        # 大きな intensity で上限テスト
        result = await self.engine.adjust("happy", intensity=50.0)
        assert result["after"]["happiness"] <= 1.0
        assert result["after"]["happiness"] >= 0.0

    @pytest.mark.asyncio
    async def test_decay(self):
        """decay で中立値に向かう"""
        # happiness=0.8 → 中立 0.5 に向かって減衰
        self.db.fetchrow = AsyncMock(return_value={
            "happiness": 0.8, "sadness": 0.1, "anger": 0.0,
            "fear": 0.1, "trust": 0.6, "surprise": 0.2,
        })
        self.db.execute = AsyncMock()
        result = await self.engine.decay()
        # happiness は 0.8 → 0.77 (0.8 - 0.1*(0.8-0.5)) に近づく
        assert result["after"]["happiness"] < 0.8
        assert result["after"]["happiness"] > 0.5

    @pytest.mark.asyncio
    async def test_decay_neutral_no_change(self):
        """中立状態では decay しても変化しない"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        result = await self.engine.decay()
        assert result["before"]["happiness"] == result["after"]["happiness"]

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """adjust 後にキャッシュがクリアされる"""
        self.db.fetchrow = AsyncMock(return_value=None)
        self.db.execute = AsyncMock()
        # 最初の get_state でキャッシュ
        await self.engine.get_state()
        assert self.engine._cache is not None
        # adjust でキャッシュがクリアされない（_save_state で上書き）
        await self.engine.adjust("happy")
        # adjust 後の cache は更新された状態
        assert self.engine._cache.happiness > 0.5
