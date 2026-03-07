"""cocoro-core — D-2/3/4/6/7/8 Unit Tests
新規モジュールの単体テスト。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ===================== D-6: テンプレート =====================

class TestPersonalityTemplates:
    def test_list_templates(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.list_templates()
        assert len(result) >= 6
        names = [t["id"] for t in result]
        assert "default" in names
        assert "analytical" in names
        assert "creative" in names
        assert "empathetic" in names
        assert "leader" in names
        assert "researcher" in names

    def test_get_template(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.get_template("default")
        assert result["name"] == "バランス型"
        assert "values" in result
        assert "emotion_baseline" in result

    def test_get_template_not_found(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.get_template("nonexistent")
        assert "error" in result

    def test_apply_template(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.apply_template("analytical")
        assert result["applied"] is True
        assert result["template"]["values"]["analytical"] == 0.95

    def test_apply_template_with_overrides(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.apply_template("default", {"values": {"openness": 0.9}})
        assert result["applied"] is True
        assert result["template"]["values"]["openness"] == 0.9

    def test_apply_clamps_values(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.apply_template("default", {"values": {"openness": 1.5}})
        assert result["template"]["values"]["openness"] == 1.0

    def test_register_custom(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.register_custom("test1", {
            "name": "テスト", "description": "テスト用",
            "values": {"openness": 0.5},
        })
        assert result["registered"] is True
        # confirm listed
        templates = mgr.list_templates()
        ids = [t["id"] for t in templates]
        assert "test1" in ids

    def test_register_custom_missing_fields(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.register_custom("bad", {"name": "x"})
        assert "error" in result

    def test_delete_custom(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        mgr.register_custom("del1", {
            "name": "del", "description": "d", "values": {}})
        result = mgr.delete_custom("del1")
        assert result["deleted"] is True

    def test_delete_builtin_fails(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        result = mgr.delete_custom("default")
        assert "error" in result

    def test_list_categories(self):
        from personality.templates import PersonalityTemplateManager
        mgr = PersonalityTemplateManager()
        cats = mgr.list_categories()
        assert "basic" in cats
        assert "professional" in cats


# ===================== D-7: 監視 =====================

class TestMetricsCollector:
    def test_increment(self):
        from infra.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.inc("test.counter")
        assert mc.get_counter("test.counter") == 1
        mc.inc("test.counter", 5)
        assert mc.get_counter("test.counter") == 6

    def test_gauge(self):
        from infra.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.set_gauge("cpu", 45.2)
        assert mc.get_gauge("cpu") == 45.2

    def test_histogram(self):
        from infra.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.observe("latency", 0.1)
        mc.observe("latency", 0.2)
        mc.observe("latency", 0.3)
        stats = mc.get_histogram_stats("latency")
        assert stats["count"] == 3
        assert abs(stats["avg"] - 0.2) < 0.01

    def test_prometheus_format(self):
        from infra.monitoring import MetricsCollector
        mc = MetricsCollector()
        mc.inc("requests")
        mc.set_gauge("memory", 55.0)
        output = mc.to_prometheus()
        assert "cocoro_requests" in output
        assert "cocoro_memory" in output
        assert "cocoro_uptime_seconds" in output

    def test_empty_histogram(self):
        from infra.monitoring import MetricsCollector
        mc = MetricsCollector()
        stats = mc.get_histogram_stats("nonexistent")
        assert stats["count"] == 0


class TestAlertRule:
    def test_gt_alert(self):
        from infra.monitoring import AlertRule
        rule = AlertRule("high_errors", "errors", "gt", 10)
        assert rule.check(5) is False
        assert rule.check(11) is True

    def test_lt_alert(self):
        from infra.monitoring import AlertRule
        rule = AlertRule("low_memory", "mem", "lt", 20)
        assert rule.check(25) is False
        assert rule.check(15) is True

    def test_to_dict(self):
        from infra.monitoring import AlertRule
        rule = AlertRule("test", "metric", "gt", 5, "critical")
        d = rule.to_dict()
        assert d["name"] == "test"
        assert d["severity"] == "critical"


class TestMonitoringManager:
    def test_record_request(self):
        from infra.monitoring import MonitoringManager
        mgr = MonitoringManager()
        mgr.record_request("/health", 200, 0.05)
        assert mgr.metrics.get_counter("api.requests_total") == 1

    def test_record_error(self):
        from infra.monitoring import MonitoringManager
        mgr = MonitoringManager()
        mgr.record_request("/fail", 500, 0.1)
        assert mgr.metrics.get_counter("api.errors") == 1


# ===================== D-8: 多言語 =====================

class TestI18n:
    def test_get_message_ja(self):
        from infra.i18n import I18nManager
        mgr = I18nManager(default_lang="ja")
        msg = mgr.get_message("greeting")
        assert "こんにちは" in msg

    def test_get_message_en(self):
        from infra.i18n import I18nManager
        mgr = I18nManager(default_lang="en")
        msg = mgr.get_message("greeting")
        assert "Hello" in msg

    def test_get_message_with_params(self):
        from infra.i18n import I18nManager
        mgr = I18nManager(default_lang="ja")
        msg = mgr.get_message("memory.recalled", count=5)
        assert "5" in msg

    def test_get_message_fallback(self):
        from infra.i18n import I18nManager
        mgr = I18nManager(default_lang="ja")
        msg = mgr.get_message("greeting", lang="nonexistent")
        assert "こんにちは" in msg

    def test_set_user_language(self):
        from infra.i18n import I18nManager
        mgr = I18nManager()
        result = mgr.set_user_language("user1", "en")
        assert result["set"] is True
        assert mgr.get_user_language("user1") == "en"

    def test_set_invalid_language(self):
        from infra.i18n import I18nManager
        mgr = I18nManager()
        result = mgr.set_user_language("user1", "xx")
        assert "error" in result

    def test_supported_languages(self):
        from infra.i18n import I18nManager
        mgr = I18nManager()
        langs = mgr.supported_languages
        codes = [l["code"] for l in langs]
        assert "ja" in codes
        assert "en" in codes
        assert "zh" in codes
        assert "ko" in codes

    def test_translate_response(self):
        from infra.i18n import I18nManager
        mgr = I18nManager()
        mgr.set_user_language("alice", "en")
        msg = mgr.translate_response("greeting", user_id="alice")
        assert "Hello" in msg


# ===================== D-3: 連携 =====================

class TestDiscordBridge:
    def test_parse_ping(self):
        from agent.integrations import DiscordBridge
        bridge = DiscordBridge()
        result = bridge.parse_interaction({"type": 1})
        assert result["type"] == "ping"
        assert result["response"] == {"type": 1}

    def test_parse_command(self):
        from agent.integrations import DiscordBridge
        bridge = DiscordBridge()
        result = bridge.parse_interaction({
            "type": 2,
            "data": {"name": "chat", "options": [{"name": "msg", "value": "hi"}]},
            "member": {"user": {"id": "123"}},
            "channel_id": "ch-1",
        })
        assert result["type"] == "command"
        assert result["name"] == "chat"
        assert result["options"]["msg"] == "hi"

    def test_status_unconfigured(self):
        from agent.integrations import DiscordBridge
        bridge = DiscordBridge()
        status = bridge.get_status()
        assert status["platform"] == "discord"
        assert status["configured"] is False


class TestLINEBridge:
    def test_parse_webhook_empty(self):
        from agent.integrations import LINEBridge
        bridge = LINEBridge()
        events = bridge.parse_webhook({"events": []})
        assert events == []

    def test_parse_webhook_message(self):
        from agent.integrations import LINEBridge
        bridge = LINEBridge()
        events = bridge.parse_webhook({
            "events": [{
                "type": "message",
                "replyToken": "rt1",
                "source": {"userId": "u1"},
                "timestamp": 1234567890,
                "message": {"type": "text", "text": "hello"},
            }]
        })
        assert len(events) == 1
        assert events[0]["type"] == "message"
        assert events[0]["text"] == "hello"

    def test_status_unconfigured(self):
        from agent.integrations import LINEBridge
        bridge = LINEBridge()
        status = bridge.get_status()
        assert status["platform"] == "line"
        assert status["configured"] is False
