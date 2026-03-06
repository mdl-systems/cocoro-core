"""cocoro-core — LLM Runtime (Ollama / Gemini)"""
import os
import time
import logging
import httpx

logger = logging.getLogger("cocoro.llm")


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

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        if self.provider == "ollama":
            return await self._ollama(prompt, system_prompt)
        return await self._gemini(prompt, system_prompt)

    async def _ollama(self, prompt: str, system_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.ollama_url}/api/generate", json={
                "model": self.ollama_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
            })
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def _gemini(self, prompt: str, system_prompt: str) -> str:
        self._rate_limit()
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_key)
        model = genai.GenerativeModel(
            self.gemini_model,
            system_instruction=system_prompt if system_prompt else None,
        )
        response = model.generate_content(prompt)
        return response.text

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
