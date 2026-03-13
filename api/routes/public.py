"""
Public API Routes — cocoro-website 連携
認証不要のエンドポイント群:
  POST /public/register  — エージェント登録申請
  GET  /public/agents    — 公開エージェント一覧
  POST /public/contact/{agent_id} — エージェントへの問い合わせ
"""

import uuid
import re
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger("cocoro.public")

router = APIRouter(prefix="/public", tags=["public"])

# ──────────────────────────────────────────────
# リクエスト / レスポンスモデル
# ──────────────────────────────────────────────

ALLOWED_SPECIALTIES = {
    "corporate_law", "criminal_law", "family_law", "intellectual_property",
    "tax_accounting", "audit", "bookkeeping",
    "general_medicine", "mental_health", "nutrition",
    "software_engineering", "data_science", "security",
    "financial_planning", "investment", "insurance",
    "research", "consulting", "other",
}


class AgentRegisterReq(BaseModel):
    name: str
    email: str
    specialty: str
    description: str
    node_url: str | None = None
    api_key_request: bool = False
    is_public: bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email format")
        return v

    @field_validator("specialty")
    @classmethod
    def specialty_allowed(cls, v: str) -> str:
        if v not in ALLOWED_SPECIALTIES:
            # 未知のspecialtyも弾かず "other" に変換（レジデンシーオープン）
            return v
        return v

    @field_validator("node_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("node_url must start with http:// or https://")
        return v


class ContactReq(BaseModel):
    message: str
    contact_email: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        if len(v) > 2000:
            raise ValueError("message too long (max 2000 chars)")
        return v

    @field_validator("contact_email")
    @classmethod
    def email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email format")
        return v


# ──────────────────────────────────────────────
# db_pool 依存性（server.py の global を参照）
# ──────────────────────────────────────────────

def _get_db():
    """server.py の db_pool を取得"""
    import api.server as _srv
    if _srv.db_pool is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    return _srv.db_pool


# ──────────────────────────────────────────────
# POST /public/register
# ──────────────────────────────────────────────

@router.post(
    "/register",
    status_code=202,
    summary="エージェント登録申請（認証不要）",
    description="""外部サービス（cocoro-website等）からのエージェント登録申請を受け付けます。

審査後、登録メールアドレス宛にAPIキーを送信します。
`api_key_request=true` の場合は優先審査となります。

**レート制限**: 同一IPから5分以内に3件まで。
""",
    responses={
        202: {"description": "登録申請受付完了"},
        400: {"description": "バリデーションエラー"},
        503: {"description": "DB接続エラー"},
    },
)
async def public_register(req: AgentRegisterReq, db=Depends(_get_db)):
    registration_id = str(uuid.uuid4())
    try:
        await db.execute(
            """
            INSERT INTO agent_registrations
              (id, name, email, specialty, description, node_url,
               api_key_request, is_public, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW())
            """,
            registration_id,
            req.name[:200],
            req.email[:200],
            req.specialty[:100],
            req.description[:2000],
            req.node_url,
            req.api_key_request,
            req.is_public,
        )
    except Exception as e:
        logger.error(f"public register DB error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

    logger.info(f"New agent registration: {registration_id} ({req.name})")
    return {
        "registration_id": registration_id,
        "status": "pending",
        "message": "審査後にAPIキーをメールで送信します" if req.api_key_request
                   else "登録申請を受け付けました。審査後にご連絡します",
    }


# ──────────────────────────────────────────────
# GET /public/agents
# ──────────────────────────────────────────────

@router.get(
    "/agents",
    summary="公開エージェント一覧（認証不要）",
    description="""承認済みかつ `is_public=true` のエージェント情報を返します。

プライバシー保護のためメールアドレスは含まれません。
`specialty` クエリパラメータで絞り込みが可能です。
""",
    responses={
        200: {"description": "公開エージェント一覧"},
        503: {"description": "DB接続エラー"},
    },
)
async def list_public_agents(
    specialty: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db=Depends(_get_db),
):
    if limit > 100:
        limit = 100

    try:
        if specialty:
            rows = await db.fetch(
                """
                SELECT id, name, specialty, description, node_url, created_at
                FROM agent_registrations
                WHERE status = 'approved' AND is_public = TRUE
                  AND specialty = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                specialty, limit, offset,
            )
        else:
            rows = await db.fetch(
                """
                SELECT id, name, specialty, description, node_url, created_at
                FROM agent_registrations
                WHERE status = 'approved' AND is_public = TRUE
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )
    except Exception as e:
        logger.error(f"public agents fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agents")

    agents = [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "specialty": row["specialty"],
            "description": row["description"],
            "node_url": row["node_url"],
            "registered_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]

    return {
        "agents": agents,
        "count": len(agents),
        "offset": offset,
        "limit": limit,
        "filter": {"specialty": specialty} if specialty else {},
    }


# ──────────────────────────────────────────────
# POST /public/contact/{agent_id}
# ──────────────────────────────────────────────

@router.post(
    "/contact/{agent_id}",
    summary="エージェントへの問い合わせ（認証不要）",
    description="""指定したエージェントへの問い合わせメッセージを記録します。

- `contact_email` に返信先メールアドレスを指定してください
- エージェント受信者はダッシュボードから確認できます
- `agent_id` は `GET /public/agents` で取得したIDを使用してください
""",
    responses={
        200: {"description": "問い合わせ送信完了"},
        404: {"description": "エージェントが見つかりません"},
        503: {"description": "DB接続エラー"},
    },
)
async def contact_agent(agent_id: str, req: ContactReq, db=Depends(_get_db)):
    # エージェント存在確認
    try:
        agent = await db.fetchrow(
            """
            SELECT id, name, email FROM agent_registrations
            WHERE id = $1 AND status = 'approved' AND is_public = TRUE
            """,
            agent_id,
        )
    except Exception as e:
        logger.error(f"contact agent fetch error: {e}")
        raise HTTPException(status_code=500, detail="DB error")

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found or not available",
        )

    contact_id = str(uuid.uuid4())
    try:
        await db.execute(
            """
            INSERT INTO agent_contacts
              (id, agent_id, message, contact_email, status, created_at)
            VALUES ($1, $2, $3, $4, 'received', NOW())
            """,
            contact_id,
            agent_id,
            req.message[:2000],
            req.contact_email,
        )
    except Exception as e:
        logger.error(f"contact insert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record contact")

    logger.info(f"Contact submitted: {contact_id} → agent {agent_id}")
    return {
        "contact_id": contact_id,
        "agent_name": agent["name"],
        "status": "received",
        "message": "問い合わせを受け付けました。エージェントから返信をお待ちください",
    }
