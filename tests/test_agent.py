"""cocoro-core — Agent モジュールのテスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.task_router.router import TaskRouter


class TestTaskRouter:
    def setup_method(self):
        self.router = TaskRouter()

    def test_route_dev(self):
        result = self.router.route("API開発をお願い")
        assert result == "dev"

    def test_route_sales(self):
        result = self.router.route("顧客への提案書作成")
        assert result == "sales"

    def test_route_marketing(self):
        result = self.router.route("SNS広告の企画")
        assert result == "marketing"

    def test_route_none(self):
        result = self.router.route("今日の天気は？")
        assert result is None

    def test_route_multiple_keywords(self):
        result = self.router.route("技術的なAPI設計とコード実装")
        assert result == "dev"

    def test_get_system_prompt_known(self):
        prompt = self.router.get_system_prompt("dev")
        assert "Dev Agent" in prompt

    def test_get_system_prompt_unknown(self):
        prompt = self.router.get_system_prompt("unknown")
        assert "汎用AI" in prompt

    def test_list_agents(self):
        agents = self.router.list_agents()
        assert len(agents) == 3
        types = [a["type"] for a in agents]
        assert "dev" in types
        assert "sales" in types
        assert "marketing" in types
