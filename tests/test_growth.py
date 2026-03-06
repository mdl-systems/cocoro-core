"""cocoro-core — Growth Tracker / Sync Rate のテスト"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock, MagicMock

from personality.growth_tracker import (
    _cosine_similarity, _gradient_step, adaptive_learning_rate,
    DIVERGENCE_CEILING,
)


# === cosine_similarity ===
class TestCosineSimilarity:
    def test_identical_vectors(self):
        """同一ベクトルの類似度は 1.0"""
        a = [0.5, 0.7, 0.9]
        assert abs(_cosine_similarity(a, a) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """直交ベクトルの類似度は 0.0"""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 0.001

    def test_opposite_vectors(self):
        """逆向きベクトルの類似度は -1.0"""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) + 1.0) < 0.001

    def test_empty_vectors(self):
        assert _cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_known_value(self):
        """既知の値で検証"""
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        expected = (4 + 10 + 18) / (math.sqrt(14) * math.sqrt(77))
        assert abs(_cosine_similarity(a, b) - expected) < 0.001


# === gradient_step ===
class TestGradientStep:
    def test_step_toward_ideal(self):
        """current < ideal → current が増加"""
        result = _gradient_step(0.5, 0.9, 0.1)
        assert result > 0.5

    def test_step_away_from_high(self):
        """current > ideal → current が減少"""
        result = _gradient_step(0.9, 0.5, 0.1)
        assert result < 0.9

    def test_at_ideal_no_change(self):
        """current == ideal → 変化なし"""
        result = _gradient_step(0.7, 0.7, 0.1)
        assert result == 0.7

    def test_clamp_high(self):
        """結果は 1.0 を超えない"""
        result = _gradient_step(0.99, 1.0, 10.0)
        assert result <= 1.0

    def test_clamp_low(self):
        """結果は 0.0 を下回らない"""
        result = _gradient_step(0.01, 0.0, 10.0)
        assert result >= 0.0


# === adaptive_learning_rate ===
class TestAdaptiveLearningRate:
    def test_low_sync_accelerate(self):
        """sync < 70 → base_lr * 1.5"""
        lr = adaptive_learning_rate(50.0, base_lr=0.02)
        assert lr == 0.03

    def test_mid_sync_normal(self):
        """70 <= sync < 85 → base_lr"""
        lr = adaptive_learning_rate(75.0, base_lr=0.02)
        assert lr == 0.02

    def test_high_sync_decelerate(self):
        """85 <= sync < 92 → base_lr * 0.3"""
        lr = adaptive_learning_rate(88.0, base_lr=0.02)
        assert abs(lr - 0.006) < 0.001

    def test_over_ceiling_stop(self):
        """sync >= 92 → 0.0"""
        lr = adaptive_learning_rate(95.0, base_lr=0.02)
        assert lr == 0.0

    def test_at_ceiling_stop(self):
        """sync == DIVERGENCE_CEILING → 0.0"""
        lr = adaptive_learning_rate(DIVERGENCE_CEILING, base_lr=0.02)
        assert lr == 0.0

    def test_just_below_ceiling(self):
        """sync = 91.9 → 減速だが停止しない"""
        lr = adaptive_learning_rate(91.9, base_lr=0.02)
        assert lr > 0.0
