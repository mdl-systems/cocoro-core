"""
Resend Email Engine — cocoro-core
Resend API を使ったメール送信エンジン。
HTMLテンプレート生成・送信履歴保存を担当。
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone, time as dtime
from typing import Any

import httpx

logger = logging.getLogger("cocoro.email")

# ──────────────────────────────────────────────
# HTML メールテンプレート
# ──────────────────────────────────────────────

_BASE_STYLE = """
<style>
  body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f0f1a; margin: 0; padding: 0; }
  .wrapper { max-width: 600px; margin: 40px auto; background: #1a1a2e; border-radius: 16px;
             overflow: hidden; box-shadow: 0 8px 32px rgba(139,92,246,0.2); }
  .header  { background: linear-gradient(135deg, #6d28d9, #4f46e5); padding: 32px 40px; text-align: center; }
  .header h1 { color: #fff; margin: 0; font-size: 24px; letter-spacing: 1px; }
  .header .emoji { font-size: 48px; display: block; margin-bottom: 12px; }
  .body    { padding: 32px 40px; color: #e2e8f0; line-height: 1.7; }
  .body h2 { color: #a78bfa; margin-top: 0; }
  .card    { background: #0f0f1a; border-radius: 12px; padding: 20px 24px; margin: 20px 0;
             border-left: 4px solid #6d28d9; }
  .stat    { display: inline-block; padding: 4px 12px; border-radius: 20px;
             background: #6d28d9; color: #fff; font-weight: bold; font-size: 18px; }
  .footer  { padding: 20px 40px; text-align: center; font-size: 12px; color: #64748b;
             border-top: 1px solid #1e293b; }
  .btn     { display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #6d28d9, #4f46e5);
             color: #fff !important; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px; }
</style>
"""


def _wrap(header_emoji: str, header_title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_BASE_STYLE}</head><body>
<div class="wrapper">
  <div class="header">
    <span class="emoji">{header_emoji}</span>
    <h1>{header_title}</h1>
  </div>
  <div class="body">{body_html}</div>
  <div class="footer">
    <p>Cocoro AI — Personality OS</p>
    <p style="margin:0;">© 2026 MDL Systems. このメールはシステムから自動送信されました。</p>
  </div>
</div></body></html>"""


TEMPLATES: dict[str, dict[str, Any]] = {

    "task_complete": {
        "subject_default": "✅ タスクが完了しました",
        "render": lambda d: _wrap("✅", "タスク完了", f"""
<h2>{d.get('task_title', 'タスク')}</h2>
<div class="card">
  <p><strong>結果:</strong></p>
  <p>{d.get('result_summary', '完了しました。')}</p>
</div>
<p>タスクの詳細はダッシュボードでご確認ください。</p>
<p><a class="btn" href="{d.get('dashboard_url', 'http://localhost:8001/dashboard')}">
  ダッシュボードを開く
</a></p>
"""),
    },

    "daily_brief": {
        "subject_default": "🌅 デイリーブリーフィング",
        "render": lambda d: _wrap("🌅", "デイリーブリーフィング", f"""
<h2>{d.get('date', '今日')}のサマリー</h2>
<div class="card">
  <p>📝 <strong>昨日の会話:</strong> {d.get('conversation_count', 0)} 件</p>
  <p>🎯 <strong>完了タスク:</strong> {d.get('completed_tasks', 0)} 件</p>
  <p>❤️ <strong>シンクロ率:</strong> <span class="stat">{d.get('sync_rate', '---')}%</span></p>
  <p>😊 <strong>主要感情:</strong> {d.get('dominant_emotion', 'neutral')}</p>
</div>
{f'<div class="card"><p><strong>💡 洞察:</strong></p><p>{d["insight"]}</p></div>' if d.get('insight') else ''}
<p>今日も一日よろしくお願いします！</p>
"""),
    },

    "sync_milestone": {
        "subject_default": "🎉 シンクロ率マイルストーン達成！",
        "render": lambda d: _wrap("💜", f"シンクロ率 {d.get('rate', '?')}% 達成！", f"""
<h2>🎉 マイルストーン達成おめでとうございます！</h2>
<div class="card" style="text-align:center;">
  <p style="font-size:14px;color:#a78bfa;margin-bottom:4px;">現在のシンクロ率</p>
  <p><span class="stat" style="font-size:36px;">{d.get('rate', '?')}%</span></p>
  <p style="color:#94a3b8;font-size:14px;">トレンド: {d.get('trend', 'stable')} {d.get('delta_str','')}</p>
</div>
{f'<p style="color:#a78bfa;font-style:italic;">"{d["message"]}"</p>' if d.get('message') else ''}
<p>あなたとAIの価値観・思考パターンの一致度が高まっています。
引き続き会話を続けてシンクロ率を高めましょう！</p>
"""),
    },

    "welcome": {
        "subject_default": "🎊 Cocoro AIへようこそ！",
        "render": lambda d: _wrap("🎊", "セットアップ完了！", f"""
<h2>ようこそ、{d.get('owner_name', 'ユーザー')} さん！</h2>
<p>Cocoro AI の初期設定が完了しました。あなただけの人格AIが起動しています。</p>
<div class="card">
  <p>🧠 <strong>人格:</strong> {d.get('personality_summary', '設定完了')}</p>
  <p>💜 <strong>初期シンクロ率:</strong> <span class="stat">{d.get('initial_sync', '50')}%</span></p>
  <p>🌟 <strong>主な価値観:</strong> {d.get('top_values', '---')}</p>
</div>
<p>まず「自己紹介してください」と話しかけてみましょう！</p>
<p><a class="btn" href="{d.get('dashboard_url', 'http://localhost:8001/dashboard')}">
  今すぐ始める
</a></p>
"""),
    },
}


# ──────────────────────────────────────────────
# EmailEngine
# ──────────────────────────────────────────────

class EmailEngine:
    """Resend API 経由のメール送信エンジン"""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self, db_pool, api_key: str, from_email: str):
        self._pool = db_pool
        self._api_key = api_key
        self._from_email = from_email
        self._enabled = bool(api_key)
        logger.info(f"EmailEngine: enabled={self._enabled}, from={from_email}")

    # ── 送信 ──────────────────────────────────

    async def send(
        self,
        to: str | list[str],
        subject: str,
        template: str,
        data: dict[str, Any] | None = None,
        triggered_by: str = "api",
    ) -> dict:
        """メール送信。履歴を DB に保存して結果を返す。"""
        data = data or {}
        to_list = [to] if isinstance(to, str) else to

        # テンプレートをHTMLに変換
        tmpl = TEMPLATES.get(template)
        if not tmpl:
            raise ValueError(f"Unknown template: {template}. Available: {list(TEMPLATES.keys())}")

        html_body = tmpl["render"](data)
        final_subject = subject or tmpl["subject_default"]

        email_id = str(uuid.uuid4())
        status = "pending"
        resend_id = None
        error_msg = None

        if not self._enabled:
            logger.warning("EmailEngine: RESEND_API_KEY not set, mail skipped (dry-run)")
            status = "skipped"
        else:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        self.RESEND_API_URL,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": f"Cocoro AI <{self._from_email}>",
                            "to": to_list,
                            "subject": final_subject,
                            "html": html_body,
                        },
                    )
                if resp.status_code in (200, 201):
                    resp_data = resp.json()
                    resend_id = resp_data.get("id")
                    status = "sent"
                    logger.info(f"Email sent: {resend_id} → {to_list}")
                else:
                    error_msg = f"Resend API error {resp.status_code}: {resp.text[:200]}"
                    status = "failed"
                    logger.error(f"Email failed: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                status = "error"
                logger.error(f"Email exception: {e}")

        # 履歴を DB 保存（失敗でも保存）
        try:
            await self._save_history(
                email_id, to_list, final_subject, template, status, resend_id, error_msg, triggered_by
            )
        except Exception as e:
            logger.error(f"Email history save failed: {e}")

        return {
            "id": email_id,
            "resend_id": resend_id,
            "status": status,
            "to": to_list,
            "subject": final_subject,
            "template": template,
            "error": error_msg,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _save_history(
        self, email_id, to_list, subject, template, status, resend_id, error_msg, triggered_by
    ):
        await self._pool.execute(
            """
            INSERT INTO email_history
              (id, to_addresses, subject, template, status, resend_id, error_msg,
               triggered_by, sent_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
            email_id,
            to_list,
            subject,
            template,
            status,
            resend_id,
            error_msg,
            triggered_by,
        )

    # ── 履歴取得 ─────────────────────────────

    async def get_history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT id, to_addresses, subject, template, status, resend_id,
                   error_msg, triggered_by, sent_at
            FROM email_history
            ORDER BY sent_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
        return [
            {
                "id": str(r["id"]),
                "to": r["to_addresses"],
                "subject": r["subject"],
                "template": r["template"],
                "status": r["status"],
                "resend_id": r["resend_id"],
                "error": r["error_msg"],
                "triggered_by": r["triggered_by"],
                "sent_at": r["sent_at"].isoformat() if r["sent_at"] else None,
            }
            for r in rows
        ]

    # ── シンクロ率マイルストーン判定 ────────

    MILESTONES = [50.0, 75.0, 90.0, 100.0]

    async def check_sync_milestone(self, current_rate: float, to_email: str | None = None):
        """シンクロ率がマイルストーンを超えた場合にメール送信"""
        if not to_email:
            return
        for milestone in self.MILESTONES:
            if current_rate >= milestone:
                # 既に同マイルストーンのメールを送ったか確認
                row = await self._pool.fetchrow(
                    """
                    SELECT id FROM email_history
                    WHERE template = 'sync_milestone'
                      AND subject LIKE $1
                      AND status IN ('sent', 'skipped')
                    LIMIT 1
                    """,
                    f"%{int(milestone)}%",
                )
                if not row:
                    delta = current_rate - milestone
                    await self.send(
                        to=to_email,
                        subject=f"🎉 シンクロ率 {int(milestone)}% 達成！",
                        template="sync_milestone",
                        data={
                            "rate": round(current_rate, 1),
                            "trend": "up",
                            "delta_str": f"(+{delta:.1f}%)",
                            "message": f"シンクロ率 {int(milestone)}% を達成しました！",
                        },
                        triggered_by="auto_milestone",
                    )
                    break  # 一度に1マイルストーンのみ送信

    # ── デイリーブリーフィングスケジューラ ──

    async def run_daily_brief_scheduler(self, send_hour: int = 9):
        """毎朝 send_hour 時にデイリーブリーフィングを送信"""
        logger.info(f"Email: daily brief scheduler started (send at {send_hour}:00)")
        while True:
            now = datetime.now(timezone.utc).astimezone()
            target = now.replace(hour=send_hour, minute=0, second=0, microsecond=0)
            if now >= target:
                from datetime import timedelta
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info(f"Email: next daily brief in {wait_seconds/3600:.1f}h")
            await asyncio.sleep(wait_seconds)

            try:
                await self._send_daily_brief()
            except Exception as e:
                logger.error(f"Daily brief error: {e}")

    async def _send_daily_brief(self):
        """デイリーブリーフィングデータを収集して送信"""
        try:
            # 受信者メールを identity から取得
            row = await self._pool.fetchrow(
                "SELECT owner_name, profile FROM identity LIMIT 1"
            )
            if not row:
                logger.warning("Email: no identity found, skip daily brief")
                return
            owner_name = row["owner_name"]

            # 過去24時間の会話数
            conv_count = await self._pool.fetchval(
                "SELECT COUNT(*) FROM conversation_log WHERE created_at > NOW() - INTERVAL '24 hours'"
            ) or 0

            # 完了タスク数
            task_count = await self._pool.fetchval(
                "SELECT COUNT(*) FROM tasks WHERE status='completed' AND updated_at > NOW() - INTERVAL '24 hours'"
            ) or 0

            # シンクロ率
            sync_row = await self._pool.fetchrow(
                "SELECT sync_rate FROM sync_rate_history ORDER BY created_at DESC LIMIT 1"
            )
            sync_rate = round(sync_row["sync_rate"], 1) if sync_row else "---"

            # 感情状態
            emotion_row = await self._pool.fetchrow(
                "SELECT dominant_emotion FROM emotion_state LIMIT 1"
            )
            dominant_emotion = emotion_row["dominant_emotion"] if emotion_row else "neutral"

            # 最新インサイト
            insight_row = await self._pool.fetchrow(
                "SELECT content FROM thought_log ORDER BY created_at DESC LIMIT 1"
            )
            insight = insight_row["content"][:200] if insight_row else None

            from datetime import date
            date_str = date.today().strftime("%Y年%m月%d日")

            # 送信先メール (identity のProfileにメールが含まれていれば使う、なければ skip)
            to_email = os.getenv("OWNER_EMAIL", "")
            if not to_email:
                logger.info("Email: OWNER_EMAIL not set, skip daily brief")
                return

            await self.send(
                to=to_email,
                subject=f"🌅 {date_str} デイリーブリーフィング",
                template="daily_brief",
                data={
                    "date": date_str,
                    "conversation_count": conv_count,
                    "completed_tasks": task_count,
                    "sync_rate": sync_rate,
                    "dominant_emotion": dominant_emotion,
                    "insight": insight,
                },
                triggered_by="scheduler_daily",
            )
        except Exception as e:
            logger.error(f"_send_daily_brief error: {e}")
