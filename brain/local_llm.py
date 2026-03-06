"""cocoro-core — Local LLM Manager (C-4)
ローカルLLM (Ollama) の完全管理。
モデルの一覧/切り替え/ヘルスチェック/Function Callingエミュレーション。
"""
import logging
import json
import httpx

logger = logging.getLogger("cocoro.llm.local")


class LocalLLMManager:
    """ローカルLLM管理"""

    def __init__(self, base_url: str = "http://localhost:11434",
                 default_model: str = "gemma2:2b"):
        self.base_url = base_url
        self.current_model = default_model
        self._available_models: list[str] = []

    async def list_models(self) -> list[dict]:
        """利用可能なモデル一覧"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                self._available_models = [m["name"] for m in models]
                return [
                    {
                        "name": m["name"],
                        "size": m.get("size", 0),
                        "modified": m.get("modified_at", ""),
                        "current": m["name"] == self.current_model,
                    }
                    for m in models
                ]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def switch_model(self, model_name: str) -> dict:
        """使用モデルを切り替え"""
        models = await self.list_models()
        available = [m["name"] for m in models]
        if model_name not in available:
            return {
                "success": False,
                "error": f"Model '{model_name}' not found",
                "available": available,
            }
        old_model = self.current_model
        self.current_model = model_name
        logger.info(f"Model switched: {old_model} -> {model_name}")
        return {"success": True, "previous": old_model, "current": model_name}

    async def model_info(self, model_name: str = None) -> dict:
        """モデル詳細情報"""
        name = model_name or self.current_model
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": name},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "name": name,
                    "parameters": data.get("parameters", ""),
                    "template": data.get("template", ""),
                    "modelfile": data.get("modelfile", "")[:500],
                    "details": data.get("details", {}),
                }
        except Exception as e:
            return {"name": name, "error": str(e)}

    async def health_check(self) -> dict:
        """Ollama サーバーのヘルスチェック"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                healthy = resp.status_code == 200
                models = resp.json().get("models", []) if healthy else []
                return {
                    "healthy": healthy,
                    "url": self.base_url,
                    "current_model": self.current_model,
                    "model_count": len(models),
                    "models": [m["name"] for m in models],
                }
        except httpx.ConnectError:
            return {
                "healthy": False,
                "url": self.base_url,
                "error": "Connection refused — Ollama is not running",
            }
        except Exception as e:
            return {"healthy": False, "url": self.base_url, "error": str(e)}

    async def generate(self, prompt: str, system_prompt: str = "",
                       temperature: float = 0.7) -> str:
        """ローカルLLM生成"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                })
                resp.raise_for_status()
                return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Local LLM generate error: {e}")
            raise

    async def emulate_function_calling(self, prompt: str, tools: list[dict],
                                        system_prompt: str = "") -> dict:
        """Ollama用 Function Callingエミュレーション
        ツール定義をプロンプトに埋め込み、JSON応答を解析する。
        """
        tool_desc = "使用可能なツール:\n"
        for t in tools:
            params_str = ", ".join(
                f"{k}: {v}" for k, v in t.get("parameters", {}).items()
            )
            tool_desc += f"- {t['name']}: {t.get('description', '')} (引数: {params_str})\n"

        fc_prompt = f"""{system_prompt}

{tool_desc}

ユーザーの要求に対して、ツールの使用が必要な場合は以下のJSON形式で返してください:
{{"tool": "ツール名", "args": {{"引数名": "値"}}}}
ツールが不要な場合は通常のテキストで回答してください。

ユーザー: {prompt}"""

        response = await self.generate(fc_prompt, temperature=0.1)

        # JSON応答の解析を試行
        try:
            # JSONブロックの抽出
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif text.startswith("{"):
                pass  # そのまま

            data = json.loads(text)
            if "tool" in data and "args" in data:
                return {
                    "type": "function_call",
                    "name": data["tool"],
                    "args": data["args"],
                }
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

        # テキスト応答にフォールバック
        return {"type": "text", "content": response}

    async def get_stats(self) -> dict:
        """ローカルLLM統計"""
        health = await self.health_check()
        return {
            "provider": "ollama",
            "base_url": self.base_url,
            "current_model": self.current_model,
            "healthy": health.get("healthy", False),
            "model_count": health.get("model_count", 0),
            "available_models": health.get("models", []),
        }
