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
    node_id: str                     # 例: "minipc-engineer"
    ip: str                          # 例: "192.168.50.86"
    port: int = 8001                 # cocoro-core ポート
    agent_port: int = 8002           # cocoro-agent ポート
    roles: list[str] = []            # 担当するロールID
    name: str = ""                   # 表示名


class NodeInfo(BaseModel):
    node_id: str
    name: str
    ip: str
    port: int
    agent_port: int
    roles: list[str]
    status: str                      # "online" | "offline" | "unknown"
    last_seen: str | None
    registered_at: str | None


# ─── ヘルパー ───────────────────────────────────────────────────────────

def _get_db():
    """server.py のモジュールレベル db_pool を遅延取得"""
    import api.server as _srv
    return _srv.db_pool


async def _ping_node(ip: str, port: int, timeout: float = 3.0) -> bool:
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


def _fmt_row(row: dict, online: bool) -> dict:
    """DBレコード → レスポンス辞書に変換"""
    return {
        "node_id":       row["node_id"],
        "name":          row["name"],
        "ip":            row["ip"],
        "port":          row["port"],
        "agent_port":    row.get("agent_port", 8002),
        "roles":         list(row["roles"] or []),
        "status":        "online" if online else "offline",
        "last_seen":     row["last_seen"].isoformat() if row["last_seen"] else None,
        "registered_at": row["registered_at"].isoformat() if row["registered_at"] else None,
    }


# ─── エンドポイント ─────────────────────────────────────────────────────

@router.post("/register", summary="ノードを登録")
async def register_node(req: NodeRegisterReq):
    """別のminiPC(cocoro-core/agent)を登録する"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    await db.execute(
        """
        INSERT INTO cocoro_nodes (node_id, name, ip, port, agent_port, roles, status, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, 'unknown', NOW())
        ON CONFLICT (node_id) DO UPDATE
            SET name       = EXCLUDED.name,
                ip         = EXCLUDED.ip,
                port       = EXCLUDED.port,
                agent_port = EXCLUDED.agent_port,
                roles      = EXCLUDED.roles,
                status     = 'unknown',
                updated_at = NOW()
        """,
        req.node_id, req.name, req.ip, req.port, req.agent_port, req.roles,
    )

    # 登録直後にpingで状態確認
    online = await _ping_node(req.ip, req.port)
    await _update_status(db, req.node_id, online)

    logger.info(
        f"Node registered: {req.node_id} ({req.ip}:{req.port})"
        f" agent_port={req.agent_port} roles={req.roles} online={online}"
    )
    return {
        "node_id":    req.node_id,
        "status":     "online" if online else "offline",
        "message":    "登録完了",
        "agent_url":  f"http://{req.ip}:{req.agent_port}",
    }


@router.get("", summary="登録済みノード一覧")
async def list_nodes(live_check: bool = False):
    """全ノードの情報を返す。

    live_check=true のときはリアルタイムpingを実行（低速）。
    デフォルトは DB のキャッシュ状態を返す（高速）。
    """
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    rows = await db.fetch(
        "SELECT * FROM cocoro_nodes ORDER BY registered_at DESC"
    )

    if live_check:
        # リアルタイムping（全ノード並列）
        async def _check(row):
            online = await _ping_node(row["ip"], row["port"])
            await _update_status(db, row["node_id"], online)
            return _fmt_row(dict(row), online)

        nodes = list(await asyncio.gather(*[_check(r) for r in rows]))
    else:
        # DBキャッシュ状態を返す（高速）
        nodes = [_fmt_row(dict(r), r["status"] == "online") for r in rows]

    return {"nodes": nodes, "count": len(nodes)}


@router.get("/{node_id}", summary="ノード詳細情報")
async def get_node(node_id: str):
    """指定ノードの詳細情報を返す（DBキャッシュ）"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    row = await db.fetchrow(
        "SELECT * FROM cocoro_nodes WHERE node_id = $1", node_id
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    return _fmt_row(dict(row), row["status"] == "online")


@router.get("/{node_id}/health", summary="対象ノードの死活確認（リアルタイム）")
async def node_health(node_id: str):
    """指定ノードにpingを送りヘルス状態を返す"""
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
        "node_id":    node_id,
        "ip":         row["ip"],
        "port":       row["port"],
        "agent_port": row.get("agent_port", 8002),
        "status":     "online" if online else "offline",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{node_id}", summary="ノード登録解除")
async def unregister_node(node_id: str):
    """指定ノードの登録を削除する"""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="DB not ready")

    result = await db.execute(
        "DELETE FROM cocoro_nodes WHERE node_id = $1", node_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    logger.info(f"Node unregistered: {node_id}")
    return {"node_id": node_id, "message": "登録削除完了"}


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
    SSE ストリームをそのまま yield する非同期ジェネレータ。

    転送先: cocoro-core ポート（port）の /chat/stream
    Authorization ヘッダーは cocoro-core の COCORO_API_KEY を使用。
    """
    import os
    url = f"http://{node['ip']}:{node['port']}/chat/stream"
    payload = {"message": message, "session_id": session_id, "role_id": role_id}

    # ローカルの COCORO_API_KEY を転送ノードへの認証として使用
    api_key = os.getenv("COCORO_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    logger.info(
        f"Forwarding to node {node['node_id']} ({node['ip']}:{node['port']}) "
        f"role={role_id} session={session_id[:8]}"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    import json as _json
                    err = _json.dumps({
                        "text": f"ノード {node['node_id']} への転送に失敗しました (HTTP {resp.status_code})"
                    })
                    yield f"data: {err}\n\n"
                    final = _json.dumps({
                        "type": "final", "sessionId": session_id,
                        "action": "error", "emotion": {"dominant": "neutral"}
                    })
                    yield f"data: {final}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line:
                        yield line + "\n\n"
    except httpx.ConnectError:
        import json as _json
        err = _json.dumps({"text": f"ノード {node['node_id']} ({node['ip']}) に接続できません。オフラインの可能性があります。"})
        yield f"data: {err}\n\n"
        # ノードをオフラインに更新
        try:
            db = _get_db()
            if db:
                await _update_status(db, node["node_id"], False)
        except Exception:
            pass
        final = _json.dumps({
            "type": "final", "sessionId": session_id,
            "action": "error", "emotion": {"dominant": "neutral"}
        })
        yield f"data: {final}\n\n"
    except Exception as e:
        import json as _json
        err = _json.dumps({"text": f"ノード転送エラー: {e}"})
        yield f"data: {err}\n\n"
        final = _json.dumps({
            "type": "final", "sessionId": session_id,
            "action": "error", "emotion": {"dominant": "neutral"}
        })
        yield f"data: {final}\n\n"


async def forward_task_to_agent(node: dict, message: str, session_id: str, role_id: str):
    """
    リモートノードの cocoro-agent (agent_port) にタスクを投入して
    SSE ストリームを cocoro-core の /chat/stream 形式に変換して yield する。

    フロー:
      1. POST http://NODE_IP:{agent_port}/tasks  → task_id を取得
      2. GET  http://NODE_IP:{agent_port}/tasks/{task_id}/stream (SSE) → 進捗を転送
      3. GET  http://NODE_IP:{agent_port}/tasks/{task_id}/result → 最終結果を /chat/stream 形式で返す
    """
    import os
    import json as _json

    agent_port = node.get("agent_port", 8002)
    base_url   = f"http://{node['ip']}:{agent_port}"
    api_key    = os.getenv("COCORO_API_KEY", "")
    headers    = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    logger.info(
        f"[AgentForward] node={node['node_id']} ({node['ip']}:{agent_port}) "
        f"role={role_id} session={session_id[:8]}"
    )

    # ── Step1: タスク投入 ──────────────────────────────────────────────────
    task_payload = {
        "title":       message[:200],
        "description": message,
        "type":        "auto",
        "role_id":     role_id,
        "priority":    "normal",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}/tasks",
                json=task_payload,
                headers=headers,
            )

        if resp.status_code not in (200, 201):
            err_text = resp.text[:300]
            logger.error(f"[AgentForward] Task creation failed: HTTP {resp.status_code} — {err_text}")
            yield f'data: {_json.dumps({"text": f"エージェントへのタスク投入に失敗しました (HTTP {resp.status_code})。"})}\n\n'
            yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
            return

        task_data = resp.json()
        task_id   = task_data.get("task_id") or task_data.get("id")
        if not task_id:
            yield f'data: {_json.dumps({"text": "タスクIDが取得できませんでした。"})}\n\n'
            yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
            return

        logger.info(f"[AgentForward] Task submitted: task_id={task_id[:8]} → {node['node_id']}")
        yield f'data: {_json.dumps({"text": f"[{role_id}エージェント] タスクを受け付けました。処理中..."})}\n\n'

    except httpx.ConnectError:
        # ノードをオフラインにマーク
        try:
            db = _get_db()
            if db:
                await _update_status(db, node["node_id"], False)
        except Exception:
            pass
        _nid = node["node_id"]; _nip = node["ip"]
        yield f'data: {_json.dumps({"text": f"ノード {_nid} ({_nip}) に接続できません。"})}\n\n'
        yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
        return
    except Exception as e:
        yield f'data: {_json.dumps({"text": f"タスク投入エラー: {e}"})}\n\n'
        yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
        return

    # ── Step2: SSE進捗ストリームをプロキシ ────────────────────────────────
    finished   = False
    full_text  = ""
    last_step  = ""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "GET",
                f"{base_url}/tasks/{task_id}/stream",
                headers=headers,
            ) as sse_resp:
                async for raw_line in sse_resp.aiter_lines():
                    # SSE "data: {...}" 行を解析
                    if not raw_line.startswith("data:"):
                        continue
                    payload_str = raw_line[5:].strip()
                    if not payload_str:
                        continue

                    try:
                        event = _json.loads(payload_str)
                    except Exception:
                        continue

                    event_type = event.get("event") or event.get("type", "")
                    data       = event.get("data", event)

                    if event_type in ("progress", "step"):
                        step     = data.get("step") or data.get("current_step", "")
                        progress = data.get("progress", 0)
                        if step and step != last_step:
                            last_step = step
                            yield f'data: {_json.dumps({"text": f"[{progress}%] {step}"})}\n\n'

                    elif event_type in ("tool_use", "tool"):
                        tool = data.get("tool", "")
                        yield f'data: {_json.dumps({"text": f"[ツール] {tool} を実行中..."})}\n\n'

                    elif event_type in ("completed", "complete", "done"):
                        finished = True
                        result   = data.get("result") or data
                        full_text = (
                            result.get("full_response")
                            or result.get("text")
                            or result.get("summary")
                            or _json.dumps(result, ensure_ascii=False)
                            if isinstance(result, dict) else str(result)
                        )
                        break

                    elif event_type == "error":
                        error_msg = data.get("error") or data.get("message") or "エラーが発生しました"
                        yield f'data: {_json.dumps({"text": f"エラー: {error_msg}"})}\n\n'
                        yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "error", "emotion": {"dominant": "neutral"}})}\n\n'
                        return

    except (httpx.ReadTimeout, asyncio.TimeoutError):
        logger.warning(f"[AgentForward] SSE stream timed out for task {task_id[:8]}, polling result...")
        # タイムアウト時は直接結果を取得

    # ── Step3: 結果を取得（SSEが終了したか、タイムアウしたとき） ──────────
    if not finished or not full_text:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                result_resp = await client.get(
                    f"{base_url}/tasks/{task_id}/result",
                    headers=headers,
                )
            if result_resp.status_code == 200:
                result_data = result_resp.json()
                result_obj  = result_data.get("result") or result_data
                full_text   = (
                    result_obj.get("full_response")
                    or result_obj.get("text")
                    or result_obj.get("summary")
                    or _json.dumps(result_obj, ensure_ascii=False)
                    if isinstance(result_obj, dict) else str(result_obj)
                )
            elif result_resp.status_code == 202:
                # まだ処理中
                full_text = f"タスク ({task_id[:8]}) はまだ処理中です。`GET {base_url}/tasks/{task_id}/result` で結果を確認できます。"
            else:
                full_text = f"結果の取得に失敗しました (HTTP {result_resp.status_code})。task_id: {task_id}"
        except Exception as e:
            full_text = f"結果取得エラー: {e}。task_id: {task_id}"

    # ── Step4: 最終テキストを /chat/stream 形式で返す ─────────────────────
    if full_text:
        # 長い結果はチャンクに分割して送信
        CHUNK_SIZE = 500
        for i in range(0, len(full_text), CHUNK_SIZE):
            chunk = full_text[i:i + CHUNK_SIZE]
            yield f'data: {_json.dumps({"text": chunk})}\n\n'

    yield f'data: {_json.dumps({"type": "final", "sessionId": session_id, "action": "delegate", "emotion": {"dominant": "neutral"}, "task_id": task_id})}\n\n'

