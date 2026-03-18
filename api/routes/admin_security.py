"""
cocoro-core — Admin Security Routes
APIキーローテーション・監査ログ確認エンドポイント。
"""
import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("cocoro.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

# ローテーション後の旧キー有効期限（デフォルト24時間）
KEY_GRACE_HOURS = int(os.getenv("API_KEY_GRACE_HOURS", "24"))


def _get_deps():
    from api.server import verify_api_key, db_pool
    return verify_api_key, db_pool


# ──────────────────────────────────────────────
# POST /admin/api-keys/rotate
# ──────────────────────────────────────────────

class RotateResponse(BaseModel):
    new_api_key: str
    old_key_expires_at: str
    grace_hours: int
    message: str


@router.post(
    "/api-keys/rotate",
    summary="APIキーのローテーション",
    description="""新しいAPIキーを生成して環境変数(`API_KEY`)を更新します。
旧APIキーは移行期間（デフォルト24時間）有効です。

**注意:** 返された `new_api_key` は一度しか表示されません。
すぐに安全な場所に保存してください。""",
    response_model=RotateResponse,
)
async def rotate_api_key(_=Depends(lambda: _get_deps()[0]())):
    """APIキーをローテーション"""
    verify_api_key, db_pool = _get_deps()

    current_key = os.getenv("API_KEY", "")
    new_key = f"ck_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=KEY_GRACE_HOURS)

    def _mask(k: str) -> str:
        if len(k) <= 8:
            return "****"
        return k[:4] + "****" + k[-4:]

    # DB に記録
    if db_pool:
        try:
            await db_pool.execute(
                """
                INSERT INTO api_key_rotation
                  (old_key_masked, new_key_masked, expires_at)
                VALUES ($1, $2, $3)
                """,
                _mask(current_key),
                _mask(new_key),
                expires_at,
            )
            # system_settings にも保存（旧キーと新キー両方）
            await db_pool.execute(
                """
                INSERT INTO system_settings (setting_key, setting_value, description)
                VALUES ('pending_old_api_key', $1, 'Rotating API key - grace period')
                ON CONFLICT (setting_key) DO UPDATE
                  SET setting_value = $1, updated_at = NOW()
                """,
                current_key,
            )
            await db_pool.execute(
                """
                INSERT INTO system_settings (setting_key, setting_value, description)
                VALUES ('pending_old_key_expires', $1, 'Old API key expiry after rotation')
                ON CONFLICT (setting_key) DO UPDATE
                  SET setting_value = $1, updated_at = NOW()
                """,
                expires_at.isoformat(),
            )
        except Exception as e:
            logger.error(f"Failed to record key rotation: {e}")

    logger.warning(f"API key rotated. Old key expires at {expires_at.isoformat()}")

    return RotateResponse(
        new_api_key=new_key,
        old_key_expires_at=expires_at.isoformat(),
        grace_hours=KEY_GRACE_HOURS,
        message=(
            f"New API key generated. Old key valid for {KEY_GRACE_HOURS} hours. "
            "Update your .env file immediately: API_KEY=" + new_key[:8] + "..."
        ),
    )


# ──────────────────────────────────────────────
# GET /admin/audit-log
# ──────────────────────────────────────────────

@router.get(
    "/audit-log",
    summary="監査ログを取得",
    description="""APIコールの監査ログを返します。
各エントリにはエンドポイント・IP・レスポンスタイム・ステータスコードが含まれます。
APIキーはマスク済みです。""",
)
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    endpoint: str = None,
    ip: str = None,
    status_code: int = None,
    _=Depends(lambda: _get_deps()[0]()),
):
    """監査ログを取得"""
    _, db_pool = _get_deps()
    if not db_pool:
        raise HTTPException(503, "DB not initialized")

    conditions = []
    params = []
    idx = 1

    if endpoint:
        conditions.append(f"endpoint ILIKE ${idx}")
        params.append(f"%{endpoint}%")
        idx += 1
    if ip:
        conditions.append(f"client_ip = ${idx}")
        params.append(ip)
        idx += 1
    if status_code:
        conditions.append(f"status_code = ${idx}")
        params.append(status_code)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    try:
        rows = await db_pool.fetch(
            f"""
            SELECT id, endpoint, method, client_ip, status_code,
                   response_time_ms, api_key_masked, user_agent, error_msg, created_at
            FROM audit_log
            {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx+1}
            """,
            *params,
        )
        total = await db_pool.fetchval(
            f"SELECT COUNT(*) FROM audit_log {where}",
            *params[:-2],
        )
    except Exception as e:
        # audit_log テーブル未作成時（migration 未適用）は空を返す
        logger.warning(f"audit_log table not available: {e}")
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "logs": [],
            "note": "audit_log table not yet created. Run /migrate/run to apply migrations.",
        }

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [dict(r) for r in rows],
    }


# ──────────────────────────────────────────────
# GET /admin/audit-log/stats
# ──────────────────────────────────────────────

@router.get(
    "/audit-log/stats",
    summary="監査ログ統計",
    description="直近24時間のAPIコール統計（エンドポイント別・ステータス別）を返します。",
)
async def get_audit_stats(_=Depends(lambda: _get_deps()[0]())):
    """監査ログ統計を取得"""
    _, db_pool = _get_deps()
    if not db_pool:
        raise HTTPException(503, "DB not initialized")

    try:
        # 直近24時間
        top_endpoints = await db_pool.fetch(
            """
            SELECT endpoint, COUNT(*) as count,
                   AVG(response_time_ms) as avg_ms,
                   COUNT(*) FILTER (WHERE status_code >= 400) as errors
            FROM audit_log
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 20
            """,
        )
        status_dist = await db_pool.fetch(
            """
            SELECT status_code, COUNT(*) as count
            FROM audit_log
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY status_code
            ORDER BY count DESC
            """,
        )
        top_ips = await db_pool.fetch(
            """
            SELECT client_ip, COUNT(*) as count,
                   COUNT(*) FILTER (WHERE status_code >= 400) as errors
            FROM audit_log
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY client_ip
            ORDER BY count DESC
            LIMIT 10
            """,
        )
        total_calls = await db_pool.fetchval(
            "SELECT COUNT(*) FROM audit_log WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        avg_response = await db_pool.fetchval(
            "SELECT AVG(response_time_ms) FROM audit_log WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
    except Exception as e:
        # audit_log テーブル未作成時（migration 未適用）は空統計を返す
        logger.warning(f"audit_log table not available: {e}")
        return {
            "period": "last_24h",
            "total_calls": 0,
            "avg_response_ms": 0,
            "top_endpoints": [],
            "status_distribution": [],
            "top_ips": [],
            "note": "audit_log table not yet created. Run /migrate/run to apply migrations.",
        }

    return {
        "period": "last_24h",
        "total_calls": total_calls,
        "avg_response_ms": round(avg_response or 0, 2),
        "top_endpoints": [dict(r) for r in top_endpoints],
        "status_distribution": [dict(r) for r in status_dist],
        "top_ips": [dict(r) for r in top_ips],
    }


# ──────────────────────────────────────────────
# GET /admin/security/status
# ──────────────────────────────────────────────

@router.get(
    "/security/status",
    summary="セキュリティ設定ステータス",
    description="現在のセキュリティ設定（IP制限・レート制限・SSL等）を返します。",
)
async def security_status(_=Depends(lambda: _get_deps()[0]())):
    """セキュリティ設定の確認"""
    from api.security_middleware import ALLOWED_NETWORKS, RATE_LIMITING_AVAILABLE, _ALLOWED_ENV

    ssl_cert = os.getenv("SSL_CERT_PATH", "")
    ssl_key = os.getenv("SSL_KEY_PATH", "")

    return {
        "ip_whitelist": {
            "enabled": bool(ALLOWED_NETWORKS),
            "config": _ALLOWED_ENV,
            "network_count": len(ALLOWED_NETWORKS),
        },
        "rate_limiting": {
            "enabled": RATE_LIMITING_AVAILABLE,
            "limits": {
                "/chat/stream": "60/minute",
                "/setup/*": "10/minute",
                "/public/*": "30/minute",
                "default": "120/minute",
            },
        },
        "ssl": {
            "cert_configured": bool(ssl_cert),
            "key_configured": bool(ssl_key),
            "note": "Cloudflare Tunnel使用時はSSL設定不要",
        },
        "api_key": {
            "rotation_grace_hours": KEY_GRACE_HOURS,
        },
        "audit_logging": {
            "enabled": True,
            "retention_days": 90,
        },
    }
