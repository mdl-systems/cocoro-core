"""cocoro-core — Database Migration Tool
軽量なスキーマバージョン管理。init.sql からの差分マイグレーションを管理する。
"""
import os
import asyncio
import logging

logger = logging.getLogger("cocoro.migration")

# マイグレーション管理テーブル
MIGRATION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    applied_at  TIMESTAMPTZ DEFAULT NOW(),
    checksum    TEXT
);
"""

# マイグレーション定義（バージョン順に追加していく）
MIGRATIONS = [
    {
        "version": 1,
        "name": "initial_schema",
        "description": "init.sql の初期スキーマ（既存DBには適用済みとしてマーク）",
        "sql": None,  # init.sqlで作成済み
    },
    {
        "version": 2,
        "name": "add_emotion_indexes",
        "description": "感情関連テーブルにインデックス追加",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_emotion_history_created
                ON emotion_history (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_conv_session_created
                ON conversation_log (session_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_conv_emotion
                ON conversation_log (emotion) WHERE emotion IS NOT NULL AND emotion != 'neutral';
        """,
    },
    {
        "version": 3,
        "name": "add_decision_log_indexes",
        "description": "判断ログのカテゴリ・日時インデックス",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_decision_log_category
                ON decision_log (category, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_thought_log_created
                ON thought_log (created_at DESC);
        """,
    },
    {
        "version": 4,
        "name": "add_self_observation_indexes",
        "description": "自己観察のタイプ・日時インデックス",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_self_observations_type_created
                ON self_observations (obs_type, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_self_observations_impact
                ON self_observations (impact_score DESC);
        """,
    },
    {
        "version": 5,
        "name": "add_cocoro_nodes_table",
        "description": "複数miniPC対応: ノード登録・発見テーブル",
        "sql": """
            CREATE TABLE IF NOT EXISTS cocoro_nodes (
                node_id       TEXT PRIMARY KEY,
                name          TEXT NOT NULL DEFAULT '',
                ip            TEXT NOT NULL,
                port          INTEGER NOT NULL DEFAULT 8001,
                roles         TEXT[] DEFAULT '{}',
                status        TEXT DEFAULT 'unknown',
                last_seen     TIMESTAMPTZ,
                registered_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at    TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_status
                ON cocoro_nodes (status);
        """,
    },
]


class MigrationRunner:
    """データベースマイグレーション実行エンジン"""

    def __init__(self, db):
        self.db = db

    async def init(self):
        """マイグレーション管理テーブルを作成"""
        await self.db.execute(MIGRATION_TABLE)
        logger.info("Migration table ready")

    async def get_current_version(self) -> int:
        """現在のスキーマバージョンを取得"""
        try:
            row = await self.db.fetchrow(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            return row["version"] if row and row["version"] else 0
        except Exception:
            return 0

    async def get_applied(self) -> list[dict]:
        """適用済みマイグレーション一覧"""
        rows = await self.db.fetch(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
        )
        return [dict(r) for r in rows]

    async def get_pending(self) -> list[dict]:
        """未適用マイグレーション一覧"""
        current = await self.get_current_version()
        return [m for m in MIGRATIONS if m["version"] > current]

    async def migrate(self, target_version: int | None = None) -> dict:
        """マイグレーションを実行"""
        await self.init()
        current = await self.get_current_version()

        # 新規DB: version 1 (init.sql) を適用済みとしてマーク
        if current == 0:
            await self.db.execute(
                "INSERT INTO schema_migrations (version, name) VALUES ($1, $2) "
                "ON CONFLICT (version) DO NOTHING",
                1, "initial_schema",
            )
            current = 1
            logger.info("Marked initial schema as applied (version 1)")

        pending = [m for m in MIGRATIONS if m["version"] > current]
        if target_version:
            pending = [m for m in pending if m["version"] <= target_version]

        if not pending:
            return {
                "status": "up_to_date",
                "current_version": current,
                "message": "スキーマは最新です",
            }

        applied = []
        for migration in pending:
            try:
                if migration["sql"]:
                    await self.db.execute(migration["sql"])
                await self.db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                    migration["version"], migration["name"],
                )
                applied.append(migration["name"])
                logger.info(f"Migration applied: v{migration['version']} - {migration['name']}")
            except Exception as e:
                logger.error(f"Migration failed at v{migration['version']}: {e}")
                return {
                    "status": "error",
                    "current_version": await self.get_current_version(),
                    "failed_at": migration["version"],
                    "error": str(e),
                    "applied": applied,
                }

        new_version = await self.get_current_version()
        return {
            "status": "migrated",
            "previous_version": current,
            "current_version": new_version,
            "applied": applied,
        }

    async def get_status(self) -> dict:
        """マイグレーション状態を取得"""
        await self.init()
        current = await self.get_current_version()
        pending = await self.get_pending()
        applied = await self.get_applied()

        return {
            "current_version": current,
            "latest_version": MIGRATIONS[-1]["version"] if MIGRATIONS else 0,
            "pending_count": len(pending),
            "pending": [{"version": m["version"], "name": m["name"]} for m in pending],
            "applied": [
                {"version": a["version"], "name": a["name"],
                 "applied_at": str(a["applied_at"]) if a.get("applied_at") else None}
                for a in applied
            ],
        }
