"""cocoro-core — Vector Memory (pgvector + pg_trgm)
セマンティック検索による知識検索。
embedding がある場合はpgvectorのコサイン類似で検索、
ない場合は pg_trgm のトライグラム類似検索にフォールバック。
"""
import json
import logging

logger = logging.getLogger("cocoro.memory.vector")


class VectorMemory:
    def __init__(self, db):
        self.db = db

    async def store(self, content: str, category: str = "general", source: str = "manual",
                    metadata: str = "{}", embedding: list = None) -> str:
        """知識を保存（embedding付き可）"""
        if embedding:
            row = await self.db.fetchrow(
                "INSERT INTO knowledge_store (content, embedding, category, source, metadata) "
                "VALUES ($1, $2::vector, $3, $4, $5) RETURNING id",
                content, str(embedding), category, source, metadata,
            )
        else:
            row = await self.db.fetchrow(
                "INSERT INTO knowledge_store (content, category, source, metadata) "
                "VALUES ($1,$2,$3,$4) RETURNING id", content, category, source, metadata,
            )
        logger.info(f"Knowledge stored: {content[:50]}...")
        return str(row["id"])

    async def search(self, query: str, limit: int = 5, embedding: list = None) -> list[dict]:
        """セマンティック検索（pgvector優先、pg_trgmフォールバック）"""
        if embedding:
            # pgvector コサイン類似検索
            rows = await self.db.fetch(
                "SELECT id, content, category, source, metadata, created_at, "
                "1 - (embedding <=> $1::vector) AS score "
                "FROM knowledge_store WHERE embedding IS NOT NULL "
                "ORDER BY embedding <=> $1::vector LIMIT $2",
                str(embedding), limit,
            )
            if rows:
                return [dict(r) for r in rows]

        # フォールバック: pg_trgm 類似テキスト検索
        rows = await self.db.fetch(
            "SELECT *, similarity(content, $1) AS score FROM knowledge_store "
            "WHERE content % $1 ORDER BY score DESC LIMIT $2", query, limit,
        )
        return [dict(r) for r in rows]

    async def search_by_category(self, query: str, category: str, limit: int = 5) -> list[dict]:
        rows = await self.db.fetch(
            "SELECT *, similarity(content, $1) AS score FROM knowledge_store "
            "WHERE category=$2 AND content % $1 ORDER BY score DESC LIMIT $3",
            query, category, limit,
        )
        return [dict(r) for r in rows]

    async def get_all(self, category: str = None, limit: int = 50) -> list[dict]:
        if category:
            rows = await self.db.fetch(
                "SELECT * FROM knowledge_store WHERE category=$1 ORDER BY created_at DESC LIMIT $2",
                category, limit)
        else:
            rows = await self.db.fetch(
                "SELECT * FROM knowledge_store ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]
