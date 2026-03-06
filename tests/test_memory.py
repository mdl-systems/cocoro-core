"""cocoro-core — Memory Consolidation パーサーのテスト"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock
from memory.consolidation import MemoryConsolidation


class TestConsolidationParser:
    def setup_method(self):
        self.consolidation = MemoryConsolidation(MagicMock(), MagicMock(), MagicMock())

    def test_parse_valid(self):
        output = json.dumps({
            "learnings": [{"lesson": "テスト", "category": "technical", "importance": 8}],
            "value_adjustments": [{"value_name": "logic", "direction": "strengthen", "reason": "理由"}],
            "belief_updates": [{"statement": "テストは重要", "confidence": 0.8, "action": "add"}],
            "growth_summary": "技術的に成長"
        })
        result = self.consolidation._parse(output)
        assert len(result["learnings"]) == 1
        assert result["learnings"][0]["category"] == "technical"
        assert result["growth_summary"] == "技術的に成長"

    def test_parse_with_markdown(self):
        output = '結果:\n```json\n{"learnings": [], "value_adjustments": [], "belief_updates": [], "growth_summary": "なし"}\n```'
        result = self.consolidation._parse(output)
        assert result["growth_summary"] == "なし"

    def test_parse_invalid(self):
        result = self.consolidation._parse("パースできないテキスト")
        assert result["learnings"] == []
        assert result["growth_summary"] == ""

    def test_parse_empty_json(self):
        result = self.consolidation._parse("{}")
        assert result.get("learnings") is None or result.get("learnings") == []
