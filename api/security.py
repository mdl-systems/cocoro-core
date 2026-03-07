"""
cocoro-core — Security Middleware
D-10: Rate Limiting, IP Whitelist, Security Headers, Login Throttle
"""
import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("cocoro.security")


# ============================================================
# Rate Limiter (インメモリ — 単一プロセス向け)
# ============================================================
class RateLimiter:
    """
    トークンバケット方式のレートリミッター。
    キーごとに rps (requests per second) で制限。
    """

    def __init__(self):
        self._buckets: dict[str, dict] = {}

    def _get_bucket(self, key: str, max_tokens: int, refill_rate: float) -> dict:
        now = time.monotonic()
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": max_tokens,
                "last_refill": now,
                "max_tokens": max_tokens,
                "refill_rate": refill_rate,
            }
        bucket = self._buckets[key]
        # トークン補充
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + elapsed * bucket["refill_rate"],
        )
        bucket["last_refill"] = now
        return bucket

    def allow(self, key: str, max_tokens: int = 60, refill_rate: float = 1.0) -> bool:
        """リクエストを許可するか判定。許可した場合トークンを1消費。"""
        bucket = self._get_bucket(key, max_tokens, refill_rate)
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    def remaining(self, key: str) -> int:
        if key in self._buckets:
            return max(0, int(self._buckets[key]["tokens"]))
        return 0

    def cleanup(self, max_age_seconds: int = 3600):
        """古いバケットを削除してメモリリークを防止"""
        now = time.monotonic()
        expired = [
            k for k, v in self._buckets.items()
            if now - v["last_refill"] > max_age_seconds
        ]
        for k in expired:
            del self._buckets[k]


# グローバルインスタンス
rate_limiter = RateLimiter()


# ============================================================
# Login Throttle (認証失敗のブルートフォース対策)
# ============================================================
class LoginThrottle:
    """
    認証失敗をIPごとにカウント。
    閾値を超えたらロックアウト（一定時間リクエスト拒否）。
    """

    def __init__(self, max_failures: int = 10, lockout_seconds: int = 300):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._locked: dict[str, float] = {}

    def record_failure(self, ip: str):
        """認証失敗を記録"""
        now = time.time()
        self._failures[ip].append(now)
        # 古い記録を削除(lockout_seconds以内のみ保持)
        cutoff = now - self.lockout_seconds
        self._failures[ip] = [t for t in self._failures[ip] if t > cutoff]
        # 閾値超えでロックアウト
        if len(self._failures[ip]) >= self.max_failures:
            self._locked[ip] = now + self.lockout_seconds
            logger.warning(f"IP {ip} locked out for {self.lockout_seconds}s ({len(self._failures[ip])} failures)")

    def record_success(self, ip: str):
        """認証成功で失敗カウントをリセット"""
        self._failures.pop(ip, None)
        self._locked.pop(ip, None)

    def is_locked(self, ip: str) -> bool:
        """ロックアウト中かチェック"""
        if ip in self._locked:
            if time.time() < self._locked[ip]:
                return True
            # ロックアウト期限切れ
            del self._locked[ip]
            self._failures.pop(ip, None)
        return False

    def get_stats(self) -> dict:
        return {
            "tracked_ips": len(self._failures),
            "locked_ips": len([ip for ip, t in self._locked.items() if time.time() < t]),
        }


# グローバルインスタンス
login_throttle = LoginThrottle()


# ============================================================
# IP Whitelist / Blacklist
# ============================================================
class IPFilter:
    """
    IPベースのアクセス制御。
    - whitelist が空 → 全IPを許可 (デフォルト)
    - whitelist が設定 → リスト内のIPのみ許可
    - blacklist → 常にブロック
    """

    def __init__(self):
        self.whitelist: set[str] = set()
        self.blacklist: set[str] = set()

    def configure(self, whitelist_csv: str = "", blacklist_csv: str = ""):
        """カンマ区切りのIP文字列から設定"""
        if whitelist_csv:
            self.whitelist = {ip.strip() for ip in whitelist_csv.split(",") if ip.strip()}
        if blacklist_csv:
            self.blacklist = {ip.strip() for ip in blacklist_csv.split(",") if ip.strip()}

    def is_allowed(self, ip: str) -> bool:
        # ブラックリストチェック
        if ip in self.blacklist:
            return False
        # ホワイトリストが空 → 全許可
        if not self.whitelist:
            return True
        # ホワイトリストチェック
        return ip in self.whitelist

    def get_config(self) -> dict:
        return {
            "whitelist": list(self.whitelist),
            "blacklist": list(self.blacklist),
            "mode": "whitelist" if self.whitelist else "open",
        }


# グローバルインスタンス
ip_filter = IPFilter()


# ============================================================
# Security Middleware (統合)
# ============================================================

# Rate limit設定 (パスパターンごと)
RATE_LIMIT_CONFIG = {
    "/auth/": {"max_tokens": 10, "refill_rate": 0.1},   # 認証: 10回/100秒
    "/chat": {"max_tokens": 30, "refill_rate": 0.5},     # チャット: 30回/60秒
    "/setup/": {"max_tokens": 20, "refill_rate": 0.3},   # セットアップ: 20回/66秒
    "default": {"max_tokens": 120, "refill_rate": 2.0},  # その他: 120回/60秒
}

# 認証不要パス
PUBLIC_PATHS = {"/health", "/dashboard", "/docs", "/openapi.json", "/redoc"}


def _get_client_ip(request: Request) -> str:
    """クライアントIPを取得 (X-Forwarded-For対応)"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_rate_limit_config(path: str) -> dict:
    """パスに応じたRate Limit設定を返す"""
    for prefix, config in RATE_LIMIT_CONFIG.items():
        if prefix != "default" and path.startswith(prefix):
            return config
    return RATE_LIMIT_CONFIG["default"]


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    統合セキュリティミドルウェア:
    1. IP Filter (Whitelist/Blacklist)
    2. Login Throttle (ブルートフォース防止)
    3. Rate Limiting (トークンバケット)
    4. Security Headers (XSS/Clickjacking/MIME sniffing 防止)
    5. HTTPS 強制 (本番環境)
    """

    def __init__(self, app, force_https: bool = False):
        super().__init__(app)
        self.force_https = force_https

    async def dispatch(self, request: Request, call_next):
        client_ip = _get_client_ip(request)
        path = request.url.path

        # 1. HTTPS強制 (本番環境)
        if self.force_https:
            proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
            if proto == "http" and path not in PUBLIC_PATHS:
                https_url = str(request.url).replace("http://", "https://", 1)
                return JSONResponse(
                    status_code=301,
                    content={"redirect": https_url},
                    headers={"Location": https_url},
                )

        # 2. IP Filter
        if not ip_filter.is_allowed(client_ip):
            logger.warning(f"IP blocked: {client_ip} on {path}")
            return JSONResponse(
                status_code=403,
                content={"error": "アクセスが拒否されました", "type": "ip_blocked"},
            )

        # 3. Login Throttle (認証エンドポイントのみ)
        if path.startswith("/auth/") and login_throttle.is_locked(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "認証試行回数超過。しばらくお待ちください",
                    "type": "login_locked",
                    "retry_after": login_throttle.lockout_seconds,
                },
                headers={"Retry-After": str(login_throttle.lockout_seconds)},
            )

        # 4. Rate Limiting
        config = _get_rate_limit_config(path)
        rate_key = f"{client_ip}:{path.split('/')[1] if '/' in path[1:] else path}"
        if not rate_limiter.allow(rate_key, config["max_tokens"], config["refill_rate"]):
            logger.warning(f"Rate limit exceeded: {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={"error": "リクエスト数が上限を超えました", "type": "rate_limited"},
                headers={"Retry-After": "60"},
            )

        # リクエスト実行
        response = await call_next(request)

        # 5. Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS (HTTPS環境のみ)
        if self.force_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Rate Limit情報をヘッダーに追加
        remaining = rate_limiter.remaining(rate_key)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
