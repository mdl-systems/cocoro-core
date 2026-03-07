"""cocoro-core — Quick Questions
簡易質問による人格ベクトル微調整。
5〜10問の質問でユーザーの特性を推定し補正する。
"""

QUICK_QUESTIONS = [
    {
        "id": "q1",
        "text": "新しい環境に飛び込むのは好きですか？",
        "options": [
            {"label": "大好き、ワクワクする", "modifiers": {"adventure": 0.15, "risk_tolerance": 0.10, "curiosity": 0.10}},
            {"label": "少し不安だけど挑戦したい", "modifiers": {"adaptability": 0.10, "caution": 0.05}},
            {"label": "できれば避けたい", "modifiers": {"stability_seek": 0.15, "caution": 0.10}},
        ],
    },
    {
        "id": "q2",
        "text": "グループの中でどんな役割が多いですか？",
        "options": [
            {"label": "リーダー・まとめ役", "modifiers": {"leadership": 0.15, "assertiveness": 0.10}},
            {"label": "サポート・フォロー役", "modifiers": {"cooperation": 0.15, "empathy": 0.10}},
            {"label": "アイデア出し・提案役", "modifiers": {"creativity": 0.15, "intuition": 0.10}},
            {"label": "一人で作業する方が好き", "modifiers": {"discipline": 0.10, "reflection": 0.10, "sociability": -0.10}},
        ],
    },
    {
        "id": "q3",
        "text": "困難な状況で最初にすることは？",
        "options": [
            {"label": "まず分析して計画を立てる", "modifiers": {"analysis": 0.15, "planning": 0.10, "logic": 0.10}},
            {"label": "直感に従って動く", "modifiers": {"intuition": 0.15, "speed": 0.10, "execution": 0.10}},
            {"label": "周りに相談する", "modifiers": {"cooperation": 0.10, "sociability": 0.10, "empathy": 0.05}},
            {"label": "しばらく様子を見る", "modifiers": {"caution": 0.15, "patience": 0.10, "reflection": 0.05}},
        ],
    },
    {
        "id": "q4",
        "text": "休日はどう過ごしますか？",
        "options": [
            {"label": "友人と外出する", "modifiers": {"sociability": 0.15, "optimism": 0.10}},
            {"label": "新しいことを学ぶ", "modifiers": {"curiosity": 0.15, "knowledge_drive": 0.10}},
            {"label": "のんびり家で過ごす", "modifiers": {"patience": 0.10, "reflection": 0.10, "stability_seek": 0.05}},
            {"label": "趣味や創作活動", "modifiers": {"creativity": 0.15, "persistence": 0.10}},
        ],
    },
    {
        "id": "q5",
        "text": "約束の時間に遅れそうな時は？",
        "options": [
            {"label": "絶対に遅刻しない。余裕をもって行動する", "modifiers": {"discipline": 0.15, "planning": 0.10, "self_control": 0.10}},
            {"label": "走って間に合わせる", "modifiers": {"speed": 0.10, "execution": 0.10, "motivation": 0.05}},
            {"label": "少しくらい遅れても大丈夫だと思う", "modifiers": {"optimism": 0.10, "adaptability": 0.05, "discipline": -0.10}},
        ],
    },
    {
        "id": "q6",
        "text": "意見が対立した時はどうしますか？",
        "options": [
            {"label": "自分の意見を論理的に主張する", "modifiers": {"assertiveness": 0.15, "logic": 0.10}},
            {"label": "相手の意見をまず聞く", "modifiers": {"empathy": 0.15, "cooperation": 0.10}},
            {"label": "妥協点を探す", "modifiers": {"fairness": 0.15, "adaptability": 0.10}},
            {"label": "衝突を避ける", "modifiers": {"caution": 0.10, "sensitivity": 0.10, "assertiveness": -0.10}},
        ],
    },
    {
        "id": "q7",
        "text": "大切にしていることは？",
        "options": [
            {"label": "正しさと公正さ", "modifiers": {"ethics": 0.15, "fairness": 0.15}},
            {"label": "人との繋がり", "modifiers": {"loyalty": 0.15, "empathy": 0.10}},
            {"label": "自分の成長", "modifiers": {"knowledge_drive": 0.15, "motivation": 0.10}},
            {"label": "達成感と目標", "modifiers": {"purpose": 0.15, "execution": 0.10}},
        ],
    },
    {
        "id": "q8",
        "text": "リスクについてどう思いますか？",
        "options": [
            {"label": "リスクを取らないと成長できない", "modifiers": {"risk_tolerance": 0.15, "adventure": 0.10, "motivation": 0.05}},
            {"label": "計算されたリスクなら取る", "modifiers": {"analysis": 0.10, "risk_tolerance": 0.05, "planning": 0.05}},
            {"label": "できるだけリスクは避けたい", "modifiers": {"caution": 0.15, "stability_seek": 0.10, "risk_tolerance": -0.10}},
        ],
    },
]


def get_questions(count: int = None) -> list[dict]:
    """質問リストを取得"""
    if count and count < len(QUICK_QUESTIONS):
        return QUICK_QUESTIONS[:count]
    return list(QUICK_QUESTIONS)


def apply_answers(answers: dict[str, int]) -> dict[str, float]:
    """回答から修正値を集計
    answers: {question_id: option_index}
    """
    total_modifiers: dict[str, float] = {}
    for q in QUICK_QUESTIONS:
        qid = q["id"]
        if qid in answers:
            idx = answers[qid]
            if 0 <= idx < len(q["options"]):
                mods = q["options"][idx]["modifiers"]
                for k, v in mods.items():
                    total_modifiers[k] = total_modifiers.get(k, 0) + v
    return total_modifiers
