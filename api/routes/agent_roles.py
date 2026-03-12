"""
Agent Roles API
専門職エージェントのロール定義とエンドポイント
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/agents", tags=["agents"])

# ─── ロール定義 ────────────────────────────────────────────────────────
AGENT_ROLES: dict[str, dict] = {
    "lawyer": {
        "id": "lawyer",
        "name": "弁護士エージェント",
        "specialty": "法律・契約・権利関係",
        "system_prompt": (
            "あなたは経験豊富な弁護士です。法律的観点から正確なアドバイスを提供します。"
            "契約書レビュー、法的リスク分析、権利関係の整理が得意です。"
        ),
    },
    "accountant": {
        "id": "accountant",
        "name": "税理士エージェント",
        "specialty": "税務・会計・節税",
        "system_prompt": (
            "あなたは税理士です。税務申告、節税対策、会計処理について"
            "専門的なアドバイスを提供します。"
        ),
    },
    "doctor": {
        "id": "doctor",
        "name": "医療アドバイザー",
        "specialty": "健康・医療・予防",
        "system_prompt": (
            "あなたは医療アドバイザーです。健康管理、症状の一般的な情報提供、"
            "予防医学についてアドバイスします。※診断は行いません。"
        ),
    },
    "engineer": {
        "id": "engineer",
        "name": "エンジニアエージェント",
        "specialty": "ソフトウェア開発・設計・レビュー",
        "system_prompt": (
            "あなたはシニアソフトウェアエンジニアです。コードレビュー、"
            "アーキテクチャ設計、技術的な問題解決が得意です。"
        ),
    },
    "financial_advisor": {
        "id": "financial_advisor",
        "name": "ファイナンシャルアドバイザー",
        "specialty": "資産運用・投資・財務計画",
        "system_prompt": (
            "あなたはファイナンシャルアドバイザーです。資産運用、投資戦略、"
            "財務計画についてアドバイスします。"
        ),
    },
    "researcher": {
        "id": "researcher",
        "name": "リサーチエージェント",
        "specialty": "情報収集・分析・レポート作成",
        "system_prompt": (
            "あなたは優秀なリサーチャーです。あらゆるトピックについて深く調査し、"
            "構造化されたレポートを作成します。"
        ),
    },
}


def get_role_system_prompt(role_id: str | None) -> str | None:
    """role_id からシステムプロンプトを返す（None の場合は None）"""
    if not role_id:
        return None
    role = AGENT_ROLES.get(role_id)
    return role["system_prompt"] if role else None


# ─── エンドポイント ────────────────────────────────────────────────────

@router.get("/roles", summary="利用可能なエージェントロール一覧")
async def list_roles():
    return {
        "roles": list(AGENT_ROLES.values()),
        "count": len(AGENT_ROLES),
    }


@router.get("/roles/{role_id}", summary="エージェントロール詳細")
async def get_role(role_id: str):
    role = AGENT_ROLES.get(role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail=f"Role '{role_id}' not found. Available: {list(AGENT_ROLES.keys())}",
        )
    return role
