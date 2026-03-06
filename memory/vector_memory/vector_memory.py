"""cocoro-core — Vector Memory (pg_trgm similarity search)
意味検索による知識検索。将来pgvector/ChromaDBに拡張可能。
"""
import logging

logger = logging.getLogger("cocoro.memory.vector")


class VectorMemory:
    def __init__(self, db):
        self.db = db

    async def store(self, content: str, category: str = "general", source: str = "manual",
                    metadata: str = "{}") -> str:
        row = await self.db.fetchrow(
            "INSERT INTO knowledge_store (content, category, source, metadata) "
            "VALUES ($1,$2,$3,$4) RETURNING id", content, category, source, metadata,
        )
        logger.info(f"Knowledge stored: {content[:50]}...")
        return str(row["id"])

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """pg_trgmによる類似テキスト検索"""
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
