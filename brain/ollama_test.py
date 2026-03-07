"""cocoro-core — Ollama Integration Test Suite (D-2)
Ollama サーバーとの実機接続テスト。
接続・モデル一覧・推論・パフォーマンス・Function Calling テスト。
"""
import time
import logging
import httpx

logger = logging.getLogger("cocoro.ollama_test")


class OllamaTestRunner:
    """Ollama 実機テストランナー"""

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "gemma2:2b"):
        self.base_url = base_url
        self.model = model

    async def run_all(self) -> dict:
        """全テストを実行して結果を返す"""
        results = {}
        results["connection"] = await self.test_connection()
        results["models"] = await self.test_list_models()
        results["generate"] = await self.test_generate()
        results["performance"] = await self.test_performance()
        results["function_calling"] = await self.test_function_calling()

        passed = sum(1 for r in results.values() if r.get("passed"))
        total = len(results)
        return {
            "passed": passed,
            "total": total,
            "all_passed": passed == total,
            "model": self.model,
            "base_url": self.base_url,
            "results": results,
        }

    async def test_connection(self) -> dict:
        """接続テスト"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return {
                    "passed": resp.status_code == 200,
                    "status_code": resp.status_code,
                    "test": "connection",
                }
        except Exception as e:
            return {"passed": False, "error": str(e), "test": "connection"}

    async def test_list_models(self) -> dict:
        """モデル一覧テスト"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                models = resp.json().get("models", [])
                names = [m["name"] for m in models]
                return {
                    "passed": len(models) > 0,
                    "model_count": len(models),
                    "models": names,
                    "target_available": self.model in names,
                    "test": "models",
                }
        except Exception as e:
            return {"passed": False, "error": str(e), "test": "models"}

    async def test_generate(self) -> dict:
        """推論テスト"""
        prompt = "Say 'hello' in one word."
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                })
                elapsed = time.time() - start
                data = resp.json()
                response_text = data.get("response", "")
                return {
                    "passed": resp.status_code == 200 and len(response_text) > 0,
                    "response_preview": response_text[:100],
                    "elapsed_seconds": round(elapsed, 2),
                    "eval_count": data.get("eval_count", 0),
                    "test": "generate",
                }
        except Exception as e:
            return {"passed": False, "error": str(e), "test": "generate"}

    async def test_performance(self) -> dict:
        """パフォーマンステスト (3回生成の平均)"""
        times = []
        for _ in range(3):
            try:
                start = time.time()
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(f"{self.base_url}/api/generate", json={
                        "model": self.model,
                        "prompt": "Count to 3.",
                        "stream": False,
                        "options": {"temperature": 0.1},
                    })
                    if resp.status_code == 200:
                        times.append(time.time() - start)
            except Exception:
                pass
        if not times:
            return {"passed": False, "error": "All attempts failed", "test": "performance"}
        avg = sum(times) / len(times)
        return {
            "passed": avg < 30,  # 30秒以内
            "avg_seconds": round(avg, 2),
            "min_seconds": round(min(times), 2),
            "max_seconds": round(max(times), 2),
            "samples": len(times),
            "test": "performance",
        }

    async def test_function_calling(self) -> dict:
        """Function Callingエミュレーションテスト"""
        prompt = """You are a JSON assistant. Given the user request, pick the right tool.
Tools: {"name": "get_weather", "args": {"city": "string"}}
User: What is the weather in Tokyo?
Respond ONLY with JSON: {"tool": "...", "args": {...}}"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0},
                })
                text = resp.json().get("response", "")
                import json
                # Try to parse JSON from response
                cleaned = text.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                parsed = json.loads(cleaned)
                has_tool = "tool" in parsed
                return {
                    "passed": has_tool,
                    "parsed": parsed,
                    "raw_preview": text[:200],
                    "test": "function_calling",
                }
        except Exception as e:
            return {"passed": False, "error": str(e), "test": "function_calling"}
