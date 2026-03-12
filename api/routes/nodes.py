"""
Cocoro Node Registration & Discovery API
複数miniPC対応のノード管理エンドポイント
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("cocoro.nodes")

router = APIRouter(prefix="/nodes", tags=["nodes"])

# DB pool は server.py の lifespan で設定された module-level 変数を参照
# （循環インポートを避けるため遅延import）


# ─── リクエスト/レスポンスモデル ─────────────────────────────────────────

class NodeRegisterReq(BaseModel):
    node_id: str                     # 例: "minipc-b"
    ip: str                          # 例: "192.168.50.93"
    port: int = 8001                 # cocoro-core ポート
    roles: list[str] = []            # 担当するロールID
    name: str = ""                   # 表示名


class NodeInfo(BaseModel):
    node_id: str
    name: str
    ip: str
    port: int
    roles: list[str]
    status: str                      # "online" | "offline" | "unknown"
    last_seen: str | None
    registered_at: str | None


# ─── ヘルパー ───────────────────────────────────────────────────────────

def _get_db():
    """server.py のモジュールレベル db_pool を遅延取得"""
    import api.server as _srv
    return _srv.db_pool


async def _ping_node(ip: str, port: int, timeout: float = 2.0) -> bool:
    """対象ノードの /health エンドポイントにpingを送る"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"http://{ip}:{port}/health")
            return r.status_code == 200
    except Exception:
        return False



async def _update_status(db, node_id: str, online: bool):
    """DBのステータスと最終確認日時を更新"""
    status = "online" if online else "offline"
    await db.execute(
        """
        UPDATE cocoro_nodes
        SET status = $1, last_seen = $2, updated_at = NOW()
        WHERE node_id = $3
        """,
        status,
        datetime.now(timezone.utc) if online else None,
        node_id,
    )


# ─── エンドポイント ─────────────────────────────────────────────────────

@router.post("/register", summary="ノードを登録")
async def register_node(req: NodeRegisterReq):
    """別のminiPC(cocoro-core/agent)を登録する"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    await db.execute(
        """
        INSERT INTO cocoro_nodes (node_id, name, ip, port, roles, status, updated_at)
        VALUES ($1, $2, $3, $4, $5, 'unknown', NOW())
        ON CONFLICT (node_id) DO UPDATE
            SET name       = EXCLUDED.name,
                ip         = EXCLUDED.ip,
                port       = EXCLUDED.port,
                roles      = EXCLUDED.roles,
                status     = 'unknown',
                updated_at = NOW()
        """,
        req.node_id, req.name, req.ip, req.port, req.roles,
    )

    # 登録直後にpingで状態確認
    online = await _ping_node(req.ip, req.port)
    await _update_status(db, req.node_id, online)

    logger.info(f"Node registered: {req.node_id} ({req.ip}:{req.port}) roles={req.roles} online={online}")
    return {
        "node_id": req.node_id,
        "status": "online" if online else "offline",
        "message": "登録完了",
    }


@router.get("", summary="登録済みノード一覧（死活確認付き）")
async def list_nodes():
    """全ノードの情報とオンライン状態を返す"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    rows = await db.fetch(
        "SELECT * FROM cocoro_nodes ORDER BY registered_at DESC"
    )

    # 全ノードに並列でpingを送る
    async def _check(row):
        online = await _ping_node(row["ip"], row["port"])
        await _update_status(db, row["node_id"], online)
        return {
            "node_id":       row["node_id"],
            "name":          row["name"],
            "ip":            row["ip"],
            "port":          row["port"],
            "roles":         list(row["roles"] or []),
            "status":        "online" if online else "offline",
            "last_seen":     str(row["last_seen"]) if row["last_seen"] else None,
            "registered_at": str(row["registered_at"]) if row["registered_at"] else None,
        }

    nodes = await asyncio.gather(*[_check(r) for r in rows])
    return {"nodes": list(nodes), "count": len(nodes)}


@router.get("/{node_id}/health", summary="対象ノードの死活確認")
async def node_health(node_id: str):
    """指定ノードのヘルス状態を返す"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    row = await db.fetchrow(
        "SELECT * FROM cocoro_nodes WHERE node_id = $1", node_id
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    online = await _ping_node(row["ip"], row["port"])
    await _update_status(db, node_id, online)

    return {
        "node_id": node_id,
        "ip":      row["ip"],
        "port":    row["port"],
        "status":  "online" if online else "offline",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── ノード経由チャット転送ユーティリティ ──────────────────────────────

async def find_node_for_role(db, role_id: str) -> dict | None:
    """
    指定 role_id を担当しているオンライン（またはunknown）ノードを返す。
    ローカルノードは除外。
    """
    if db is None or not role_id:
        return None
    row = await db.fetchrow(
        """
        SELECT * FROM cocoro_nodes
        WHERE $1 = ANY(roles)
          AND status != 'offline'
        ORDER BY last_seen DESC NULLS LAST
        LIMIT 1
        """,
        role_id,
    )
    return dict(row) if row else None


async def forward_to_node(node: dict, message: str, session_id: str, role_id: str):
    """
    リモートノードの /chat/stream にリクエストを転送して
    SSE ストリームをそのまま yield する非同期ジェネレータ
    """
    url = f"http://{node['ip']}:{node['port']}/chat/stream"
    payload = {"message": message, "session_id": session_id, "role_id": role_id}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        yield line + "\n\n"
    except Exception as e:
        import json as _json
        err = _json.dumps({"text": f"ノード転送エラー: {e}"})
        yield f"data: {err}\n\n"
        final = _json.dumps({
            "type": "final", "sessionId": session_id,
            "action": "error", "emotion": {"dominant": "neutral"}
        })
        yield f"data: {final}\n\n"
