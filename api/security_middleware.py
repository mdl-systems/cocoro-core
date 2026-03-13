"""
cocoro-core — Security Middleware
レート制限・IPホワイトリスト・監査ログを提供するミドルウェア層。

slowapi (Starlette compatible) によるエンドポイント別レートリミット。
"""
import time
import ipaddress
import logging
import os
from typing import Optional

logger = logging.getLogger("cocoro.security")

# ──────────────────────────────────────────────
# IPホワイトリスト
# ──────────────────────────────────────────────

def _parse_allowed_networks(env_val: str) -> list:
    """ALLOWED_IPS環境変数 → ネットワークリストに変換"""
    networks = []
    for cidr in env_val.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning(f"Invalid CIDR in ALLOWED_IPS: {cidr}")
    return networks


_ALLOWED_ENV = os.getenv("ALLOWED_IPS", "127.0.0.1,192.168.0.0/16,172.16.0.0/12,10.0.0.0/8")
ALLOWED_NETWORKS: list = _parse_allowed_networks(_ALLOWED_ENV)


def is_ip_allowed(ip: str) -> bool:
    """IPアドレスがホワイトリスト内か確認"""
    if not ALLOWED_NETWORKS:
        return True  # 未設定時は全許可
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in ALLOWED_NETWORKS)
    except ValueError:
        return False


def get_client_ip(request) -> str:
    """リクエストからクライアントIPを取得 (プロキシヘッダ対応)"""
    # Cloudflare or nginx proxy headers
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.split(",")[0].strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ──────────────────────────────────────────────
# レート制限 (slowapi ラッパー)
# ──────────────────────────────────────────────

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import JSONResponse

    limiter = Limiter(key_func=get_remote_address)

    def get_ratelimit_handler():
        """RateLimitExceeded エラーハンドラを返す"""
        async def _handler(request: StarletteRequest, exc: RateLimitExceeded):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": str(exc.retry_after) if hasattr(exc, "retry_after") else "60",
                },
            )
        return _handler

    RATE_LIMITING_AVAILABLE = True
    logger.info("slowapi rate limiting enabled")

except ImportError:
    logger.warning("slowapi not installed — rate limiting disabled. Add slowapi>=0.1.9 to requirements.txt")
    RATE_LIMITING_AVAILABLE = False
    limiter = None

    class _NoopDecorator:
        def __call__(self, func):
            return func

    def get_ratelimit_handler():
        return None


# ──────────────────────────────────────────────
# 監査ログ
# ──────────────────────────────────────────────

class AuditLogger:
    """全APIコールの監査ログを記録"""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    def set_pool(self, pool):
        self.db_pool = pool

    def _mask_key(self, key: Optional[str]) -> str:
        if not key:
            return "none"
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]

    async def log(
        self,
        *,
        endpoint: str,
        method: str,
        ip: str,
        status_code: int,
        response_time_ms: float,
        api_key: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """監査ログをDBに記録 (失敗しても例外を投げない)"""
        entry = {
            "endpoint": endpoint,
            "method": method,
            "ip": ip,
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 2),
            "api_key_masked": self._mask_key(api_key),
            "user_agent": (user_agent or "")[:200],
            "error": error,
        }
        logger.debug(f"AUDIT {method} {endpoint} {status_code} {response_time_ms:.0f}ms from {ip}")

        if not self.db_pool:
            return
        try:
            await self.db_pool.execute(
                """
                INSERT INTO audit_log
                  (endpoint, method, client_ip, status_code, response_time_ms,
                   api_key_masked, user_agent, error_msg, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                entry["endpoint"],
                entry["method"],
                entry["ip"],
                entry["status_code"],
                entry["response_time_ms"],
                entry["api_key_masked"],
                entry["user_agent"],
                entry["error"],
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


# ──────────────────────────────────────────────
# Starlette ミドルウェア
# ──────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse as _JSONResponse


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    1. IPホワイトリストチェック
    2. 全リクエストの監査ログ記録
    """

    def __init__(self, app, audit_logger: AuditLogger, enable_ip_filter: bool = True):
        super().__init__(app)
        self.audit = audit_logger
        self.enable_ip_filter = enable_ip_filter
        # /public/* と /health は IP チェックをスキップ
        self.ip_skip_prefixes = ["/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        client_ip = get_client_ip(request)

        # ── IPホワイトリストチェック ──
        if self.enable_ip_filter:
            path = request.url.path
            skip = any(path.startswith(p) for p in self.ip_skip_prefixes)
            if not skip and not is_ip_allowed(client_ip):
                logger.warning(f"IP blocked: {client_ip} → {path}")
                await self.audit.log(
                    endpoint=path,
                    method=request.method,
                    ip=client_ip,
                    status_code=403,
                    response_time_ms=0,
                    error="ip_blocked",
                )
                return _JSONResponse(
                    status_code=403,
                    content={"error": "access_denied", "message": "Your IP is not allowed"},
                )

        # ── リクエスト処理 ──
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ── 監査ログ記録 ──
        api_key = request.headers.get("Authorization", "")
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        await self.audit.log(
            endpoint=request.url.path,
            method=request.method,
            ip=client_ip,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            api_key=api_key if api_key else None,
            user_agent=request.headers.get("User-Agent"),
        )
        return response


# グローバルシングルトン
audit_logger = AuditLogger()
