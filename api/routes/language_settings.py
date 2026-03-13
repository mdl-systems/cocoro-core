"""
Language Settings API Routes
  GET  /settings/language               — 現在の言語設定を取得
  POST /settings/language               — 言語設定を変更
  GET  /settings/language/supported     — 対応言語一覧
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("cocoro.lang")

router = APIRouter(prefix="/settings", tags=["admin"])

# サポート言語定義
SUPPORTED_LANGUAGES = {
    "ja": {"name": "日本語", "prompt_directive": "日本語で応答してください。"},
    "en": {"name": "English", "prompt_directive": "Please respond in English."},
    "zh": {"name": "中文", "prompt_directive": "请用中文回答。"},
    "ko": {"name": "한국어", "prompt_directive": "한국어로 답변해 주세요."},
}


# ──────────────────────────────────────────────
# 依存性
# ──────────────────────────────────────────────

def _verify_key():
    from api.server import verify_api_key
    return verify_api_key


def _get_db():
    import api.server as _srv
    if not hasattr(_srv, "db_pool") or _srv.db_pool is None:
        raise HTTPException(status_code=503, detail="DB not initialized")
    return _srv.db_pool


# ──────────────────────────────────────────────
# リクエストモデル
# ──────────────────────────────────────────────

class LanguageSetReq(BaseModel):
    language: str


# ──────────────────────────────────────────────
# GET /settings/language
# ──────────────────────────────────────────────

@router.get(
    "/language",
    summary="現在の言語設定を取得",
    description="""システムの言語設定を返します。
この言語がAIのsystem_promptに反映され、応答言語を制御します。""",
)
async def get_language(
    _=Depends(_verify_key),
    db=Depends(_get_db),
):
    try:
        row = await db.fetchrow(
            "SELECT setting_value FROM system_settings WHERE setting_key = 'language' LIMIT 1"
        )
        lang = row["setting_value"] if row else "ja"
    except Exception:
        lang = "ja"

    lang_info = SUPPORTED_LANGUAGES.get(lang, SUPPORTED_LANGUAGES["ja"])
    return {
        "language": lang,
        "name": lang_info["name"],
        "prompt_directive": lang_info["prompt_directive"],
        "supported": list(SUPPORTED_LANGUAGES.keys()),
    }


# ──────────────────────────────────────────────
# POST /settings/language
# ──────────────────────────────────────────────

@router.post(
    "/language",
    summary="言語設定を変更",
    description="""システムの言語設定を変更します。
変更後はAIの応答言語が即座に切り替わります。

**対応言語:** `ja` (日本語) / `en` (English) / `zh` (中文) / `ko` (한국어)
""",
)
async def set_language(
    req: LanguageSetReq,
    _=Depends(_verify_key),
    db=Depends(_get_db),
):
    if req.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unsupported language: '{req.language}'",
                "supported": list(SUPPORTED_LANGUAGES.keys()),
            }
        )

    try:
        await db.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value, updated_at)
            VALUES ('language', $1, NOW())
            ON CONFLICT (setting_key) DO UPDATE
              SET setting_value = $1, updated_at = NOW()
            """,
            req.language,
        )
    except Exception as e:
        logger.error(f"Failed to save language setting: {e}")
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    lang_info = SUPPORTED_LANGUAGES[req.language]
    logger.info(f"Language changed to: {req.language}")

    return {
        "language": req.language,
        "name": lang_info["name"],
        "prompt_directive": lang_info["prompt_directive"],
        "message": f"Language set to {lang_info['name']}",
    }


# ──────────────────────────────────────────────
# GET /settings/language/supported
# ──────────────────────────────────────────────

@router.get(
    "/language/supported",
    summary="対応言語一覧",
    description="サポートしている言語の一覧を返します。",
)
async def list_supported_languages():
    return {
        "languages": [
            {
                "code": code,
                "name": info["name"],
                "prompt_directive": info["prompt_directive"],
            }
            for code, info in SUPPORTED_LANGUAGES.items()
        ],
        "count": len(SUPPORTED_LANGUAGES),
    }
