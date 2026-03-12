"""cocoro-core — User Memory Engine
会話から自動的にユーザー情報を抽出・記憶するエンジン。

knowledge_base テーブルを活用:
  - type (category): preference / event / person / place / emotion_note / general
  - source: 'user_memory'
  - confidence: 0.0-1.0

auto_extract() が会話テキストを解析し、重要な情報を自動保存する。
"""
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger("cocoro.memory.user")

# 記憶タイプの日本語ラベル
MEMORY_TYPE_LABELS = {
    "preference": "好み・興味",
    "event":      "出来事・予定",
    "person":     "人物関係",
    "place":      "場所",
    "emotion_note": "感情メモ",
    "general":    "一般情報",
}

# 自動抽出ルール: (パターンリスト, タイプ, 信頼度)
# ユーザー発言から検出する
EXTRACT_RULES: list[tuple[list[str], str, float]] = [
    # 好み・興味
    (["好き", "大好き", "気に入", "お気に入り", "趣味", "興味", "はまってる", "ハマってる"], "preference", 0.85),
    (["嫌い", "苦手", "嫌だ", "嫌いな", "嫌いです"], "preference", 0.80),
    (["いつも", "よく", "毎日", "定期的に", "習慣"], "preference", 0.70),
    # 出来事・予定
    (["予定", "スケジュール", "明日", "来週", "今週末", "今度", "次は"], "event", 0.75),
    (["行く", "行った", "やる", "やった", "参加", "開催"], "event", 0.70),
    (["仕事", "会議", "打ち合わせ", "出張", "休暇", "旅行"], "event", 0.75),
    # 人物
    (["友達", "友人", "彼女", "彼氏", "パートナー", "家族", "親", "兄", "姉", "弟", "妹"], "person", 0.80),
    (["同僚", "上司", "部下", "チームメンバー", "先生", "生徒"], "person", 0.75),
    # 場所
    (["住んでる", "住んでいる", "在住", "地元", "実家", "会社", "職場", "学校"], "place", 0.80),
    (["に住", "から来た", "出身"], "place", 0.85),
    # 感情メモ
    (["嬉しい", "楽しかった", "悲しい", "つらかった", "怒った", "感動した"], "emotion_note", 0.65),
    (["最近", "ストレス", "悩んでいる", "困っている", "心配", "不安"], "emotion_note", 0.70),
]

# 文脈が「ユーザー自身の話」かを示すキーワード（AIの応答は除外）
USER_CONTEXT_MARKERS = ["私", "僕", "俺", "私は", "僕は", "俺は", "自分", "うち", "うちは"]


def _is_about_user(text: str) -> bool:
    """テキストがユーザー自身についての発言か判定"""
    return any(marker in text for marker in USER_CONTEXT_MARKERS)


def _extract_relevant_sentences(text: str, keywords: list[str]) -> list[str]:
    """キーワードを含む文を抽出"""
    sentences = re.split(r"[。！？\n]", text)
    relevant = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 5:
            continue
        if any(kw in sent for kw in keywords):
            relevant.append(sent)
    return relevant


class UserMemoryEngine:
    """ユーザー情報を自動学習するエンジン"""

    def __init__(self, db):
        self.db = db

    # ===========================
    # CRUD Operations
    # ===========================

    async def add(self, topic: str, content: str, memory_type: str = "general",
                  confidence: float = 0.8) -> str:
        """記憶を手動追加（または自動抽出結果を保存）"""
        # 同じトピック・内容の重複を防ぐ
        existing = await self.db.fetchrow(
            "SELECT id FROM knowledge_base WHERE topic=$1 AND content=$2 AND source='user_memory'",
            topic, content
        )
        if existing:
            # 信頼度を更新
            await self.db.execute(
                "UPDATE knowledge_base SET confidence=GREATEST(confidence, $1), "
                "updated_at=NOW() WHERE id=$2",
                confidence, existing["id"]
            )
            return str(existing["id"])

        row = await self.db.fetchrow(
            "INSERT INTO knowledge_base (topic, content, source, category, confidence) "
            "VALUES ($1, $2, 'user_memory', $3, $4) RETURNING id",
            topic, content, memory_type, confidence
        )
        logger.info(f"UserMemory saved: [{memory_type}] {topic[:30]}")
        return str(row["id"])

    async def list_all(self, memory_type: str = None, limit: int = 50) -> list[dict]:
        """記憶一覧を取得"""
        if memory_type:
            rows = await self.db.fetch(
                "SELECT id, topic, content, category, confidence, created_at "
                "FROM knowledge_base WHERE source='user_memory' AND category=$1 "
                "ORDER BY confidence DESC, created_at DESC LIMIT $2",
                memory_type, limit
            )
        else:
            rows = await self.db.fetch(
                "SELECT id, topic, content, category, confidence, created_at "
                "FROM knowledge_base WHERE source='user_memory' "
                "ORDER BY confidence DESC, created_at DESC LIMIT $1",
                limit
            )
        return [
            {
                "id": str(r["id"]),
                "type": r["category"],
                "type_label": MEMORY_TYPE_LABELS.get(r["category"], r["category"]),
                "topic": r["topic"],
                "content": r["content"],
                "confidence": round(float(r["confidence"]), 2),
                "created_at": str(r["created_at"])[:10],
            }
            for r in rows
        ]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """キーワードで記憶を検索"""
        rows = await self.db.fetch(
            "SELECT id, topic, content, category, confidence, created_at "
            "FROM knowledge_base "
            "WHERE source='user_memory' AND (topic ILIKE $1 OR content ILIKE $1) "
            "ORDER BY confidence DESC, created_at DESC LIMIT $2",
            f"%{query}%", limit
        )
        return [
            {
                "id": str(r["id"]),
                "type": r["category"],
                "type_label": MEMORY_TYPE_LABELS.get(r["category"], r["category"]),
                "topic": r["topic"],
                "content": r["content"],
                "confidence": round(float(r["confidence"]), 2),
                "created_at": str(r["created_at"])[:10],
            }
            for r in rows
        ]

    async def delete(self, memory_id: str) -> bool:
        """特定の記憶を削除"""
        result = await self.db.execute(
            "DELETE FROM knowledge_base WHERE id=$1::uuid AND source='user_memory'",
            memory_id
        )
        deleted = result.split()[-1] != "0"
        if deleted:
            logger.info(f"UserMemory deleted: {memory_id}")
        return deleted

    async def get_high_confidence(self, limit: int = 10) -> list[dict]:
        """重要度の高い記憶を取得（system prompt 注入用）"""
        rows = await self.db.fetch(
            "SELECT topic, content, category FROM knowledge_base "
            "WHERE source='user_memory' AND confidence >= 0.75 "
            "ORDER BY confidence DESC, created_at DESC LIMIT $1",
            limit
        )
        return [dict(r) for r in rows]

    # ===========================
    # Auto-Extraction
    # ===========================

    async def auto_extract(self, user_message: str, ai_response: str = "") -> list[str]:
        """会話テキストからユーザー情報を自動抽出してDBに保存する。

        Args:
            user_message: ユーザーの発言
            ai_response: AIの応答（文脈補助）

        Returns:
            保存された記憶IDのリスト
        """
        saved_ids = []

        if not user_message or len(user_message) < 10:
            return saved_ids

        # ユーザー自身についての発言かチェック（最低限の文脈フィルタ）
        text = user_message

        for keywords, mem_type, confidence in EXTRACT_RULES:
            sentences = _extract_relevant_sentences(text, keywords)
            for sent in sentences:
                if len(sent) < 8 or len(sent) > 200:
                    continue

                # トピック名を生成（キーワードを含む最初の語）
                topic = self._make_topic(sent, mem_type)

                try:
                    mem_id = await self.add(
                        topic=topic,
                        content=sent,
                        memory_type=mem_type,
                        confidence=confidence,
                    )
                    saved_ids.append(mem_id)
                except Exception as e:
                    logger.warning(f"Failed to save memory: {e}")

        return saved_ids

    def _make_topic(self, sentence: str, mem_type: str) -> str:
        """文からトピック名を生成（先頭20文字）"""
        type_prefix = {
            "preference": "好み",
            "event":      "予定",
            "person":     "人物",
            "place":      "場所",
            "emotion_note": "感情",
            "general":    "情報",
        }.get(mem_type, "情報")

        # 先頭20文字を使い、重複が起きにくいトピック名にする
        short = sentence[:20].strip()
        return f"{type_prefix}: {short}"

    async def build_prompt_section(self) -> str:
        """重要な記憶を system prompt 用テキストに変換"""
        memories = await self.get_high_confidence(limit=8)
        if not memories:
            return ""

        lines = ["【ユーザーについて知っていること】"]
        for m in memories:
            label = MEMORY_TYPE_LABELS.get(m["category"], "")
            lines.append(f"  - [{label}] {m['content']}")
        return "\n".join(lines)
