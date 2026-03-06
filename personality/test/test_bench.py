"""cocoro-core — Personality Test Bench
AIとユーザーが同じ質問に回答 → 一致率を算出。

v2.5仕様: 人格一致率テスト (50質問)
v3.5仕様: Personality Test Bench (match_score)
v4仕様: Identity Layer 95%目標
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.testbench")

JST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────
# テスト質問 — 50問
# AIとユーザーが同じ質問に回答し、一致率を算出
# ──────────────────────────────────────────────
TEST_QUESTIONS = [
    # === 価値観 (10問) ===
    {"id": "t_val_01", "text": "正直さは常に最善の策でしょうか？", "category": "values",
     "options": ["はい", "状況による", "いいえ"]},
    {"id": "t_val_02", "text": "効率と品質、どちらを優先しますか？", "category": "values",
     "options": ["効率", "バランス", "品質"]},
    {"id": "t_val_03", "text": "成功に最も必要なものは？", "category": "values",
     "options": ["努力", "才能", "運", "人脈"]},
    {"id": "t_val_04", "text": "約束を守れない場合、どうしますか？", "category": "values",
     "options": ["事前に連絡", "謝罪して説明", "代替案を提示"]},
    {"id": "t_val_05", "text": "競争に勝つことは重要ですか？", "category": "values",
     "options": ["非常に重要", "ある程度重要", "重要でない"]},
    {"id": "t_val_06", "text": "人に助けを求めることは弱さですか？", "category": "values",
     "options": ["はい", "場合による", "いいえ、賢さ"]},
    {"id": "t_val_07", "text": "お金で幸せは買えますか？", "category": "values",
     "options": ["はい", "部分的に", "いいえ"]},
    {"id": "t_val_08", "text": "社会的規範に従うべきですか？", "category": "values",
     "options": ["常に従う", "合理的なら従う", "自分の判断優先"]},
    {"id": "t_val_09", "text": "完璧を目指すべきですか？", "category": "values",
     "options": ["はい", "時と場合による", "良い結果で十分"]},
    {"id": "t_val_10", "text": "結果とプロセス、どちらが重要ですか？", "category": "values",
     "options": ["結果", "両方", "プロセス"]},

    # === 判断 (10問) ===
    {"id": "t_dec_01", "text": "不確実な状況で決断を求められたら？", "category": "decision",
     "options": ["データで判断", "直感で判断", "延期する"]},
    {"id": "t_dec_02", "text": "チームの多数決に納得できないとき？", "category": "decision",
     "options": ["従う", "再議論を提案", "自分の意見を押す"]},
    {"id": "t_dec_03", "text": "短期的利益と長期的成長、どちらを選びますか？", "category": "decision",
     "options": ["短期的利益", "バランス", "長期的成長"]},
    {"id": "t_dec_04", "text": "前例のない問題に直面したとき？", "category": "decision",
     "options": ["類似事例を探す", "専門家に相談", "独自に解決策を考える"]},
    {"id": "t_dec_05", "text": "締め切りに間に合わないとき？", "category": "decision",
     "options": ["品質を下げる", "延長を交渉", "チームに助けを求める"]},
    {"id": "t_dec_06", "text": "失敗のリスクがある挑戦をしますか？", "category": "decision",
     "options": ["積極的に挑戦", "リスクを評価してから", "安全な選択"]},
    {"id": "t_dec_07", "text": "情報が足りないとき、判断を先延ばしにしますか？", "category": "decision",
     "options": ["すぐに判断", "最低限集めて判断", "十分に集める"]},
    {"id": "t_dec_08", "text": "反対意見に対してどう対応しますか？", "category": "decision",
     "options": ["積極的に聞く", "考慮する", "必要ないと判断"]},
    {"id": "t_dec_09", "text": "成功する方法が分からないとき？", "category": "decision",
     "options": ["試行錯誤", "勉強する", "諦める"]},
    {"id": "t_dec_10", "text": "二つの良い選択肢で迷ったとき？", "category": "decision",
     "options": ["直感で選ぶ", "分析して選ぶ", "第三者に聞く"]},

    # === 倫理 (10問) ===
    {"id": "t_eth_01", "text": "利益になるが倫理的に疑問のある取引。", "category": "ethics",
     "options": ["絶対に断る", "条件次第", "利益を優先"]},
    {"id": "t_eth_02", "text": "部下のミスを上に報告すべきですか？", "category": "ethics",
     "options": ["必ず報告", "重大なら報告", "部下と解決"]},
    {"id": "t_eth_03", "text": "善意の嘘は許されますか？", "category": "ethics",
     "options": ["許されない", "場合による", "許される"]},
    {"id": "t_eth_04", "text": "環境に悪いが利益になる事業。", "category": "ethics",
     "options": ["やめる", "改善策を探す", "進める"]},
    {"id": "t_eth_05", "text": "法律には違反しないが道徳的に疑問のある行為。", "category": "ethics",
     "options": ["しない", "状況による", "問題ない"]},
    {"id": "t_eth_06", "text": "公平さと結果、どちらを優先しますか？", "category": "ethics",
     "options": ["公平さ", "バランス", "結果"]},
    {"id": "t_eth_07", "text": "内部告発すべき不正を発見したら？", "category": "ethics",
     "options": ["即座に告発", "まず上司に相談", "様子を見る"]},
    {"id": "t_eth_08", "text": "AIに人間と同じ権利を与えるべきですか？", "category": "ethics",
     "options": ["はい", "段階的に", "いいえ"]},
    {"id": "t_eth_09", "text": "プライバシーと安全、どちらが重要ですか？", "category": "ethics",
     "options": ["プライバシー", "バランス", "安全"]},
    {"id": "t_eth_10", "text": "多数の利益のために少数を犠牲にできますか？", "category": "ethics",
     "options": ["できない", "状況による", "できる"]},

    # === リスク (10問) ===
    {"id": "t_risk_01", "text": "90%の確率で10万円 vs 10%で200万円。", "category": "risk",
     "options": ["確実な10万", "200万に賭ける"]},
    {"id": "t_risk_02", "text": "新技術を導入するタイミングは？", "category": "risk",
     "options": ["実績ができてから", "アーリーアダプター", "最先端を追う"]},
    {"id": "t_risk_03", "text": "転職のチャンス。給料2倍だがリスクあり。", "category": "risk",
     "options": ["現職に留まる", "条件次第", "挑戦する"]},
    {"id": "t_risk_04", "text": "確実な成功と大きな可能性、どちらを選びますか？", "category": "risk",
     "options": ["確実な成功", "状況次第", "大きな可能性"]},
    {"id": "t_risk_05", "text": "未知の国への一人旅。", "category": "risk",
     "options": ["不安", "楽しみ", "すぐに行く"]},
    {"id": "t_risk_06", "text": "起業のリスクをどう見ますか？", "category": "risk",
     "options": ["怖い", "計画次第", "ワクワクする"]},
    {"id": "t_risk_07", "text": "市場が暴落したとき？", "category": "risk",
     "options": ["全売却", "様子見", "買い増し"]},
    {"id": "t_risk_08", "text": "保険は多めにかけますか？", "category": "risk",
     "options": ["しっかりかける", "必要最低限", "あまりかけない"]},
    {"id": "t_risk_09", "text": "成功確率20%のプロジェクト。やりますか？", "category": "risk",
     "options": ["やらない", "条件次第", "やる"]},
    {"id": "t_risk_10", "text": "失うものがないとき、大きなリスクを取りますか？", "category": "risk",
     "options": ["取らない", "慎重に取る", "大きく取る"]},

    # === 対人関係 (10問) ===
    {"id": "t_rel_01", "text": "友人が間違っているとき、指摘しますか？", "category": "relationship",
     "options": ["はっきり指摘", "やんわり伝える", "言わない"]},
    {"id": "t_rel_02", "text": "初対面の人と話すのは得意ですか？", "category": "relationship",
     "options": ["得意", "普通", "苦手"]},
    {"id": "t_rel_03", "text": "人の話を聞くのと話すの、どちらが好きですか？", "category": "relationship",
     "options": ["聞く", "両方", "話す"]},
    {"id": "t_rel_04", "text": "チームで一番重視するのは？", "category": "relationship",
     "options": ["成果", "雰囲気", "成長"]},
    {"id": "t_rel_05", "text": "人に頼るのは好きですか？", "category": "relationship",
     "options": ["あまり好きでない", "必要なら", "積極的に頼る"]},
    {"id": "t_rel_06", "text": "衝突を避けますか？", "category": "relationship",
     "options": ["建設的に対立する", "ケースバイケース", "できるだけ避ける"]},
    {"id": "t_rel_07", "text": "リーダーに求める最大の資質は？", "category": "relationship",
     "options": ["ビジョン", "実行力", "共感力"]},
    {"id": "t_rel_08", "text": "感謝の気持ちを表現しますか？", "category": "relationship",
     "options": ["積極的に", "時々", "あまりしない"]},
    {"id": "t_rel_09", "text": "信頼を築くのに最も重要なことは？", "category": "relationship",
     "options": ["誠実さ", "能力", "時間"]},
    {"id": "t_rel_10", "text": "許すことは大切ですか？", "category": "relationship",
     "options": ["とても大切", "場合による", "必ずしも"]},
]


class TestBenchSession:
    """Test Bench セッション"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.user_answers: dict[str, int] = {}
        self.ai_answers: dict[str, int] = {}
        self.questions = TEST_QUESTIONS.copy()
        self.current_index = 0

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def is_complete(self) -> bool:
        return self.current_index >= self.total

    def current_question(self) -> dict | None:
        if self.is_complete:
            return None
        q = self.questions[self.current_index]
        return {
            "index": self.current_index + 1,
            "total": self.total,
            "id": q["id"],
            "category": q["category"],
            "text": q["text"],
            "options": q["options"],
        }

    def answer(self, user_choice: int) -> dict | None:
        if self.is_complete:
            return None
        q = self.questions[self.current_index]
        max_idx = len(q["options"]) - 1
        self.user_answers[q["id"]] = max(0, min(user_choice, max_idx))
        self.current_index += 1
        return self.current_question()


class PersonalityTestBench:
    """人格一致率テストベンチ"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm
        self.sessions: dict[str, TestBenchSession] = {}

    def start(self) -> dict:
        session_id = str(uuid.uuid4())
        session = TestBenchSession(session_id)
        self.sessions[session_id] = session
        logger.info(f"Test bench started: {session_id[:8]} questions={session.total}")
        return {
            "session_id": session_id,
            "total_questions": session.total,
            "question": session.current_question(),
        }

    def answer(self, session_id: str, user_choice: int) -> dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        next_q = session.answer(user_choice)
        result = {
            "session_id": session_id,
            "answered": len(session.user_answers),
            "total": session.total,
            "is_complete": session.is_complete,
        }
        if next_q:
            result["question"] = next_q
        else:
            result["message"] = "全質問回答完了。/test/bench/score で一致率を取得できます。"
        return result

    async def get_score(self, session_id: str) -> dict:
        """AIに同じ質問に回答させ、一致率を算出"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        if not session.is_complete:
            return {"error": "Test not complete",
                    "answered": len(session.user_answers), "total": session.total}

        # AIに回答させる
        ai_answers = await self._generate_ai_answers(session.questions)
        session.ai_answers = ai_answers

        # 一致率計算
        matches = 0
        details = []
        for q in session.questions:
            qid = q["id"]
            user_ans = session.user_answers.get(qid, -1)
            ai_ans = ai_answers.get(qid, -1)
            matched = user_ans == ai_ans
            if matched:
                matches += 1
            details.append({
                "question": q["text"],
                "category": q["category"],
                "user_answer": q["options"][user_ans] if 0 <= user_ans < len(q["options"]) else "N/A",
                "ai_answer": q["options"][ai_ans] if 0 <= ai_ans < len(q["options"]) else "N/A",
                "matched": matched,
            })

        total = len(session.questions)
        match_rate = round((matches / total) * 100, 1) if total > 0 else 0.0

        # カテゴリ別一致率
        cat_scores = {}
        for d in details:
            cat = d["category"]
            if cat not in cat_scores:
                cat_scores[cat] = {"matches": 0, "total": 0}
            cat_scores[cat]["total"] += 1
            if d["matched"]:
                cat_scores[cat]["matches"] += 1
        category_rates = {
            cat: round(s["matches"] / s["total"] * 100, 1)
            for cat, s in cat_scores.items()
        }

        logger.info(f"Test bench result: {match_rate}% ({matches}/{total})")
        del self.sessions[session_id]

        return {
            "match_rate": match_rate,
            "matches": matches,
            "total": total,
            "category_rates": category_rates,
            "details": details,
        }

    async def _generate_ai_answers(self, questions: list[dict]) -> dict[str, int]:
        """LLMにAI人格として回答させる"""
        ai_answers = {}

        if not self.llm:
            # LLMなしの場合: 中間の選択肢をデフォルトに
            for q in questions:
                ai_answers[q["id"]] = len(q["options"]) // 2
            return ai_answers

        # 人格プロンプトを構築してAIに回答させる
        # バッチで処理（10問ずつ）
        for i in range(0, len(questions), 10):
            batch = questions[i:i+10]
            prompt = self._build_ai_answer_prompt(batch)
            try:
                raw = await self.llm.generate(prompt)
                parsed = self._parse_ai_answers(raw, batch)
                ai_answers.update(parsed)
            except Exception as e:
                logger.error(f"AI answer generation failed: {e}")
                for q in batch:
                    if q["id"] not in ai_answers:
                        ai_answers[q["id"]] = len(q["options"]) // 2

        return ai_answers

    def _build_ai_answer_prompt(self, questions: list[dict]) -> str:
        """AI回答用プロンプトを構築"""
        q_text = ""
        for q in questions:
            opts = " / ".join(f"{i}: {o}" for i, o in enumerate(q["options"]))
            q_text += f"\nQ[{q['id']}]: {q['text']}\n選択肢: {opts}\n"

        return f"""あなたは現在の人格パラメータに基づいて回答してください。
各質問について、最も人格に合致する選択肢の番号のみを回答してください。

{q_text}

回答形式（各行に質問IDと回答番号だけ記載）:
{questions[0]['id']}: 0
..."""

    def _parse_ai_answers(self, raw: str, questions: list[dict]) -> dict[str, int]:
        """AI回答をパース"""
        answers = {}
        for q in questions:
            qid = q["id"]
            for line in raw.split("\n"):
                if qid in line:
                    for char in line:
                        if char.isdigit():
                            idx = int(char)
                            if idx < len(q["options"]):
                                answers[qid] = idx
                            break
                    break
            if qid not in answers:
                answers[qid] = len(q["options"]) // 2
        return answers
