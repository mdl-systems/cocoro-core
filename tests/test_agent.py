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
        assert len(agents) == 7
        types = [a["type"] for a in agents]
        assert "dev" in types
        assert "sales" in types
        assert "marketing" in types
        assert "researcher" in types
        assert "legal" in types
        assert "finance" in types
        assert "support" in types

    def test_route_researcher(self):
        result = self.router.route("競合他社のリサーチと分析")
        assert result == "researcher"

    def test_route_legal(self):
        result = self.router.route("利用規約の法律チェック")
        assert result == "legal"

    def test_route_finance(self):
        result = self.router.route("今月の経理と予算管理")
        assert result == "finance"

    def test_route_support(self):
        result = self.router.route("顧客の問い合わせ対応とFAQ作成")
        assert result == "support"

    def test_system_prompt_researcher(self):
        prompt = self.router.get_system_prompt("researcher")
        assert "Research" in prompt
