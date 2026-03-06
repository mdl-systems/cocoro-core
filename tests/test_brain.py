"""cocoro-core — Brain モジュールのテスト"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from brain.planner.planner import Planner
from brain.decision_engine.decision_graph import DecisionGraph
from brain.reasoning.reasoning_engine import ReasoningEngine
from brain.llm_runtime import LLMRuntime, LLMError


# === Planner ===
class TestPlanner:
    def setup_method(self):
        self.planner = Planner()

    def test_build_plan_prompt(self):
        prompt = self.planner.build_plan_prompt("API開発", "REST API設計")
        assert "API開発" in prompt
        assert "REST API設計" in prompt

    def test_parse_plan_valid(self):
        llm_output = '```json\n{"steps": [{"step": 1, "action": "設計"}], "recommended_agent": "dev", "total_minutes": 30}\n```'
        result = self.planner.parse_plan(llm_output)
        assert len(result["steps"]) == 1
        assert result["recommended_agent"] == "dev"
        assert result["total_minutes"] == 30

    def test_parse_plan_invalid(self):
        result = self.planner.parse_plan("これはJSONではありません")
        assert result["steps"] == []
        assert result["recommended_agent"] is None


# === DecisionGraph ===
class TestDecisionGraph:
    def setup_method(self):
        self.dg = DecisionGraph(MagicMock(), MagicMock())

    def test_build_classify_prompt(self):
        prompt = self.dg.build_classify_prompt("売上レポート作成して")
        assert "売上レポート作成して" in prompt

    def test_parse_classification_valid(self):
        output = '{"action": "delegate", "reason": "業務依頼", "category": "business", "agent": "sales", "priority": 7}'
        result = self.dg.parse_classification(output)
        assert result["action"] == "delegate"
        assert result["agent"] == "sales"
        assert result["priority"] == 7

    def test_parse_classification_invalid(self):
        result = self.dg.parse_classification("不正な出力")
        assert result["action"] == "chat"
        assert result["reason"] == "parse_failed"

    def test_parse_decision_valid(self):
        output = '{"decision": "承認する", "reasoning": "コスト対効果", "values_applied": ["efficiency"], "confidence": 0.85, "risk": "low"}'
        result = self.dg.parse_decision(output)
        assert result["decision"] == "承認する"
        assert result["confidence"] == 0.85

    def test_parse_decision_invalid(self):
        result = self.dg.parse_decision("解析できません")
        assert "decision" in result
        assert result["confidence"] == 0.5


# === ReasoningEngine ===
class TestReasoningEngine:
    def setup_method(self):
        self.engine = ReasoningEngine(MagicMock(), MagicMock())

    def test_parse_reasoning_valid(self):
        output = json.dumps({
            "analysis": "問題分析",
            "options": ["A", "B"],
            "evaluation": "Aが最適",
            "conclusion": "Aを選択",
            "confidence": 0.9,
            "reasoning_chain": ["ステップ1", "ステップ2"]
        })
        result = self.engine.parse_reasoning(output)
        assert result["conclusion"] == "Aを選択"
        assert result["confidence"] == 0.9
        assert len(result["reasoning_chain"]) == 2

    def test_parse_reasoning_invalid(self):
        result = self.engine.parse_reasoning("自由形式の回答です")
        assert result["confidence"] == 0.5
        assert "自由形式" in result["analysis"]


# === LLMRuntime ===
class TestLLMRuntime:
    def test_init_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            llm = LLMRuntime()
            assert llm.gemini_model == "gemini-2.5-flash-lite"

    def test_rate_limit_counter(self):
        llm = LLMRuntime()
        initial = llm._rpm_count
        llm._rate_limit()
        assert llm._rpm_count == initial + 1

    @pytest.mark.asyncio
    async def test_generate_retry_exhausted(self):
        llm = LLMRuntime()
        llm.provider = "gemini"
        with patch.object(llm, '_gemini', side_effect=Exception("API error")):
            with pytest.raises(LLMError, match="LLM生成に失敗"):
                await llm.generate("test", retries=0)
