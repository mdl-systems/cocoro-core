"""cocoro-core — Identity Engine
人格の核。「私は誰か」を定義する。
"""
import logging

logger = logging.getLogger("cocoro.identity")


class IdentityEngine:
    """人格のアイデンティティ管理"""

    def __init__(self, db):
        self.db = db
        # NOTE: キャッシュなし — 常にDBから最新を読む
        # （boot_wizard更新後に古いデータが残る問題を防ぐ）

    async def get(self) -> dict:
        """現在のアイデンティティを取得（常にDBから最新を読む）"""
        row = await self.db.fetchrow("SELECT * FROM identity LIMIT 1")
        return dict(row) if row else {"owner_name": "Unknown", "profile": "", "philosophy": ""}

    async def update(self, **kwargs) -> dict:
        """アイデンティティを更新"""
        identity = await self.get()
        sets, params, i = [], [], 1
        for key in ("owner_name", "profile", "philosophy"):
            if key in kwargs and kwargs[key] is not None:
                sets.append(f"{key}=${i}")
                params.append(kwargs[key])
                i += 1
        if sets:
            params.append(identity.get("id"))
            await self.db.execute(
                f"UPDATE identity SET {','.join(sets)} WHERE id=${i}::uuid", *params
            )
            logger.info(f"Identity updated: {list(kwargs.keys())}")
        return await self.get()

    async def to_prompt(self) -> str:
        """アイデンティティをプロンプト文に変換"""
        i = await self.get()
        return f"""【アイデンティティ】
名前: {i.get('owner_name', '')}
プロフィール: {i.get('profile', '')}
理念: {i.get('philosophy', '')}"""
