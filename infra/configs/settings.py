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

    # === JWT ===
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")  # 空=API Key認証にフォールバック
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

    # === CORS ===
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # カンマ区切り or *

    # === Logging ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "/var/log/cocoro/cocoro.log")  # 空=ファイル出力なし

    # === Scheduler ===
    CONSOLIDATION_INTERVAL_HOURS: int = int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "6"))

    # === Webhook ===
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")  # Discord/Slack webhook

    # === Email (Resend) ===
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@cocoro.ai")
    EMAIL_ENABLED: bool = os.getenv("RESEND_API_KEY", "") != ""  # キーが設定されているか

    # === Security ===
    IP_WHITELIST: str = os.getenv("IP_WHITELIST", "")  # カンマ区切り。空=全許可
    IP_BLACKLIST: str = os.getenv("IP_BLACKLIST", "")  # カンマ区切り。空=ブロックなし
    # 外部リクエスト允許ネットワーク (セキュリティミドルウェア用)
    ALLOWED_IPS: str = os.getenv("ALLOWED_IPS", "127.0.0.1,192.168.0.0/16,172.16.0.0/12,10.0.0.0/8")
    ENABLE_IP_FILTER: bool = os.getenv("ENABLE_IP_FILTER", "true").lower() in ("true", "1", "yes")
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() in ("true", "1", "yes")
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    LOGIN_MAX_FAILURES: int = int(os.getenv("LOGIN_MAX_FAILURES", "10"))
    LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300"))
    API_KEY_GRACE_HOURS: int = int(os.getenv("API_KEY_GRACE_HOURS", "24"))  # ローテーション後旧キー有効時間
    AUDIT_LOG_ENABLED: bool = os.getenv("AUDIT_LOG_ENABLED", "true").lower() in ("true", "1", "yes")

    # === SSL / HTTPS ===
    SSL_CERT_PATH: str = os.getenv("SSL_CERT_PATH", "")  # 空=Cloudflare Tunnel用の場合不要
    SSL_KEY_PATH: str = os.getenv("SSL_KEY_PATH", "")

    # === Cloudflare Tunnel ===
    TUNNEL_ENABLED: bool = os.getenv("TUNNEL_ENABLED", "false").lower() in ("true", "1", "yes")
    TUNNEL_URL: str = os.getenv("TUNNEL_URL", "https://console.cocoro-os.com")
    LOCAL_URL: str = os.getenv("LOCAL_URL", "http://192.168.50.92")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
