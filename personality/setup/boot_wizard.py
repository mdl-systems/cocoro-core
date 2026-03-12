"""cocoro-core — Boot Wizard / Interview Engine
人格形成の初回セットアップ + 深層インタビュー。

v2仕様: Boot Wizard (40-60問, 5カテゴリ)
v2.5仕様: Phase1 Interview (80-120問, 8カテゴリ)

セッションベースの質問応答 → LLM心理分析 → 人格パラメータ生成。
"""
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.setup")

JST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────
# 質問データベース — 8カテゴリ
# mode="boot" → 各カテゴリ5問 (計40問)
# mode="deep" → 全問 (計80問)
# ──────────────────────────────────────────────
QUESTIONS = {
    "identity": {
        "label": "アイデンティティ",
        "questions": [
            {"id": "id_01", "text": "あなたはどんな人ですか？職業や専門分野を教えてください。", "type": "open"},
            {"id": "id_02", "text": "あなたの最大の強みは何ですか？", "type": "open"},
            {"id": "id_03", "text": "人生の目的は何だと考えていますか？", "type": "open"},
            {"id": "id_04", "text": "あなたを一言で表すとしたら？", "type": "open"},
            {"id": "id_05", "text": "5年後、どんな自分になっていたいですか？", "type": "open"},
            {"id": "id_06", "text": "あなたが最も誇りに思う実績は何ですか？", "type": "open"},
            {"id": "id_07", "text": "他人からどのような人だと言われますか？", "type": "open"},
            {"id": "id_08", "text": "仕事とプライベート、どちらを優先しますか？", "type": "choice",
             "options": ["仕事優先", "バランス重視", "プライベート優先"]},
            {"id": "id_09", "text": "リーダーとフォロワー、どちらが自然ですか？", "type": "choice",
             "options": ["リーダー", "状況による", "フォロワー"]},
            {"id": "id_10", "text": "あなたの人生のモットーは？", "type": "open"},
        ]
    },
    "values": {
        "label": "価値観",
        "questions": [
            {"id": "val_01", "text": "次の価値観を重要度順に並べてください: 誠実さ, 効率, 成長, 自由, 安定, 挑戦, 影響力",
             "type": "ranking", "items": ["誠実さ", "効率", "成長", "自由", "安定", "挑戦", "影響力"]},
            {"id": "val_02", "text": "お金と時間、どちらが大切ですか？", "type": "choice",
             "options": ["お金", "どちらも同じ", "時間"]},
            {"id": "val_03", "text": "成功の定義は何ですか？", "type": "open"},
            {"id": "val_04", "text": "正しいことと効率的なこと、どちらを選びますか？", "type": "choice",
             "options": ["絶対に正しいこと", "状況による", "効率的なこと"]},
            {"id": "val_05", "text": "人間関係で最も大切にすることは？", "type": "open"},
            {"id": "val_06", "text": "完璧主義ですか？それとも80点主義ですか？", "type": "choice",
             "options": ["完璧主義", "ケースバイケース", "80点主義"]},
            {"id": "val_07", "text": "競争と協力、どちらが好きですか？", "type": "choice",
             "options": ["競争", "両方", "協力"]},
            {"id": "val_08", "text": "安全な道と未知の道、どちらを選びますか？", "type": "choice",
             "options": ["安全な道", "状況次第", "未知の道"]},
            {"id": "val_09", "text": "仕事を選ぶとき最も重視するのは？", "type": "choice",
             "options": ["報酬", "やりがい", "成長機会", "安定性", "社会貢献"]},
            {"id": "val_10", "text": "あなたにとって「幸せ」とは？", "type": "open"},
        ]
    },
    "beliefs": {
        "label": "信念",
        "questions": [
            {"id": "bel_01", "text": "「失敗は避けるべき」vs「失敗は学習機会」どちらに近いですか？",
             "type": "scale", "left": "避けるべき", "right": "学習機会"},
            {"id": "bel_02", "text": "「人は基本的に信頼できる」vs「人は信頼を証明すべき」",
             "type": "scale", "left": "基本的に信頼", "right": "証明すべき"},
            {"id": "bel_03", "text": "「努力は必ず報われる」と思いますか？", "type": "scale",
             "left": "必ず報われる", "right": "報われないこともある"},
            {"id": "bel_04", "text": "「ルールは守るべき」vs「ルールは変えるべき」",
             "type": "scale", "left": "守るべき", "right": "変えるべき"},
            {"id": "bel_05", "text": "運命は決まっていると思いますか？自分で作れると思いますか？",
             "type": "scale", "left": "決まっている", "right": "自分で作れる"},
            {"id": "bel_06", "text": "「正解は一つ」vs「正解は複数ある」",
             "type": "scale", "left": "一つ", "right": "複数ある"},
            {"id": "bel_07", "text": "最も信頼する情報源は？", "type": "choice",
             "options": ["自分の経験", "データ・統計", "専門家の意見", "直感"]},
            {"id": "bel_08", "text": "「変化は好機」vs「変化はリスク」",
             "type": "scale", "left": "リスク", "right": "好機"},
            {"id": "bel_09", "text": "組織の中で最も重要なのは？", "type": "choice",
             "options": ["リーダーの資質", "チームワーク", "制度・仕組み", "個人の能力"]},
            {"id": "bel_10", "text": "あなたが絶対に譲れない信念は何ですか？", "type": "open"},
        ]
    },
    "decision_style": {
        "label": "意思決定スタイル",
        "questions": [
            {"id": "dec_01", "text": "意思決定で最も頼りにするのは？", "type": "choice",
             "options": ["データ・分析", "直感・経験", "専門家の意見", "チームの合意"]},
            {"id": "dec_02", "text": "重要な決断をするとき、どのくらい時間をかけますか？", "type": "choice",
             "options": ["即断即決", "数時間〜1日", "数日〜1週間", "じっくり考える"]},
            {"id": "dec_03", "text": "判断を間違えたとき、どう対応しますか？", "type": "open"},
            {"id": "dec_04", "text": "情報が不足していても決断しますか？", "type": "choice",
             "options": ["すぐに決断する", "最低限の情報で決断", "十分な情報を集めてから"]},
            {"id": "dec_05", "text": "過去の最も難しかった決断は何ですか？", "type": "open"},
            {"id": "dec_06", "text": "他人の意見にどの程度影響されますか？", "type": "scale",
             "left": "全く影響されない", "right": "大きく影響される"},
            {"id": "dec_07", "text": "「石橋を叩いて渡る」vs「まずやってみる」",
             "type": "scale", "left": "石橋を叩く", "right": "まずやってみる"},
            {"id": "dec_08", "text": "大きなリスクのある挑戦をしますか？", "type": "choice",
             "options": ["積極的にする", "リスクを評価してから", "避ける"]},
            {"id": "dec_09", "text": "合理性と感情、どちらを優先しますか？", "type": "choice",
             "options": ["合理性", "バランス", "感情"]},
            {"id": "dec_10", "text": "決断後に後悔することが多いですか？", "type": "choice",
             "options": ["ほとんどない", "たまにある", "よくある"]},
        ]
    },
    "risk_profile": {
        "label": "リスクプロファイル",
        "questions": [
            {"id": "risk_01", "text": "投資でどちらを選びますか？ A: 確実に年5%利益 B: 30%の確率で年50%利益",
             "type": "choice", "options": ["A: 確実な5%", "B: 30%で50%"]},
            {"id": "risk_02", "text": "新しいビジネスチャンスがあります。成功確率40%、利益1億、損失2000万。投資しますか？",
             "type": "choice", "options": ["投資する", "もっと情報を集める", "投資しない"]},
            {"id": "risk_03", "text": "安定した会社員と不安定だが大きな可能性のある起業、どちらを選びますか？",
             "type": "choice", "options": ["会社員", "状況による", "起業"]},
            {"id": "risk_04", "text": "全財産の何%まで一つの投資に入れられますか？", "type": "choice",
             "options": ["10%以下", "10-30%", "30-50%", "50%以上"]},
            {"id": "risk_05", "text": "締め切りが迫っているとき、品質と速度どちらを重視しますか？", "type": "choice",
             "options": ["品質", "バランスを取る", "速度"]},
        ]
    },
    "emotional_profile": {
        "label": "感情プロファイル",
        "questions": [
            {"id": "emo_01", "text": "ストレスを感じたとき、どう対処しますか？", "type": "open"},
            {"id": "emo_02", "text": "怒りを感じたとき、どう行動しますか？", "type": "choice",
             "options": ["冷静に対処", "少し時間を置く", "すぐに表現する"]},
            {"id": "emo_03", "text": "嬉しいとき、どう表現しますか？", "type": "choice",
             "options": ["静かに喜ぶ", "人に伝える", "大きく表現する"]},
            {"id": "emo_04", "text": "批判されたとき、どう反応しますか？", "type": "open"},
            {"id": "emo_05", "text": "感情的になりやすいですか？冷静ですか？", "type": "scale",
             "left": "非常に冷静", "right": "感情的になりやすい"},
        ]
    },
    "cognitive_style": {
        "label": "思考スタイル",
        "questions": [
            {"id": "cog_01", "text": "問題に直面したとき、最初に何をしますか？", "type": "choice",
             "options": ["情報を集める", "全体像を把握する", "直感で動く", "人に相談する"]},
            {"id": "cog_02", "text": "大局的思考と細部への注目、どちらが得意ですか？", "type": "choice",
             "options": ["大局的", "両方", "細部"]},
            {"id": "cog_03", "text": "新しいアイデアをどうやって生み出しますか？", "type": "open"},
            {"id": "cog_04", "text": "論理的思考と創造的思考、どちらが強いですか？", "type": "scale",
             "left": "論理的", "right": "創造的"},
            {"id": "cog_05", "text": "学ぶとき、どの方法が一番効率的ですか？", "type": "choice",
             "options": ["本・文書を読む", "実際にやってみる", "動画・講義", "人から教わる"]},
        ]
    },
    "life_narrative": {
        "label": "人生のストーリー",
        "questions": [
            {"id": "life_01", "text": "人生で最も重要だった出来事は何ですか？", "type": "open"},
            {"id": "life_02", "text": "最大の失敗経験は何ですか？そこから何を学びましたか？", "type": "open"},
            {"id": "life_03", "text": "最も誇りに思う成功体験は？", "type": "open"},
            {"id": "life_04", "text": "人生の転機となった瞬間はありますか？", "type": "open"},
            {"id": "life_05", "text": "あなたの人生に最も影響を与えた人物は誰ですか？", "type": "open"},
        ]
    }
}

# ──────────────────────────────────────────────
# LLMプロンプト: 心理分析
# ──────────────────────────────────────────────
ANALYSIS_PROMPT = """以下はユーザーの人格インタビュー回答です。
心理学的に分析し、JSON形式で人格パラメータを出力してください。

回答:
{answers_text}

以下のJSON形式で出力してください。数値は0.0〜1.0です:
```json
{{
  "identity": {{
    "profile_summary": "一行の人物像",
    "strengths": ["強み1", "強み2", "強み3"],
    "philosophy": "人生哲学"
  }},
  "values": {{
    "honesty": 0.0-1.0,
    "efficiency": 0.0-1.0,
    "growth": 0.0-1.0,
    "empathy": 0.0-1.0,
    "logic": 0.0-1.0,
    "courage": 0.0-1.0,
    "risk_tolerance": 0.0-1.0,
    "curiosity": 0.0-1.0
  }},
  "beliefs": [
    {{"statement": "信念1", "confidence": 0.0-1.0}},
    {{"statement": "信念2", "confidence": 0.0-1.0}},
    {{"statement": "信念3", "confidence": 0.0-1.0}}
  ],
  "decision_style": "data-driven | intuitive | collaborative | cautious",
  "risk_profile": 0.0-1.0,
  "cognitive_style": "analytical | creative | balanced | practical",
  "goals": [
    {{"title": "目標1", "type": "life_mission|long_term|short_term"}},
    {{"title": "目標2", "type": "life_mission|long_term|short_term"}}
  ]
}}
```"""


class SetupSession:
    """セットアップセッション — 質問状態を管理"""

    def __init__(self, session_id: str, mode: str = "boot"):
        self.session_id = session_id
        self.mode = mode  # "boot" (40問) or "deep" (80問)
        self.answers: dict[str, str] = {}
        self.created_at = datetime.now(JST)

        # モードに応じて質問を選択
        self.question_list = []
        per_category = 5 if mode == "boot" else 10
        for cat_key, cat_data in QUESTIONS.items():
            for q in cat_data["questions"][:per_category]:
                self.question_list.append({**q, "category": cat_key,
                                           "category_label": cat_data["label"]})

        self.current_index = 0

    @property
    def total_questions(self) -> int:
        return len(self.question_list)

    @property
    def progress(self) -> float:
        return (self.current_index / self.total_questions * 100) if self.total_questions > 0 else 0

    @property
    def is_complete(self) -> bool:
        return self.current_index >= self.total_questions

    def current_question(self) -> dict | None:
        if self.is_complete:
            return None
        q = self.question_list[self.current_index]
        return {
            "index": self.current_index + 1,
            "total": self.total_questions,
            "progress": round(self.progress, 1),
            **q,
        }

    def answer(self, answer_text: str, question_id: str | None = None) -> dict | None:
        if self.is_complete and question_id is None:
            return None
        # question_id 指定時はそのインデックスにジャンプ（戻る操作対応）
        if question_id is not None:
            target_index = next(
                (i for i, q in enumerate(self.question_list) if q["id"] == question_id),
                None
            )
            if target_index is not None:
                self.current_index = target_index
        if self.current_index >= len(self.question_list):
            return None
        q = self.question_list[self.current_index]
        self.answers[q["id"]] = answer_text
        self.current_index += 1
        return self.current_question()


class BootWizard:
    """人格形成ウィザード — セッション管理 + LLM分析"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm
        self.sessions: dict[str, SetupSession] = {}

    def start_session(self, mode: str = "boot") -> dict:
        """新しいセットアップセッションを開始"""
        session_id = str(uuid.uuid4())
        session = SetupSession(session_id, mode)
        self.sessions[session_id] = session
        logger.info(f"Setup session started: {session_id[:8]} mode={mode} "
                     f"questions={session.total_questions}")
        return {
            "session_id": session_id,
            "mode": mode,
            "total_questions": session.total_questions,
            "question": session.current_question(),
        }

    def answer(self, session_id: str, answer_text: str, question_id: str | None = None) -> dict:
        """質問に回答し、次の質問を取得（question_id 指定で任意の問にジャンプ可能）"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        next_q = session.answer(answer_text, question_id)
        result = {
            "session_id": session_id,
            "answered": len(session.answers),
            "total": session.total_questions,
            "progress": round(session.progress, 1),
            "is_complete": session.is_complete,
        }
        if next_q:
            result["question"] = next_q
        else:
            result["message"] = "全ての質問に回答しました。/setup/result で結果を取得できます。"
        return result

    def get_progress(self, session_id: str) -> dict:
        """進捗を確認"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        return {
            "session_id": session_id,
            "mode": session.mode,
            "answered": len(session.answers),
            "total": session.total_questions,
            "progress": round(session.progress, 1),
            "is_complete": session.is_complete,
            "current_question": session.current_question(),
        }

    async def get_result(self, session_id: str) -> dict:
        """回答をLLMで分析し、人格パラメータを生成"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        if not session.is_complete:
            return {"error": "Interview not complete",
                    "progress": round(session.progress, 1)}

        # 回答をテキストにまとめる
        answers_text = self._format_answers(session)

        # LLM分析
        analysis = None
        if self.llm:
            try:
                prompt = ANALYSIS_PROMPT.format(answers_text=answers_text)
                raw = await self.llm.generate(prompt)
                analysis = self._parse_analysis(raw)
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")

        # 分析結果がない場合はデフォルト
        if not analysis:
            analysis = self._default_analysis()

        # DBに反映
        applied = await self._apply_to_personality(analysis)

        # セッション終了
        del self.sessions[session_id]

        return {
            "session_id": session_id,
            "mode": session.mode,
            "total_answered": len(session.answers),
            "analysis": analysis,
            "applied": applied,
        }

    def _format_answers(self, session: SetupSession) -> str:
        """回答をテキスト形式に整形"""
        lines = []
        for q in session.question_list:
            answer = session.answers.get(q["id"], "（未回答）")
            lines.append(f"Q[{q['category_label']}]: {q['text']}")
            lines.append(f"A: {answer}")
            lines.append("")
        return "\n".join(lines)

    def _parse_analysis(self, raw: str) -> dict | None:
        """LLM出力をJSONパース"""
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _default_analysis(self) -> dict:
        """LLM分析失敗時のデフォルト値"""
        return {
            "identity": {"profile_summary": "分析中", "strengths": [], "philosophy": ""},
            "values": {
                "honesty": 0.8, "efficiency": 0.7, "growth": 0.8,
                "empathy": 0.6, "logic": 0.8, "courage": 0.5,
                "risk_tolerance": 0.5, "curiosity": 0.7,
            },
            "beliefs": [],
            "decision_style": "balanced",
            "risk_profile": 0.5,
            "cognitive_style": "balanced",
            "goals": [],
        }

    async def _apply_to_personality(self, analysis: dict) -> dict:
        """分析結果をDBに反映"""
        applied = {"identity": False, "values": False, "beliefs": False, "goals": False}
        try:
            # Identity 更新
            identity = analysis.get("identity", {})
            if identity.get("profile_summary") or identity.get("philosophy"):
                await self.db.execute(
                    "UPDATE identity SET profile=$1, philosophy=$2 "
                    "WHERE id=(SELECT id FROM identity LIMIT 1)",
                    identity.get("profile_summary", ""),
                    identity.get("philosophy", ""))
                applied["identity"] = True

            # Values 更新
            values = analysis.get("values", {})
            for name, weight in values.items():
                if isinstance(weight, (int, float)):
                    await self.db.execute(
                        "UPDATE values_system SET weight=$1 WHERE name=$2",
                        float(weight), name)
            if values:
                applied["values"] = True

            # Beliefs 追加
            beliefs = analysis.get("beliefs", [])
            for b in beliefs:
                if isinstance(b, dict) and b.get("statement"):
                    await self.db.execute(
                        "INSERT INTO beliefs (statement, confidence, source) "
                        "VALUES ($1, $2, 'interview') ON CONFLICT DO NOTHING",
                        b["statement"], b.get("confidence", 0.7))
            if beliefs:
                applied["beliefs"] = True

            # Goals 追加
            goals = analysis.get("goals", [])
            type_map = {"life_mission": "life_mission", "long_term": "long_term",
                        "short_term": "short_term"}
            for g in goals:
                if isinstance(g, dict) and g.get("title"):
                    goal_type = type_map.get(g.get("type", ""), "short_term")
                    await self.db.execute(
                        "INSERT INTO goals (title, goal_type, priority) VALUES ($1, $2, 7)",
                        g["title"], goal_type)
            if goals:
                applied["goals"] = True

            logger.info(f"Setup applied to personality: {applied}")
        except Exception as e:
            logger.error(f"Failed to apply personality: {e}")

        return applied
