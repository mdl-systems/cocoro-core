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


# ===================== PersonalityVector 32次元 =====================

class TestPersonalityVector:
    def test_default_values(self):
        from personality.personality_vector import PersonalityVector, ALL_PARAMS
        vec = PersonalityVector()
        assert len(ALL_PARAMS) == 32
        for p in ALL_PARAMS:
            assert vec.get(p) == 0.5

    def test_set_and_get(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector()
        vec.set("logic", 0.8)
        assert vec.get("logic") == 0.8

    def test_clamp(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector()
        vec.set("logic", 1.5)
        assert vec.get("logic") == 1.0
        vec.set("logic", -0.3)
        assert vec.get("logic") == 0.0

    def test_adjust(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector()
        new_val = vec.adjust("logic", 0.2)
        assert abs(new_val - 0.7) < 0.001

    def test_distance(self):
        from personality.personality_vector import PersonalityVector
        vec_a = PersonalityVector()
        vec_b = PersonalityVector({"logic": 1.0, "empathy": 0.0})
        dist = vec_a.distance(vec_b)
        assert dist > 0

    def test_similarity(self):
        from personality.personality_vector import PersonalityVector
        vec_a = PersonalityVector()
        vec_b = PersonalityVector()
        assert vec_a.similarity(vec_b) == 1.0

    def test_to_categorized_dict(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector()
        cats = vec.to_categorized_dict()
        assert "thinking" in cats
        assert "emotion" in cats
        assert len(cats) == 8

    def test_dominant_traits(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector({"logic": 0.95, "empathy": 0.9})
        top = vec.dominant_traits(2)
        assert top[0][0] == "logic"
        assert top[0][1] == 0.95

    def test_category_averages(self):
        from personality.personality_vector import PersonalityVector
        vec = PersonalityVector()
        avgs = vec.category_averages()
        assert avgs["thinking"] == 0.5
        assert len(avgs) == 8

    def test_from_dict(self):
        from personality.personality_vector import PersonalityVector
        data = {"logic": 0.8, "empathy": 0.3}
        vec = PersonalityVector.from_dict(data)
        assert vec.get("logic") == 0.8
        assert vec.get("empathy") == 0.3
        assert vec.get("creativity") == 0.5


class TestZodiacTraits:
    def test_determine_zodiac(self):
        from personality.zodiac_traits import determine_zodiac
        assert determine_zodiac(7, 15) == "cancer"
        assert determine_zodiac(3, 25) == "aries"
        assert determine_zodiac(12, 25) == "capricorn"
        assert determine_zodiac(1, 15) == "capricorn"

    def test_get_zodiac_modifiers(self):
        from personality.zodiac_traits import get_zodiac_modifiers
        mods = get_zodiac_modifiers("cancer")
        assert "empathy" in mods
        assert mods["empathy"] > 0

    def test_get_zodiac_element(self):
        from personality.zodiac_traits import get_zodiac_element
        assert get_zodiac_element("aries") == "fire"
        assert get_zodiac_element("taurus") == "earth"
        assert get_zodiac_element("gemini") == "air"
        assert get_zodiac_element("cancer") == "water"


class TestAnimalPersonality:
    def test_list_animals(self):
        from personality.animal_personality import list_animals
        animals = list_animals()
        assert len(animals) == 12
        names = [a["id"] for a in animals]
        assert "lion" in names
        assert "wolf" in names

    def test_get_modifiers(self):
        from personality.animal_personality import get_animal_modifiers
        mods = get_animal_modifiers("lion")
        assert mods["leadership"] == 0.30
        assert mods["assertiveness"] == 0.20

    def test_get_archetype(self):
        from personality.animal_personality import get_animal_archetype
        arch = get_animal_archetype("wolf")
        assert arch["name"] == "オオカミ"
        assert "modifiers" in arch


class TestBloodTraits:
    def test_get_modifiers(self):
        from personality.blood_traits import get_blood_modifiers
        mods = get_blood_modifiers("A")
        assert "discipline" in mods
        assert mods["discipline"] > 0

    def test_validate(self):
        from personality.blood_traits import validate_blood_type
        assert validate_blood_type("A") is True
        assert validate_blood_type("AB") is True
        assert validate_blood_type("X") is False


class TestQuickQuestions:
    def test_get_questions(self):
        from personality.quick_questions import get_questions
        qs = get_questions()
        assert len(qs) == 8

    def test_get_limited(self):
        from personality.quick_questions import get_questions
        qs = get_questions(3)
        assert len(qs) == 3

    def test_apply_answers(self):
        from personality.quick_questions import apply_answers
        mods = apply_answers({"q1": 0, "q2": 1})
        assert "adventure" in mods or "cooperation" in mods
        assert len(mods) > 0


class TestPersonalityLearning:
    def test_learn_from_feedback(self):
        from personality.personality_vector import PersonalityVector
        from personality.personality_learning import PersonalityLearning
        vec = PersonalityVector()
        learner = PersonalityLearning()
        record = learner.learn_from_feedback(vec, "positive", {"creativity": 0.8})
        assert "creativity" in record["changes"]
        assert record["changes"]["creativity"]["new"] > 0.5

    def test_apply_decay(self):
        from personality.personality_vector import PersonalityVector
        from personality.personality_learning import PersonalityLearning
        vec = PersonalityVector({"logic": 0.9, "empathy": 0.1})
        learner = PersonalityLearning()
        result = learner.apply_decay(vec)
        # Should move toward center (0.5)
        assert vec.get("logic") < 0.9
        assert vec.get("empathy") > 0.1

    def test_get_stats(self):
        from personality.personality_learning import PersonalityLearning
        learner = PersonalityLearning()
        stats = learner.get_stats()
        assert stats["total_updates"] == 0
        assert stats["learning_rate"] == 0.02


class TestPersonalityProfile:
    def test_generate_seed(self):
        from datetime import date
        from personality.models.personality_profile import PersonalityProfile
        profile = PersonalityProfile(
            birthdate=date(1990, 7, 15),
            blood_type="A",
            animal_type="wolf",
        )
        result = profile.generate_seed()
        assert result["zodiac_sign"] == "cancer"
        assert result["animal_type"] == "wolf"
        assert result["blood_type"] == "A"
        assert "vector" in result

    def test_to_dict(self):
        from datetime import date
        from personality.models.personality_profile import PersonalityProfile
        profile = PersonalityProfile(
            birthdate=date(1990, 7, 15),
            blood_type="O",
            animal_type="lion",
        )
        profile.generate_seed()
        d = profile.to_dict()
        assert d["zodiac_sign"] == "cancer"
        assert d["blood_type"] == "O"
        assert "personality_vector" in d
        assert "dominant_traits" in d
        assert len(d["personality_vector"]) == 32

    def test_from_dict(self):
        from datetime import date
        from personality.models.personality_profile import PersonalityProfile
        data = {
            "birthdate": "1990-07-15",
            "blood_type": "B",
            "animal_type": "cat",
            "personality_vector": {"creativity": 0.8},
        }
        profile = PersonalityProfile.from_dict(data)
        assert profile.blood_type == "B"
        assert profile.vector.get("creativity") == 0.8


# ===================== Compatibility Engine =====================

class TestCompatibilityEngine:
    def test_check_identical(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.compatibility_engine import CompatibilityEngine
        vec_a = PersonalityVector()
        vec_b = PersonalityVector()
        engine = CompatibilityEngine()
        result = engine.check(vec_a, vec_b)
        assert result["compatibility_score"] > 0.5
        assert "level" in result
        assert "components" in result

    def test_check_different(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.compatibility_engine import CompatibilityEngine
        vec_a = PersonalityVector({"logic": 1.0, "empathy": 0.0, "speed": 1.0})
        vec_b = PersonalityVector({"logic": 0.0, "empathy": 1.0, "speed": 0.0})
        engine = CompatibilityEngine()
        result = engine.check(vec_a, vec_b)
        assert "compatibility_score" in result

    def test_level_determination(self):
        from compatibility.compatibility_engine import CompatibilityEngine
        engine = CompatibilityEngine()
        level = engine._determine_level(0.9)
        assert level["level_id"] == "ideal_partner"
        level = engine._determine_level(0.75)
        assert level["level_id"] == "strong_match"
        level = engine._determine_level(0.4)
        assert level["level_id"] == "challenging"

    def test_report(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.compatibility_engine import CompatibilityEngine
        vec_a = PersonalityVector()
        vec_b = PersonalityVector()
        engine = CompatibilityEngine()
        result = engine.check(vec_a, vec_b)
        report = engine.get_report(result)
        assert "summary" in report
        assert "score" in report
        assert "recommendation" in report

    def test_relationship_type(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.compatibility_engine import CompatibilityEngine
        vec_a = PersonalityVector()
        vec_b = PersonalityVector()
        engine = CompatibilityEngine()
        result = engine.check(vec_a, vec_b, "human-ai")
        assert result["relationship_type"] == "human-ai"


class TestSimilarityCalculator:
    def test_identical(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.similarity_calculator import calculate_similarity
        vec = PersonalityVector()
        result = calculate_similarity(vec, vec)
        assert result["similarity"] == 1.0

    def test_different(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.similarity_calculator import calculate_similarity
        vec_a = PersonalityVector({"logic": 1.0})
        vec_b = PersonalityVector({"logic": 0.0})
        result = calculate_similarity(vec_a, vec_b)
        assert result["similarity"] < 1.0


class TestValueAlignment:
    def test_aligned(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.value_alignment import calculate_value_alignment
        vec = PersonalityVector()
        result = calculate_value_alignment(vec, vec)
        assert result["value_alignment"] == 1.0
        assert result["fully_aligned"] is True

    def test_misaligned(self):
        from personality.personality_vector import PersonalityVector
        from compatibility.value_alignment import calculate_value_alignment
        vec_a = PersonalityVector({"ethics": 1.0, "fairness": 0.0})
        vec_b = PersonalityVector({"ethics": 0.0, "fairness": 1.0})
        result = calculate_value_alignment(vec_a, vec_b)
        assert result["value_alignment"] < 1.0
        assert len(result["conflict_areas"]) > 0
