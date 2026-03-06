"""cocoro-core — Memory Archiver (C-7)
長期記憶の自動整理。古いデータを要約・アーカイブしてストレージを最適化。
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("cocoro.memory.archiver")


class MemoryArchiver:
    """記憶アーカイブエンジン"""

    # アーカイブ対象の閾値
    CONVERSATION_RETAIN_DAYS = 90     # 90日以上前の会話をアーカイブ
    THOUGHT_RETAIN_DAYS = 180         # 180日以上前の思考をアーカイブ
    DECISION_RETAIN_DAYS = 365        # 365日以上前の判断をアーカイブ
    EMOTION_RETAIN_DAYS = 30          # 30日以上前の感情履歴をアーカイブ
    OBSERVATION_RETAIN_DAYS = 60      # 60日以上前の自己観察をアーカイブ

    def __init__(self, db):
        self.db = db

    async def _ensure_archive_table(self):
        """アーカイブテーブルが存在しなければ作成"""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory_archive (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_table TEXT NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                record_count INTEGER DEFAULT 0,
                summary TEXT NOT NULL,
                detail JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

    async def get_stats(self) -> dict:
        """各テーブルの件数と古さの統計"""
        tables = {
            "conversation_log": "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM conversation_log",
            "thought_log":      "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM thought_log",
            "decision_log":     "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM decision_log",
            "emotion_history":  "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM emotion_history",
            "self_observations": "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM self_observations",
            "learning_log":     "SELECT COUNT(*) as cnt, MIN(created_at) as oldest, MAX(created_at) as newest FROM learning_log",
        }
        stats = {}
        for table, sql in tables.items():
            try:
                row = await self.db.fetchrow(sql)
                stats[table] = {
                    "count": row["cnt"] if row else 0,
                    "oldest": str(row["oldest"]) if row and row["oldest"] else None,
                    "newest": str(row["newest"]) if row and row["newest"] else None,
                }
            except Exception:
                stats[table] = {"count": 0, "oldest": None, "newest": None}

        # アーカイブ情報
        try:
            archive_row = await self.db.fetchrow(
                "SELECT COUNT(*) as cnt FROM memory_archive"
            )
            stats["archives"] = {"count": archive_row["cnt"] if archive_row else 0}
        except Exception:
            stats["archives"] = {"count": 0}

        return stats

    async def archive_conversations(self, days: int = None) -> dict:
        """古い会話をアーカイブ"""
        await self._ensure_archive_table()
        retain_days = days or self.CONVERSATION_RETAIN_DAYS
        cutoff = datetime.utcnow() - timedelta(days=retain_days)

        # アーカイブ対象をカウント
        count_row = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM conversation_log WHERE created_at < $1", cutoff
        )
        count = count_row["cnt"] if count_row else 0

        if count == 0:
            return {"table": "conversation_log", "archived": 0, "message": "アーカイブ対象なし"}

        # 期間情報取得
        period = await self.db.fetchrow(
            "SELECT MIN(created_at) as start_date, MAX(created_at) as end_date "
            "FROM conversation_log WHERE created_at < $1", cutoff
        )

        # セッション別の要約情報を収集
        sessions = await self.db.fetch(
            "SELECT session_id, COUNT(*) as msg_count, "
            "MIN(created_at) as started, MAX(created_at) as ended "
            "FROM conversation_log WHERE created_at < $1 "
            "GROUP BY session_id ORDER BY started",
            cutoff
        )

        # アーカイブレコード作成
        await self.db.execute(
            "INSERT INTO memory_archive (source_table, period_start, period_end, record_count, summary, detail) "
            "VALUES ($1, $2, $3, $4, $5, $6::jsonb)",
            "conversation_log",
            period["start_date"].date() if period["start_date"] else cutoff.date(),
            period["end_date"].date() if period["end_date"] else cutoff.date(),
            count,
            f"会話ログ {count}件をアーカイブ ({len(sessions)}セッション)",
            f'{{"sessions": {len(sessions)}, "total_messages": {count}}}',
        )

        # 古いレコード削除
        await self.db.execute(
            "DELETE FROM conversation_log WHERE created_at < $1", cutoff
        )

        logger.info(f"Archived {count} conversations ({len(sessions)} sessions)")
        return {
            "table": "conversation_log",
            "archived": count,
            "sessions": len(sessions),
            "cutoff": str(cutoff),
        }

    async def archive_emotions(self, days: int = None) -> dict:
        """古い感情履歴をアーカイブ"""
        await self._ensure_archive_table()
        retain_days = days or self.EMOTION_RETAIN_DAYS
        cutoff = datetime.utcnow() - timedelta(days=retain_days)

        count_row = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM emotion_history WHERE created_at < $1", cutoff
        )
        count = count_row["cnt"] if count_row else 0

        if count == 0:
            return {"table": "emotion_history", "archived": 0, "message": "アーカイブ対象なし"}

        await self.db.execute(
            "INSERT INTO memory_archive (source_table, period_start, period_end, record_count, summary) "
            "VALUES ($1, (SELECT MIN(created_at)::date FROM emotion_history WHERE created_at < $2), "
            "$2::date, $3, $4)",
            "emotion_history", cutoff, count,
            f"感情履歴 {count}件をアーカイブ",
        )

        await self.db.execute(
            "DELETE FROM emotion_history WHERE created_at < $1", cutoff
        )

        logger.info(f"Archived {count} emotion records")
        return {"table": "emotion_history", "archived": count}

    async def archive_observations(self, days: int = None) -> dict:
        """古い自己観察をアーカイブ"""
        await self._ensure_archive_table()
        retain_days = days or self.OBSERVATION_RETAIN_DAYS
        cutoff = datetime.utcnow() - timedelta(days=retain_days)

        count_row = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM self_observations WHERE created_at < $1", cutoff
        )
        count = count_row["cnt"] if count_row else 0

        if count == 0:
            return {"table": "self_observations", "archived": 0, "message": "アーカイブ対象なし"}

        # タイプ別集計をdetailに保存
        type_counts = await self.db.fetch(
            "SELECT obs_type, COUNT(*) as cnt FROM self_observations "
            "WHERE created_at < $1 GROUP BY obs_type", cutoff
        )
        import json
        detail = {r["obs_type"]: r["cnt"] for r in type_counts}

        await self.db.execute(
            "INSERT INTO memory_archive (source_table, period_start, period_end, record_count, summary, detail) "
            "VALUES ($1, (SELECT MIN(created_at)::date FROM self_observations WHERE created_at < $2), "
            "$2::date, $3, $4, $5::jsonb)",
            "self_observations", cutoff, count,
            f"自己観察 {count}件をアーカイブ",
            json.dumps(detail),
        )

        await self.db.execute(
            "DELETE FROM self_observations WHERE created_at < $1", cutoff
        )

        logger.info(f"Archived {count} observations")
        return {"table": "self_observations", "archived": count, "by_type": detail}

    async def run_full_archive(self) -> dict:
        """全テーブルのアーカイブを実行"""
        results = {
            "conversations": await self.archive_conversations(),
            "emotions": await self.archive_emotions(),
            "observations": await self.archive_observations(),
        }
        total = sum(r.get("archived", 0) for r in results.values())
        results["total_archived"] = total
        results["status"] = "completed"
        logger.info(f"Full archive completed: {total} records archived")
        return results

    async def get_archive_history(self, limit: int = 20) -> list[dict]:
        """アーカイブ履歴"""
        await self._ensure_archive_table()
        rows = await self.db.fetch(
            "SELECT * FROM memory_archive ORDER BY created_at DESC LIMIT $1", limit
        )
        return [
            {
                "id": str(r["id"]),
                "source_table": r["source_table"],
                "period": f"{r['period_start']} — {r['period_end']}",
                "record_count": r["record_count"],
                "summary": r["summary"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]
