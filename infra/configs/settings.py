"""cocoro-core — Configuration"""
import os


class Settings:
    # === LLM ===
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma2:2b")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    # === Database ===
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "cocoro-postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cocoro")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "cocoro_secret")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cocoro_db")

    # === Redis ===
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://cocoro-redis:6379/0")

    # === API ===
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    COCORO_API_KEY: str = os.getenv("COCORO_API_KEY", "")

    # === Logging ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # === Scheduler ===
    CONSOLIDATION_INTERVAL_HOURS: int = int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "6"))

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
