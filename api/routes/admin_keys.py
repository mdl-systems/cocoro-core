"""
Admin API Key Management Routes
  GET    /admin/api-keys          — 発行済みAPIキー一覧
  POST   /admin/api-keys          — 新規APIキー発行
  DELETE /admin/api-keys/{key_id} — APIキー無効化
"""

import uuid
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("cocoro.admin_keys")

router = APIRouter(prefix="/admin/api-keys", tags=["admin"])


# ──────────────────────────────────────────────
# 依存性
# ──────────────────────────────────────────────

def _get_db():
    import api.server as _srv
    if _srv.db_pool is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    return _srv.db_pool


def _verify_admin_key():
    """server.py の verify_api_key を再利用"""
    from api.server import verify_api_key
    return verify_api_key


# ──────────────────────────────────────────────
# リクエストモデル
# ──────────────────────────────────────────────

class ApiKeyCreateReq(BaseModel):
    label: str                          # 識別ラベル（例: "田中法律事務所"）
    registration_id: str | None = None  # agent_registrations.id (任意)
    expires_days: int | None = None     # 有効期限（日数）。None=無期限
    scopes: list[str] = ["chat"]        # 許可スコープ


# ──────────────────────────────────────────────
# GET /admin/api-keys
# ──────────────────────────────────────────────

@router.get(
    "",
    summary="発行済みAPIキー一覧",
    description="""発行済みの全APIキーを返します。

セキュリティのためキーの値（`key_value`）は先頭8文字のみ表示します。
""",
)
async def list_api_keys(
    _=Depends(_verify_admin_key),
    db=Depends(_get_db),
    include_revoked: bool = False,
):
    try:
        if include_revoked:
            rows = await db.fetch(
                """
                SELECT id, label, key_prefix, scopes, registration_id,
                       expires_at, is_active, created_at, last_used_at
                FROM api_keys
                ORDER BY created_at DESC
                LIMIT 200
                """
            )
        else:
            rows = await db.fetch(
                """
                SELECT id, label, key_prefix, scopes, registration_id,
                       expires_at, is_active, created_at, last_used_at
                FROM api_keys
                WHERE is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 200
                """
            )
    except Exception as e:
        logger.error(f"api-keys list error: {e}")
        raise HTTPException(status_code=500, detail="DB error")

    keys = [
        {
            "id": str(row["id"]),
            "label": row["label"],
            "key_prefix": row["key_prefix"],  # "ck_xxxx..." の頭8文字
            "scopes": row["scopes"] or [],
            "registration_id": str(row["registration_id"]) if row["registration_id"] else None,
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
        }
        for row in rows
    ]

    return {
        "api_keys": keys,
        "count": len(keys),
        "include_revoked": include_revoked,
    }


# ──────────────────────────────────────────────
# POST /admin/api-keys
# ──────────────────────────────────────────────

@router.post(
    "",
    status_code=201,
    summary="APIキー新規発行",
    description="""新しいAPIキーを発行します。

**⚠️ レスポンスに含まれる `api_key` は一度しか表示されません。**
必ず安全な場所に保存してください。

キーフォーマット: `ck_<random32chars>`
""",
)
async def create_api_key(
    req: ApiKeyCreateReq,
    _=Depends(_verify_admin_key),
    db=Depends(_get_db),
):
    key_value = f"ck_{secrets.token_urlsafe(32)}"
    key_prefix = key_value[:12]  # "ck_" + 9文字 = 12文字を保存
    key_id = str(uuid.uuid4())

    expires_at = None
    if req.expires_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_days)

    try:
        await db.execute(
            """
            INSERT INTO api_keys
              (id, label, key_value, key_prefix, scopes, registration_id,
               expires_at, is_active, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW())
            """,
            key_id,
            req.label[:200],
            key_value,   # ハッシュせずに保存（secretsトークンで十分）
            key_prefix,
            req.scopes,
            req.registration_id,
            expires_at,
        )
    except Exception as e:
        logger.error(f"api-key create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

    logger.info(f"New API key issued: {key_id} ({req.label})")
    return {
        "id": key_id,
        "api_key": key_value,   # ⚠️ 一度しか表示されない
        "key_prefix": key_prefix,
        "label": req.label,
        "scopes": req.scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "message": "⚠️ このキーは一度しか表示されません。必ず安全な場所に保存してください。",
    }


# ──────────────────────────────────────────────
# DELETE /admin/api-keys/{key_id}
# ──────────────────────────────────────────────

@router.delete(
    "/{key_id}",
    summary="APIキー無効化",
    description="""指定したIDのAPIキーを無効化（ソフトデリート）します。

無効化されたキーは `is_active=false` となり、認証に使用できなくなります。
物理削除は行いません。
""",
    responses={
        200: {"description": "無効化成功"},
        404: {"description": "キーが見つかりません"},
    },
)
async def revoke_api_key(
    key_id: str,
    _=Depends(_verify_admin_key),
    db=Depends(_get_db),
):
    try:
        row = await db.fetchrow(
            "SELECT id, label, is_active FROM api_keys WHERE id = $1",
            key_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail=f"API key '{key_id}' not found")

    if not row["is_active"]:
        return {
            "id": key_id,
            "label": row["label"],
            "status": "already_revoked",
            "message": "このキーは既に無効化されています",
        }

    try:
        await db.execute(
            "UPDATE api_keys SET is_active = FALSE WHERE id = $1",
            key_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revoke failed: {e}")

    logger.info(f"API key revoked: {key_id} ({row['label']})")
    return {
        "id": key_id,
        "label": row["label"],
        "status": "revoked",
        "message": "APIキーを無効化しました",
    }
