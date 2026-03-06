"""cocoro-core — Plugin System (C-5)
カスタムツールの動的登録・管理システム。
外部プラグインやユーザー定義ツールを実行時に追加可能。
"""
import logging
import importlib
from typing import Any, Callable, Awaitable

logger = logging.getLogger("cocoro.plugins")


class PluginRegistry:
    """プラグイン管理レジストリ"""

    def __init__(self):
        self._plugins: dict[str, dict] = {}
        self._handlers: dict[str, Callable[..., Awaitable[dict]]] = {}

    def register(self, name: str, description: str,
                 parameters: dict, handler: Callable[..., Awaitable[dict]],
                 category: str = "custom", version: str = "1.0") -> bool:
        """プラグインを登録"""
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' already registered, overwriting")

        self._plugins[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "category": category,
            "version": version,
            "enabled": True,
        }
        self._handlers[name] = handler
        logger.info(f"Plugin registered: {name} (v{version})")
        return True

    def unregister(self, name: str) -> bool:
        """プラグインを解除"""
        if name not in self._plugins:
            return False
        del self._plugins[name]
        del self._handlers[name]
        logger.info(f"Plugin unregistered: {name}")
        return True

    def enable(self, name: str) -> bool:
        """プラグインを有効化"""
        if name not in self._plugins:
            return False
        self._plugins[name]["enabled"] = True
        return True

    def disable(self, name: str) -> bool:
        """プラグインを無効化"""
        if name not in self._plugins:
            return False
        self._plugins[name]["enabled"] = False
        return True

    async def execute(self, name: str, args: dict) -> dict:
        """プラグインを実行"""
        if name not in self._plugins:
            return {"error": f"Plugin not found: {name}"}
        if not self._plugins[name]["enabled"]:
            return {"error": f"Plugin disabled: {name}"}

        handler = self._handlers[name]
        try:
            result = await handler(args)
            logger.info(f"Plugin executed: {name}")
            return result
        except Exception as e:
            logger.error(f"Plugin error ({name}): {e}")
            return {"error": str(e)}

    def get_tool_definitions(self) -> list[dict]:
        """有効なプラグインのツール定義を返す"""
        return [
            {
                "name": info["name"],
                "description": info["description"],
                "parameters": info["parameters"],
            }
            for info in self._plugins.values()
            if info["enabled"]
        ]

    def list_plugins(self) -> list[dict]:
        """全プラグイン一覧"""
        return list(self._plugins.values())

    def get_stats(self) -> dict:
        """プラグイン統計"""
        total = len(self._plugins)
        enabled = sum(1 for p in self._plugins.values() if p["enabled"])
        categories = {}
        for p in self._plugins.values():
            cat = p["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "categories": categories,
        }


# === 組み込みプラグイン ===

async def _echo_plugin(args: dict) -> dict:
    """テスト用エコープラグイン"""
    return {"echo": args.get("message", ""), "status": "ok"}


async def _math_plugin(args: dict) -> dict:
    """数値計算プラグイン"""
    expr = args.get("expression", "")
    try:
        # 安全な数式のみ許可
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expr):
            return {"error": "Invalid characters in expression"}
        result = eval(expr)  # noqa: S307
        return {"expression": expr, "result": result}
    except Exception as e:
        return {"error": f"Math error: {e}"}


async def _text_stats_plugin(args: dict) -> dict:
    """テキスト統計プラグイン"""
    text = args.get("text", "")
    return {
        "characters": len(text),
        "words": len(text.split()) if text else 0,
        "lines": text.count("\n") + 1 if text else 0,
        "sentences": text.count("。") + text.count(".") + 1 if text else 0,
    }


def register_builtin_plugins(registry: PluginRegistry):
    """組み込みプラグインを登録"""
    registry.register(
        name="echo",
        description="テスト用エコー。入力をそのまま返す。",
        parameters={"message": "エコーするメッセージ"},
        handler=_echo_plugin,
        category="system",
        version="1.0",
    )
    registry.register(
        name="math",
        description="数式を計算する。四則演算に対応。",
        parameters={"expression": "計算式（例: 2+3*4）"},
        handler=_math_plugin,
        category="utility",
        version="1.0",
    )
    registry.register(
        name="text_stats",
        description="テキストの文字数・単語数・行数を分析する。",
        parameters={"text": "分析するテキスト"},
        handler=_text_stats_plugin,
        category="utility",
        version="1.0",
    )
    logger.info(f"Builtin plugins registered: {len(registry.list_plugins())}")
