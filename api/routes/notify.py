"""
Notification / Email API Routes
  POST /notify/email       — メール送信
  GET  /notify/history     — 送信履歴
  GET  /notify/templates   — 利用可能テンプレート一覧
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("cocoro.notify")

router = APIRouter(prefix="/notify", tags=["admin"])


# ──────────────────────────────────────────────
# 依存性
# ──────────────────────────────────────────────

def _get_email_engine():
    import api.server as _srv
    if not hasattr(_srv, "email_engine") or _srv.email_engine is None:
        raise HTTPException(status_code=503, detail="Email engine not initialized")
    return _srv.email_engine


def _verify_key():
    from api.server import verify_api_key
    return verify_api_key


# ──────────────────────────────────────────────
# リクエストモデル
# ──────────────────────────────────────────────

class SendEmailReq(BaseModel):
    to: str | list[str]
    subject: str = ""
    template: str
    data: dict = {}


# ──────────────────────────────────────────────
# POST /notify/email
# ──────────────────────────────────────────────

@router.post(
    "/email",
    summary="メール送信",
    description="""Resend API を使ってメールを送信します。

**利用可能テンプレート:**
- `task_complete` — タスク完了通知
- `daily_brief` — デイリーブリーフィング
- `sync_milestone` — シンクロ率マイルストーン達成
- `welcome` — 初回セットアップ完了

`RESEND_API_KEY` が未設定の場合は `status: skipped` を返します（履歴には保存されます）。
""",
)
async def send_email(
    req: SendEmailReq,
    _=Depends(_verify_key),
    engine=Depends(_get_email_engine),
):
    try:
        result = await engine.send(
            to=req.to,
            subject=req.subject,
            template=req.template,
            data=req.data,
            triggered_by="api",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"send_email error: {e}")
        raise HTTPException(status_code=500, detail=f"Send failed: {e}")

    return result


# ──────────────────────────────────────────────
# GET /notify/history
# ──────────────────────────────────────────────

@router.get(
    "/history",
    summary="送信済みメール履歴",
    description="送信済みメールの一覧を返します。最新順。`limit` / `offset` でページネーション。",
)
async def get_email_history(
    limit: int = 50,
    offset: int = 0,
    _=Depends(_verify_key),
    engine=Depends(_get_email_engine),
):
    if limit > 200:
        limit = 200
    try:
        history = await engine.get_history(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {
        "history": history,
        "count": len(history),
        "limit": limit,
        "offset": offset,
    }


# ──────────────────────────────────────────────
# GET /notify/templates
# ──────────────────────────────────────────────

@router.get(
    "/templates",
    summary="利用可能なメールテンプレート一覧",
    description="メール送信で指定できるテンプレートの一覧を返します。",
)
async def list_templates(_=Depends(_verify_key)):
    from agent.email_engine import TEMPLATES
    return {
        "templates": [
            {
                "id": key,
                "subject_default": tmpl["subject_default"],
            }
            for key, tmpl in TEMPLATES.items()
        ],
        "count": len(TEMPLATES),
    }
