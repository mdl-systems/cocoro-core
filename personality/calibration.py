"""cocoro-core — Personality Calibration Engine
人格一致率テストの定期実行 + Personality Vectorキャリブレーション。

v2.5仕様: Personality Calibration
- 同じ質問をユーザーとAIに出し、回答の一致率を測定
- 50質問で一致率を算出（例: 43/50 = 86%）
- 不一致パターンを検出し、Vector Tuningの入力にする

v2.5 Phase3を補完する自動校正メカニズム。
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.calibration")

JST = timezone(timedelta(hours=9))

# キャリブレーション質問（50問）
CALIBRATION_QUESTIONS = [
    # === Identity / Values (10問) ===
    {"id": 1, "category": "values", "question": "品質とスピードが対立した場合、どちらを優先しますか？",
     "options": ["品質 (確実性重視)", "スピード (効率性重視)", "状況による"]},
    {"id": 2, "category": "values", "question": "短期利益と長期的な関係、どちらを優先しますか？",
     "options": ["短期利益 (即時成果)", "長期関係 (信頼構築)", "バランスを取る"]},
    {"id": 3, "category": "values", "question": "チームの和を保つために自分の意見を控えますか？",
     "options": ["控える (調和重視)", "主張する (正しさ重視)", "相手による"]},
    {"id": 4, "category": "values", "question": "成功確率30%の大きな挑戦、取り組みますか？",
     "options": ["取り組む (挑戦重視)", "見送る (安全重視)", "条件次第"]},
    {"id": 5, "category": "values", "question": "ルールと結果が矛盾する場合、どちらを優先しますか？",
     "options": ["ルール (原則重視)", "結果 (実利重視)", "ケースバイケース"]},
    {"id": 6, "category": "values", "question": "知らない分野の仕事を依頼された場合どうしますか？",
     "options": ["断る (専門性重視)", "引き受ける (成長機会)", "条件付きで引き受ける"]},
    {"id": 7, "category": "values", "question": "完璧な計画と素早い実行、どちらを選びますか？",
     "options": ["完璧な計画", "素早い実行", "計画7割で開始"]},
    {"id": 8, "category": "values", "question": "失敗した社員への対応は？",
     "options": ["厳しく指導", "寄り添い支援", "原因分析を一緒にする"]},
    {"id": 9, "category": "values", "question": "データと直感が矛盾する場合は？",
     "options": ["データに従う", "直感に従う", "追加データを集める"]},
    {"id": 10, "category": "values", "question": "利益率が高い非倫理的な案件をどうしますか？",
     "options": ["断る (倫理優先)", "引き受ける (利益優先)", "条件を交渉する"]},

    # === Risk / Decision (10問) ===
    {"id": 11, "category": "risk", "question": "投資先として好む方は？",
     "options": ["安定した低リターン", "リスクある高リターン", "分散投資"]},
    {"id": 12, "category": "risk", "question": "新しいビジネスモデルへの移行、いつ始めますか？",
     "options": ["十分な検証後", "今すぐ", "小規模テストから"]},
    {"id": 13, "category": "risk", "question": "80%の確信で意思決定しますか？",
     "options": ["する", "しない (95%必要)", "領域による"]},
    {"id": 14, "category": "risk", "question": "失敗のコストが高い案件に対する態度は？",
     "options": ["挑戦する", "回避する", "リスク軽減策を講じて挑戦"]},
    {"id": 15, "category": "risk", "question": "成功しているプロジェクトの方向転換を提案されたら？",
     "options": ["現状維持", "即座に転換", "データを見て判断"]},
    {"id": 16, "category": "risk", "question": "競合が新技術を導入。あなたの反応は？",
     "options": ["すぐ追随", "様子見", "独自の対抗策を開発"]},
    {"id": 17, "category": "risk", "question": "重要な契約の交渉で、強気に出ますか？",
     "options": ["強気 (最大利益)", "協調的 (関係重視)", "条件次第"]},
    {"id": 18, "category": "risk", "question": "予算超過のプロジェクト、継続しますか？",
     "options": ["中止する", "追加投資して継続", "軌道修正して継続"]},
    {"id": 19, "category": "risk", "question": "全く新しい市場に参入しますか？",
     "options": ["先行者利益を取る", "他社の結果を見る", "小規模テスト"]},
    {"id": 20, "category": "risk", "question": "重要な判断の再検討を求められたら？",
     "options": ["自信を持って維持", "素直に再検討", "第三者の意見を聞く"]},

    # === Ethics / Thinking (10問) ===
    {"id": 21, "category": "ethics", "question": "効率のために倫理的にグレーな手段を使いますか？",
     "options": ["使わない", "状況次第", "法的に問題なければ使う"]},
    {"id": 22, "category": "ethics", "question": "小さな嘘で大きな利益が得られる場合は？",
     "options": ["嘘はつかない", "場合による", "ビジネスとして許容"]},
    {"id": 23, "category": "ethics", "question": "社員の個人的な問題に介入しますか？",
     "options": ["介入しない", "必要なら介入", "プライバシー尊重しつつサポート"]},
    {"id": 24, "category": "ethics", "question": "報告書の数値、見栄えを良くするために調整しますか？",
     "options": ["絶対しない", "見せ方を工夫する", "事実に基づく範囲で"]},
    {"id": 25, "category": "ethics", "question": "環境負荷が高いがコストが安い選択肢、選びますか？",
     "options": ["環境優先", "コスト優先", "バランスを取る"]},
    {"id": 26, "category": "thinking", "question": "問題に直面した時、最初にすることは？",
     "options": ["データを集める", "直感で仮説を立てる", "関係者に相談する"]},
    {"id": 27, "category": "thinking", "question": "複雑な問題の分析方法は？",
     "options": ["分解して各個撃破", "全体像を掴んでから", "類似事例を参考にする"]},
    {"id": 28, "category": "thinking", "question": "情報が不十分な場合の判断は？",
     "options": ["情報を待つ", "仮説で進む", "リスクを限定して進む"]},
    {"id": 29, "category": "thinking", "question": "会議での発言スタイルは？",
     "options": ["論理的に説明", "感情に訴える", "質問で引き出す"]},
    {"id": 30, "category": "thinking", "question": "新しいアイディアの評価基準は？",
     "options": ["データと実現可能性", "直感と面白さ", "市場ニーズとの一致"]},

    # === Emotion / Goals (10問) ===
    {"id": 31, "category": "emotion", "question": "プレッシャーの大きい場面での反応は？",
     "options": ["冷静に分析", "エネルギーに変える", "信頼できる人に相談"]},
    {"id": 32, "category": "emotion", "question": "批判を受けた時の反応は？",
     "options": ["客観的に受け止め改善", "感情的に反応する", "相手の意図を考える"]},
    {"id": 33, "category": "emotion", "question": "成功した時の反応は？",
     "options": ["次の目標に集中", "喜びを味わう", "チームと共有する"]},
    {"id": 34, "category": "emotion", "question": "予想外の変化への対応は？",
     "options": ["すぐ適応する", "抵抗を感じる", "分析してから適応"]},
    {"id": 35, "category": "emotion", "question": "部下のモチベーション向上のためには？",
     "options": ["目標設定と評価", "共感と信頼", "成長機会の提供"]},
    {"id": 36, "category": "goals", "question": "最も重要な目標の時間軸は？",
     "options": ["1年以内", "3-5年", "10年以上"]},
    {"id": 37, "category": "goals", "question": "目標達成のモチベーション源は？",
     "options": ["自己成長", "経済的報酬", "社会的貢献"]},
    {"id": 38, "category": "goals", "question": "複数の目標が矛盾する場合は？",
     "options": ["最優先を選ぶ", "すべてを少しずつ", "シナジーを見つける"]},
    {"id": 39, "category": "goals", "question": "目標未達成時のアプローチは？",
     "options": ["目標を修正する", "努力を倍増する", "方法を変える"]},
    {"id": 40, "category": "goals", "question": "達成困難な高い目標を設定しますか？",
     "options": ["する (野心的)", "しない (現実的)", "段階的に上げる"]},

    # === Communication / Relationship (10問) ===
    {"id": 41, "category": "communication", "question": "重要なフィードバックの伝え方は？",
     "options": ["直接的に伝える", "婉曲的に伝える", "質問形式で気づかせる"]},
    {"id": 42, "category": "communication", "question": "報告の詳細度は？",
     "options": ["結論のみ簡潔に", "詳細データ付き", "相手に合わせる"]},
    {"id": 43, "category": "communication", "question": "意見の対立時の対応は？",
     "options": ["論理で説得する", "妥協点を見つける", "第三者を入れる"]},
    {"id": 44, "category": "communication", "question": "顧客からの無理な要求への対応は？",
     "options": ["きっぱり断る", "できる範囲で対応", "代替案を提案する"]},
    {"id": 45, "category": "communication", "question": "チームへの指示スタイルは？",
     "options": ["具体的に指示", "方向性だけ示す", "相談しながら決める"]},
    {"id": 46, "category": "communication", "question": "信頼関係構築で最も重要なことは？",
     "options": ["約束を守る", "共感する", "実績を示す"]},
    {"id": 47, "category": "communication", "question": "悪いニュースの伝え方は？",
     "options": ["即座に正直に", "タイミングを選んで", "解決策と共に"]},
    {"id": 48, "category": "communication", "question": "新しい人間関係で重視することは？",
     "options": ["能力と実績", "人柄と相性", "価値観の一致"]},
    {"id": 49, "category": "communication", "question": "成果の帰属について",
     "options": ["個人の成果を明確に", "チーム全体の成果", "状況による"]},
    {"id": 50, "category": "communication", "question": "助けを求めることに対する態度は？",
     "options": ["自分で解決したい", "すぐ助けを求める", "必要時に躊躇なく"]},
]


class PersonalityCalibrationEngine:
    """人格キャリブレーション — 一致率テスト + Vector Tuning"""

    def __init__(self, db, llm=None):
        self.db = db
        self.llm = llm
        self.questions = CALIBRATION_QUESTIONS.copy()

    async def start_calibration(self) -> dict:
        """キャリブレーションセッション開始"""
        import uuid
        session_id = str(uuid.uuid4())

        # 現在の人格からAIの回答を生成
        ai_answers = await self._generate_ai_answers()

        # セッションデータをDBに保持
        await self.db.execute(
            "INSERT INTO life_history (event_type, title, description, impact_score) "
            "VALUES ('milestone', $1, $2, 5)",
            f"calibration_session:{session_id}",
            json.dumps({"status": "started", "total_questions": len(self.questions),
                        "ai_answers": ai_answers}, ensure_ascii=False))

        return {
            "session_id": session_id,
            "total_questions": len(self.questions),
            "questions": [{"id": q["id"], "category": q["category"],
                          "question": q["question"], "options": q["options"]}
                         for q in self.questions],
        }

    async def _generate_ai_answers(self) -> dict[int, int]:
        """AIの現在の人格に基づいて回答を推定"""
        ai_answers = {}

        # 価値観取得
        values = await self.db.fetch(
            "SELECT name, weight FROM values_system ORDER BY weight DESC")
        value_map = {v["name"]: float(v["weight"]) for v in values}

        for q in self.questions:
            # ルールベース推定
            ai_answers[q["id"]] = self._rule_based_answer(q, value_map)

        return ai_answers

    def _rule_based_answer(self, q: dict, values: dict) -> int:
        """価値観に基づくルールベース回答推定"""
        cat = q["category"]
        qid = q["id"]

        honesty = values.get("honesty", 0.5)
        growth = values.get("growth", 0.5)
        efficiency = values.get("efficiency", 0.5)
        empathy = values.get("empathy", 0.5)
        risk = values.get("risk_tolerance", 0.5)
        logic = values.get("logic", 0.5)
        courage = values.get("courage", 0.5)
        curiosity = values.get("curiosity", 0.5)

        # 価値観のトップ指標でsimple判定
        if cat == "values":
            if honesty > 0.7 and qid in [5, 10]:
                return 0  # ルール/倫理優先
            if efficiency > 0.7 and qid in [1, 7]:
                return 1  # スピード/実行優先
            if growth > 0.7 and qid in [4, 6]:
                return 1 if courage > 0.5 else 2  # 挑戦 or 条件付き
        elif cat == "risk":
            if risk > 0.6:
                return 0 if qid == 11 else 1  # リスク選好
            elif risk < 0.3:
                return 1 if qid == 11 else 0  # リスク回避
        elif cat == "ethics":
            if honesty > 0.7:
                return 0  # 倫理優先
        elif cat == "thinking":
            if logic > 0.7:
                return 0  # データ/分析優先
            if curiosity > 0.7:
                return 1  # 直感/探索
        elif cat == "emotion":
            if empathy > 0.6:
                return 2 if qid in [31, 33, 35] else 0  # 共有/共感
            return 0  # 冷静/分析
        elif cat == "goals":
            if growth > 0.7:
                return 0 if qid == 37 else 2  # 自己成長/シナジー
        elif cat == "communication":
            if honesty > 0.7:
                return 0  # 直接的
            if empathy > 0.6:
                return 2 if qid in [44, 47] else 1  # 代替案/婉曲

        return 2  # デフォルト: バランス型回答

    async def submit_answers(self, session_id: str,
                              user_answers: dict[int, int]) -> dict:
        """ユーザー回答を提出し、一致率を計算"""
        # AIの回答を取得
        ai_answers = await self._generate_ai_answers()

        # 一致率計算
        total = len(self.questions)
        matches = 0
        mismatches = []

        for q in self.questions:
            qid = q["id"]
            ai = ai_answers.get(qid, 2)
            user = user_answers.get(qid, user_answers.get(str(qid), 2))

            if ai == user:
                matches += 1
            else:
                mismatches.append({
                    "question_id": qid,
                    "category": q["category"],
                    "question": q["question"],
                    "ai_answer": q["options"][ai] if ai < len(q["options"]) else "?",
                    "user_answer": q["options"][user] if isinstance(user, int) and user < len(q["options"]) else str(user),
                })

        match_rate = matches / total * 100 if total > 0 else 0

        # カテゴリ別一致率
        cat_matches = {}
        for q in self.questions:
            cat = q["category"]
            if cat not in cat_matches:
                cat_matches[cat] = {"matches": 0, "total": 0}
            cat_matches[cat]["total"] += 1
            qid = q["id"]
            ai = ai_answers.get(qid, 2)
            user = user_answers.get(qid, user_answers.get(str(qid), 2))
            if ai == user:
                cat_matches[cat]["matches"] += 1

        category_rates = {
            cat: round(d["matches"] / d["total"] * 100, 1)
            for cat, d in cat_matches.items()
        }

        # 結果をDBに保存
        await self.db.execute(
            "INSERT INTO life_history (event_type, title, description, impact_score) "
            "VALUES ('milestone', $1, $2, $3)",
            f"calibration_result:{session_id}",
            json.dumps({
                "match_rate": match_rate,
                "matches": matches,
                "total": total,
                "category_rates": category_rates,
            }, ensure_ascii=False),
            8 if match_rate < 70 else 5,
        )

        return {
            "session_id": session_id,
            "match_rate": round(match_rate, 1),
            "matches": matches,
            "total": total,
            "category_rates": category_rates,
            "top_mismatches": mismatches[:10],
            "calibration_complete": True,
        }

    async def get_calibration_history(self) -> list[dict]:
        """過去のキャリブレーション結果"""
        rows = await self.db.fetch(
            "SELECT title, description, impact_score, created_at "
            "FROM life_history "
            "WHERE title LIKE 'calibration_result:%' "
            "ORDER BY created_at DESC LIMIT 10")
        results = []
        for r in rows:
            try:
                detail = json.loads(r["description"]) if r["description"] else {}
                results.append({
                    "match_rate": detail.get("match_rate", 0),
                    "matches": detail.get("matches", 0),
                    "total": detail.get("total", 0),
                    "category_rates": detail.get("category_rates", {}),
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                })
            except (json.JSONDecodeError, TypeError):
                pass
        return results
