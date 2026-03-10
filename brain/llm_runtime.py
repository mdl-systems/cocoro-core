"""cocoro-core — LLM Runtime (Ollama / Gemini)"""
import os
import time
import asyncio
import logging
import httpx

logger = logging.getLogger("cocoro.llm")


class LLMError(Exception):
    """LLM呼び出し失敗"""
    pass


class LLMRuntime:
    """LLM統合クライアント — Ollama優先、Geminiフォールバック"""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma2:2b")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self._rpm_count = 0
        self._rpm_start = time.time()

    async def generate(self, prompt: str, system_prompt: str = "", retries: int = 2) -> str:
        """LLM生成（リトライ付き）"""
        last_error = None
        for attempt in range(retries + 1):
            try:
                if self.provider == "ollama":
                    return await self._ollama(prompt, system_prompt)
                return await self._gemini(prompt, system_prompt)
            except Exception as e:
                last_error = e
                if attempt < retries:
                    wait = 2 ** attempt
                    logger.warning(f"LLM retry {attempt+1}/{retries} after {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"LLM failed after {retries+1} attempts: {e}")
        raise LLMError(f"LLM生成に失敗しました: {last_error}")

    async def _ollama(self, prompt: str, system_prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.ollama_url}/api/generate", json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                })
                resp.raise_for_status()
                return resp.json().get("response", "")
        except httpx.TimeoutException:
            raise LLMError(f"Ollama タイムアウト ({self.ollama_model})")
        except httpx.ConnectError:
            raise LLMError(f"Ollama 接続失敗 ({self.ollama_url})")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}")

    async def _gemini(self, prompt: str, system_prompt: str) -> str:
        self._rate_limit()
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(
                self.gemini_model,
                system_instruction=system_prompt if system_prompt else None,
            )
            response = model.generate_content(prompt)
            if not response.text:
                raise LLMError("Gemini: 空の応答（安全フィルタの可能性）")
            return response.text
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Gemini API エラー: {type(e).__name__}: {e}")

    def _rate_limit(self):
        now = time.time()
        if now - self._rpm_start > 60:
            self._rpm_count = 0
            self._rpm_start = now
        self._rpm_count += 1
        if self._rpm_count > 15:
            wait = 60 - (now - self._rpm_start)
            time.sleep(max(wait, 1))
            self._rpm_count = 1
            self._rpm_start = time.time()

    async def health(self) -> dict:
        try:
            if self.provider == "ollama":
                async with httpx.AsyncClient(timeout=5) as c:
                    r = await c.get(f"{self.ollama_url}/api/tags")
                    return {"provider": "ollama", "healthy": r.status_code == 200}
            return {"provider": "gemini", "healthy": bool(self.gemini_key)}
        except Exception:
            return {"provider": self.provider, "healthy": False}

    async def generate_stream(self, prompt: str, system_prompt: str = ""):
        """LLMストリーミング生成（AsyncGenerator）

        Gemini / Ollama の同期ストリーミングをスレッドエグゼキュータで実行し、
        非同期ジェネレーターとして chunk を yield する。
        """
        import queue as _queue
        import threading

        chunk_queue: "_queue.Queue[str | None | Exception]" = _queue.Queue()

        def _sync_stream():
            try:
                if self.provider == "ollama":
                    import httpx
                    with httpx.Client(timeout=120) as client:
                        with client.stream("POST", f"{self.ollama_url}/api/generate", json={
                            "model": self.ollama_model,
                            "prompt": prompt,
                            "system": system_prompt,
                            "stream": True,
                        }) as resp:
                            import json as _json
                            for line in resp.iter_lines():
                                if line:
                                    try:
                                        data = _json.loads(line)
                                        text = data.get("response", "")
                                        if text:
                                            chunk_queue.put(text)
                                        if data.get("done"):
                                            break
                                    except Exception:
                                        pass
                else:
                    # Gemini streaming
                    self._rate_limit()
                    import google.generativeai as genai
                    genai.configure(api_key=self.gemini_key)
                    model = genai.GenerativeModel(
                        self.gemini_model,
                        system_instruction=system_prompt if system_prompt else None,
                    )
                    response = model.generate_content(prompt, stream=True)
                    for chunk in response:
                        text = getattr(chunk, "text", "") or ""
                        if text:
                            chunk_queue.put(text)
            except Exception as e:
                chunk_queue.put(e)
            finally:
                chunk_queue.put(None)  # sentinel

        thread = threading.Thread(target=_sync_stream, daemon=True)
        thread.start()

        while True:
            # ノンブロッキングでキューをポーリング
            try:
                import queue as _q
                item = chunk_queue.get_nowait()
            except _q.Empty:
                await asyncio.sleep(0.01)
                continue

            if item is None:
                break
            if isinstance(item, Exception):
                logger.error(f"[generate_stream] error: {item}")
                break
            yield item

        thread.join(timeout=5)


    async def generate_with_tools(self, prompt: str, tools: list[dict],
                                   system_prompt: str = "") -> dict:
        """Gemini Function Calling — ツール定義を渡してLLMに呼び出しを判断させる

        Returns:
            {"type": "text", "content": "..."} or
            {"type": "function_call", "name": "...", "args": {...}}
        """
        if self.provider != "gemini":
            # Ollama非対応: テキスト生成にフォールバック
            text = await self.generate(prompt, system_prompt)
            return {"type": "text", "content": text}

        self._rate_limit()
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)

            # ツール定義をGemini形式に変換
            gemini_tools = []
            for t in tools:
                func_decl = genai.protos.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            k: genai.protos.Schema(type=genai.protos.Type.STRING, description=v)
                            for k, v in t.get("parameters", {}).items()
                        },
                    ),
                )
                gemini_tools.append(func_decl)

            tool_config = genai.protos.Tool(function_declarations=gemini_tools)
            model = genai.GenerativeModel(
                self.gemini_model,
                system_instruction=system_prompt if system_prompt else None,
                tools=[tool_config],
            )
            response = model.generate_content(prompt)

            # Function Callの確認
            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    logger.info(f"Function call: {fc.name}({args})")
                    return {"type": "function_call", "name": fc.name, "args": args}

            # テキスト応答にフォールバック
            return {"type": "text", "content": response.text or ""}
        except Exception as e:
            logger.error(f"Function Calling error: {type(e).__name__}: {e}")
            # テキスト生成にフォールバック
            text = await self.generate(prompt, system_prompt)
            return {"type": "text", "content": text}
