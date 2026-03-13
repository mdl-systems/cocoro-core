"""cocoro-core — Autonomous Thinker
会話のない時間帯にAIが自律的に思考・振り返りを行うエンジン。

機能:
  - 直近の会話を振り返り洞察を生成
  - 未解決の課題と感情状態を分析
  - 記憶から重要パターンを抽出
  - 翌日のブリーフィングを準備
  - thought_log テーブルに reflection タイプとして保存
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("cocoro.thinker")

# 自律思考のタイプ
THINKING_TYPE = "reflection"

# ブリーフィングを保存するテーブル列識別子
BRIEFING_PREFIX = "[DAILY_BRIEF]"


class AutonomousThinker:
    """自律思考エンジン — 会話のない時間に動作する内省システム"""

    def __init__(self, db_pool, llm, personality=None, memory=None):
        self.db = db_pool
        self.llm = llm
        self.personality = personality
        self.memory = memory
        self._running = False
        self._last_think_time: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # メインの思考セッション
    # ------------------------------------------------------------------ #

    async def run_thinking_session(self) -> dict:
        """自律思考セッションを実行してthought_logに保存。

        Returns:
            {"session_id": str, "insights": list, "summary": str}
        """
        logger.info("Autonomous thinking session started")
        now = datetime.now(timezone.utc)

        # 1. 直近24時間の会話を集める
        recent_convs = await self._fetch_recent_conversations(hours=24)

        # 2. 保存済みユーザー記憶を集める
        recent_memories = await self._fetch_recent_memories(limit=10)

        # 3. 感情状態を取得
        emotion_summary = await self._get_emotion_summary()

        # 4. LLM に自律思考を依頼
        thinking_prompt = self._build_thinking_prompt(
            recent_convs, recent_memories, emotion_summary, now
        )

        try:
            raw_thought = await self.llm.generate(
                thinking_prompt,
                system_prompt=self._thinking_system_prompt(),
            )
        except Exception as e:
            logger.warning(f"LLM thinking failed: {e}")
            raw_thought = "LLM生成に失敗しました。"

        # 5. 洞察を構造化
        insights = self._parse_insights(raw_thought)
        summary = raw_thought[:300] if raw_thought else "思考セッション完了"

        # 6. thought_log に保存
        session_id = await self._save_thought(
            input_summary=f"直近{len(recent_convs)}会話の振り返り",
            reasoning_chain=thinking_prompt[:500],
            conclusion=raw_thought[:1000],
            confidence=0.75,
        )

        self._last_think_time = now
        logger.info(f"Thinking session saved: {session_id}, {len(insights)} insights")

        return {
            "session_id": str(session_id),
            "insights": insights,
            "summary": summary,
            "conversation_count": len(recent_convs),
        }

    async def get_latest_insights(self, limit: int = 5) -> list:
        """最新の思考セッションから洞察一覧を返す。"""
        try:
            rows = await self.db.fetch(
                """SELECT conclusion, confidence, created_at
                   FROM thought_log
                   WHERE thought_type = $1
                   ORDER BY created_at DESC LIMIT $2""",
                THINKING_TYPE, limit
            )
            insights = []
            for row in rows:
                parsed = self._parse_insights(row["conclusion"] or "")
                for item in parsed:
                    item["recorded_at"] = row["created_at"].isoformat() if row["created_at"] else None
                    insights.append(item)
            return insights[:limit * 3]  # 各セッション最大3件
        except Exception as e:
            logger.error(f"Failed to fetch insights: {e}")
            return []

    # ------------------------------------------------------------------ #
    # デイリーブリーフィング
    # ------------------------------------------------------------------ #

    async def generate_daily_briefing(self) -> dict:
        """今日のデイリーブリーフィングを生成して保存。"""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        # 昨日の振り返りデータ
        yesterday_convs = await self._fetch_recent_conversations(hours=48)
        emotion_summary = await self._get_emotion_summary()
        recent_memories = await self._fetch_recent_memories(limit=5)

        brief_prompt = self._build_briefing_prompt(
            yesterday_convs, recent_memories, emotion_summary, now
        )

        try:
            brief_text = await self.llm.generate(
                brief_prompt,
                system_prompt=(
                    "あなたは誠実なAIアシスタントです。"
                    "ユーザーの一日を支えるブリーフィングを作成してください。"
                    "具体的で実用的な内容にしてください。"
                ),
            )
        except Exception as e:
            logger.warning(f"LLM briefing failed: {e}")
            brief_text = "デイリーブリーフィングの生成に失敗しました。"

        # thought_log に保存（BRIEFING_PREFIX でマーク）
        briefing_id = await self._save_thought(
            input_summary=f"{BRIEFING_PREFIX} {today_str}",
            reasoning_chain="デイリーブリーフィング生成",
            conclusion=brief_text[:2000],
            confidence=0.8,
        )

        logger.info(f"Daily briefing saved: {briefing_id}")
        return {
            "date": today_str,
            "briefing": brief_text,
            "briefing_id": str(briefing_id),
            "emotion_snapshot": emotion_summary,
        }

    async def get_daily_briefing(self, date: Optional[str] = None) -> Optional[dict]:
        """保存済みブリーフィングを返す。date省略時は最新。"""
        try:
            if date:
                row = await self.db.fetchrow(
                    """SELECT id, conclusion, confidence, created_at
                       FROM thought_log
                       WHERE thought_type = $1
                         AND input_summary LIKE $2
                       ORDER BY created_at DESC LIMIT 1""",
                    THINKING_TYPE, f"{BRIEFING_PREFIX} {date}%"
                )
            else:
                row = await self.db.fetchrow(
                    """SELECT id, conclusion, confidence, created_at
                       FROM thought_log
                       WHERE thought_type = $1
                         AND input_summary LIKE $2
                       ORDER BY created_at DESC LIMIT 1""",
                    THINKING_TYPE, f"{BRIEFING_PREFIX}%"
                )
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "briefing": row["conclusion"],
                "confidence": row["confidence"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        except Exception as e:
            logger.error(f"Failed to fetch briefing: {e}")
            return None

    # ------------------------------------------------------------------ #
    # 定期スケジューラ (asyncio ループ)
    # ------------------------------------------------------------------ #

    async def run_hourly_scheduler(self, interval_hours: int = 1):
        """1時間ごとに自律思考セッションを実行するスケジューラ。"""
        logger.info(f"AutoThinker scheduler: every {interval_hours}h")
        await asyncio.sleep(60 * 5)  # 起動5分後から開始
        while True:
            try:
                await self.run_thinking_session()
                logger.info("AutoThinker: scheduled session complete")
            except Exception as e:
                logger.error(f"AutoThinker scheduled error: {e}")

            # 毎日0時前後にブリーフィング生成
            now = datetime.now(timezone.utc)
            if now.hour == 0 and now.minute < 65:
                try:
                    await self.generate_daily_briefing()
                    logger.info("AutoThinker: daily briefing generated")
                except Exception as e:
                    logger.error(f"AutoThinker briefing error: {e}")

            await asyncio.sleep(interval_hours * 3600)

    # ------------------------------------------------------------------ #
    # 内部ヘルパー
    # ------------------------------------------------------------------ #

    async def _fetch_recent_conversations(self, hours: int = 24) -> list:
        """直近n時間の会話ログを取得。"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            rows = await self.db.fetch(
                """SELECT role, content, session_id, created_at
                   FROM conversation_log
                   WHERE created_at >= $1
                   ORDER BY created_at DESC LIMIT 50""",
                cutoff
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    async def _fetch_recent_memories(self, limit: int = 10) -> list:
        """ユーザー記憶（knowledge_base）から最新を取得。"""
        try:
            rows = await self.db.fetch(
                """SELECT topic, content, confidence
                   FROM knowledge_base
                   WHERE source = 'user_memory'
                   ORDER BY created_at DESC LIMIT $1""",
                limit
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    async def _get_emotion_summary(self) -> dict:
        """現在の感情状態サマリーを取得。"""
        try:
            if self.personality and hasattr(self.personality, "emotion"):
                state = await self.personality.emotion.get_current_state()
                return state if isinstance(state, dict) else {}
        except Exception:
            pass
        # フォールバック: DBから直接取得
        try:
            row = await self.db.fetchrow(
                """SELECT happiness, sadness, anger, fear, surprise, trust
                   FROM emotion_state LIMIT 1"""
            )
            if row:
                return dict(row)
        except Exception:
            pass
        return {}

    async def _save_thought(
        self,
        input_summary: str,
        reasoning_chain: str,
        conclusion: str,
        confidence: float = 0.7,
    ):
        """thought_log に reflection タイプで保存して ID を返す。"""
        try:
            row = await self.db.fetchrow(
                """INSERT INTO thought_log
                   (thought_type, input_summary, reasoning_chain, conclusion, confidence)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING id""",
                THINKING_TYPE,
                input_summary[:500],
                reasoning_chain[:1000],
                conclusion[:3000],
                confidence,
            )
            return row["id"] if row else None
        except Exception as e:
            logger.error(f"Failed to save thought: {e}")
            return None

    def _parse_insights(self, text: str) -> list:
        """思考テキストから洞察リストを抽出。"""
        insights = []
        lines = text.splitlines()

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            # 洞察タイプを推定
            if any(kw in line for kw in ["提案", "おすすめ", "試してみ", "やってみ"]):
                itype = "suggestion"
                confidence = 0.8
            elif any(kw in line for kw in ["気づ", "発見", "わかっ", "判明"]):
                itype = "observation"
                confidence = 0.75
            elif any(kw in line for kw in ["注意", "確認", "チェック", "問題"]):
                itype = "alert"
                confidence = 0.85
            elif any(kw in line for kw in ["振り返", "昨日", "最近", "これまで"]):
                itype = "reflection"
                confidence = 0.7
            else:
                itype = "note"
                confidence = 0.65

            # 箇条書き・番号付きリストの記号を除去
            content = line.lstrip("・•-*・1234567890.）) ")
            if len(content) > 15:
                insights.append({
                    "type": itype,
                    "content": content,
                    "confidence": confidence,
                })

        return insights[:10]  # 最大10件

    def _build_thinking_prompt(
        self,
        conversations: list,
        memories: list,
        emotion: dict,
        now: datetime,
    ) -> str:
        time_str = now.strftime("%Y/%m/%d %H:%M")
        conv_summary = "\n".join(
            f"  [{r.get('role','')}] {str(r.get('content',''))[:80]}"
            for r in conversations[:10]
        ) if conversations else "  （会話なし）"

        mem_summary = "\n".join(
            f"  - {m.get('topic','')}: {m.get('content','')[:60]}"
            for m in memories[:5]
        ) if memories else "  （記憶なし）"

        emo_str = (
            f"happiness={emotion.get('happiness',0):.1f}, "
            f"trust={emotion.get('trust',0):.1f}, "
            f"sadness={emotion.get('sadness',0):.1f}"
        ) if emotion else "不明"

        return f"""現在時刻: {time_str}

【直近の会話（抜粋）】
{conv_summary}

【ユーザーについての記憶】
{mem_summary}

【現在の感情状態】
{emo_str}

以上を踏まえて、以下を行ってください：
1. 直近の会話パターンと重要なテーマを振り返る
2. ユーザーへの具体的な提案を1〜3個挙げる
3. 自分（AI）として気づいたことを記録する
4. 未解決の課題があれば整理する

箇条書きで簡潔にまとめてください。"""

    def _build_briefing_prompt(
        self,
        conversations: list,
        memories: list,
        emotion: dict,
        now: datetime,
    ) -> str:
        date_str = now.strftime("%Y年%m月%d日")
        conv_count = len(conversations)
        topics = set()
        for c in conversations[:20]:
            content = str(c.get("content", ""))
            for kw in ["プログラム", "仕事", "勉強", "健康", "趣味", "料理", "旅行", "家族"]:
                if kw in content:
                    topics.add(kw)

        topic_str = "・".join(topics) if topics else "特定のテーマなし"

        return f"""{date_str}のデイリーブリーフィングを作成してください。

【昨日の会話数】{conv_count}件
【主なトピック】{topic_str}
【ユーザーの記憶から】{len(memories)}件の情報
【AI感情状態】happiness={emotion.get('happiness',0):.1f}

以下の形式でブリーフィングを作成：

## 昨日の振り返り
（主なやり取りと気づきを2〜3文で）

## 今日のおすすめアクション
1. （具体的な行動提案）
2. （具体的な行動提案）
3. （具体的な行動提案）

## 今日の一言
（ユーザーへの励ましや動機づけメッセージ）"""

    def _thinking_system_prompt(self) -> str:
        return (
            "あなたは人格AIとして自律的に思考する内省エンジンです。"
            "会話の外で静かに観察・学習・思索を行います。"
            "ユーザーをより深く理解し、より良いサポートができるよう"
            "客観的かつ共感的な視点で振り返りを行ってください。"
            "内容は実用的で具体的にしてください。"
        )
