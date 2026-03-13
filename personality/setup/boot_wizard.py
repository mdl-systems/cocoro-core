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
            {"id": "bel_02", "text": "「人は基本的に信頼できる」vs「人は信頼を証明すべき」どちらに近いですか？",
             "type": "scale", "left": "基本的に信頼", "right": "証明すべき"},
            {"id": "bel_03", "text": "「努力は必ず報われる」vs「報われないこともある」どちらに近いですか？", "type": "scale",
             "left": "必ず報われる", "right": "報われないこともある"},
            {"id": "bel_04", "text": "「ルールは守るべき」vs「ルールは変えるべき」どちらに近いですか？",
             "type": "scale", "left": "守るべき", "right": "変えるべき"},
            {"id": "bel_05", "text": "「運命は決まっている」vs「自分で切り開ける」どちらに近いですか？",
             "type": "scale", "left": "決まっている", "right": "自分で切り開ける"},
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
            {"id": "risk_01", "text": "投資でどちらを選びますか？",
             "type": "choice", "options": ["A: 確実に年5%利益", "B: 30%の確率で年50%利益"]},
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
            {"id": "emo_05", "text": "「冷静」vs「感情的」どちらに近いですか？", "type": "scale",
             "left": "冷静", "right": "感情的"},
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
            {"id": "cog_04", "text": "「創造的思考」vs「論理的思考」どちらが強いですか？", "type": "scale",
             "left": "創造的思考", "right": "論理的思考"},
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
# 英語版質問データベース (40問)
# ──────────────────────────────────────────────
QUESTIONS_EN = {
    "identity": {
        "label": "Identity",
        "questions": [
            {"id": "id_01", "text": "What do you do? Tell us about your profession or area of expertise.", "type": "open"},
            {"id": "id_02", "text": "What is your greatest strength?", "type": "open"},
            {"id": "id_03", "text": "What is your life's purpose?", "type": "open"},
            {"id": "id_04", "text": "How would you describe yourself in one word?", "type": "open"},
            {"id": "id_05", "text": "Where do you see yourself in 5 years?", "type": "open"},
            {"id": "id_06", "text": "What achievement are you most proud of?", "type": "open"},
            {"id": "id_07", "text": "How do others typically describe you?", "type": "open"},
            {"id": "id_08", "text": "Work or personal life — which takes priority?",
             "type": "choice", "options": ["Work first", "Balance", "Personal life first"]},
            {"id": "id_09", "text": "Leader or follower — which comes more naturally to you?",
             "type": "choice", "options": ["Leader", "Depends on situation", "Follower"]},
            {"id": "id_10", "text": "What is your personal motto?", "type": "open"},
        ]
    },
    "values": {
        "label": "Values",
        "questions": [
            {"id": "val_01", "text": "Rank these values by importance: Integrity, Efficiency, Growth, Freedom, Stability, Challenge, Impact",
             "type": "ranking", "items": ["Integrity", "Efficiency", "Growth", "Freedom", "Stability", "Challenge", "Impact"]},
            {"id": "val_02", "text": "Money or time — which is more important?",
             "type": "choice", "options": ["Money", "Both equal", "Time"]},
            {"id": "val_03", "text": "How do you define success?", "type": "open"},
            {"id": "val_04", "text": "Doing what is right vs. doing what is efficient — which do you choose?",
             "type": "choice", "options": ["Always do what's right", "Depends", "Efficiency comes first"]},
            {"id": "val_05", "text": "What do you value most in relationships?", "type": "open"},
            {"id": "val_06", "text": "Perfectionist or good-enough mindset?",
             "type": "choice", "options": ["Perfectionist", "Case by case", "80% is fine"]},
            {"id": "val_07", "text": "Competition or collaboration — which do you prefer?",
             "type": "choice", "options": ["Competition", "Both", "Collaboration"]},
            {"id": "val_08", "text": "The safe path or the unknown — which do you choose?",
             "type": "choice", "options": ["Safe path", "Depends", "Unknown path"]},
            {"id": "val_09", "text": "What matters most when choosing a job?",
             "type": "choice", "options": ["Compensation", "Fulfillment", "Growth", "Stability", "Social impact"]},
            {"id": "val_10", "text": "What does 'happiness' mean to you?", "type": "open"},
        ]
    },
    "beliefs": {
        "label": "Beliefs",
        "questions": [
            {"id": "bel_01", "text": "'Failure should be avoided' vs 'Failure is a learning opportunity' — which is closer to your view?",
             "type": "scale", "left": "Avoid failure", "right": "Learning opportunity"},
            {"id": "bel_02", "text": "'People are trustworthy by default' vs 'Trust must be earned' — which is closer?",
             "type": "scale", "left": "Trust by default", "right": "Trust must be earned"},
            {"id": "bel_03", "text": "'Hard work always pays off' vs 'Sometimes it doesn't' — which is closer?",
             "type": "scale", "left": "Always pays off", "right": "Doesn't always"},
            {"id": "bel_04", "text": "'Rules should be followed' vs 'Rules should be changed' — which is closer?",
             "type": "scale", "left": "Follow rules", "right": "Change rules"},
            {"id": "bel_05", "text": "'Fate is predetermined' vs 'We make our own destiny' — which is closer?",
             "type": "scale", "left": "Predetermined", "right": "Self-made"},
            {"id": "bel_06", "text": "'There is one right answer' vs 'Multiple answers are valid'",
             "type": "scale", "left": "One answer", "right": "Multiple valid"},
            {"id": "bel_07", "text": "What is your most trusted source of information?",
             "type": "choice", "options": ["Personal experience", "Data & statistics", "Expert opinion", "Intuition"]},
            {"id": "bel_08", "text": "'Change is opportunity' vs 'Change is risk'",
             "type": "scale", "left": "Risk", "right": "Opportunity"},
            {"id": "bel_09", "text": "What matters most within an organization?",
             "type": "choice", "options": ["Leadership quality", "Teamwork", "Processes & systems", "Individual ability"]},
            {"id": "bel_10", "text": "What is the one belief you will never compromise on?", "type": "open"},
        ]
    },
    "decision_style": {
        "label": "Decision Style",
        "questions": [
            {"id": "dec_01", "text": "When making decisions, what do you rely on most?",
             "type": "choice", "options": ["Data & analysis", "Intuition & experience", "Expert advice", "Team consensus"]},
            {"id": "dec_02", "text": "How much time do you take for important decisions?",
             "type": "choice", "options": ["Decide immediately", "A few hours to a day", "A few days to a week", "Take my time"]},
            {"id": "dec_03", "text": "When you make a wrong judgment, how do you respond?", "type": "open"},
            {"id": "dec_04", "text": "Do you make decisions even with incomplete information?",
             "type": "choice", "options": ["Yes, decide right away", "With minimal info", "Only with sufficient info"]},
            {"id": "dec_05", "text": "What was the hardest decision you've ever made?", "type": "open"},
            {"id": "dec_06", "text": "How much do others' opinions influence your decisions?",
             "type": "scale", "left": "Not at all", "right": "Greatly influenced"},
            {"id": "dec_07", "text": "'Look before you leap' vs 'Just try it' — which fits you?",
             "type": "scale", "left": "Look first", "right": "Just try"},
            {"id": "dec_08", "text": "Would you take on a high-risk challenge?",
             "type": "choice", "options": ["Actively yes", "After assessing risk", "Prefer to avoid"]},
            {"id": "dec_09", "text": "Rationality or emotion — which guides your decisions?",
             "type": "choice", "options": ["Rationality", "Balance", "Emotion"]},
            {"id": "dec_10", "text": "Do you often regret your decisions?",
             "type": "choice", "options": ["Rarely", "Occasionally", "Often"]},
        ]
    },
    "risk_profile": {
        "label": "Risk Profile",
        "questions": [
            {"id": "risk_01", "text": "Which investment would you choose?",
             "type": "choice", "options": ["A: Guaranteed 5% annual return", "B: 30% chance of 50% annual return"]},
            {"id": "risk_02", "text": "A new business opportunity: 40% success rate, $1M gain, $200K loss potential. Would you invest?",
             "type": "choice", "options": ["Invest", "Gather more info first", "Don't invest"]},
            {"id": "risk_03", "text": "Stable corporate job or uncertain but high-potential entrepreneurship?",
             "type": "choice", "options": ["Corporate job", "Depends", "Entrepreneurship"]},
            {"id": "risk_04", "text": "What percentage of your total assets would you put into a single investment?",
             "type": "choice", "options": ["Less than 10%", "10-30%", "30-50%", "50% or more"]},
            {"id": "risk_05", "text": "Under a tight deadline, quality or speed — which takes priority?",
             "type": "choice", "options": ["Quality", "Balance", "Speed"]},
        ]
    },
    "emotional_profile": {
        "label": "Emotional Profile",
        "questions": [
            {"id": "emo_01", "text": "How do you deal with stress?", "type": "open"},
            {"id": "emo_02", "text": "When you feel angry, how do you act?",
             "type": "choice", "options": ["Stay calm", "Take time before responding", "Express it immediately"]},
            {"id": "emo_03", "text": "When you're happy, how do you express it?",
             "type": "choice", "options": ["Quietly feel it", "Tell someone", "Express it openly"]},
            {"id": "emo_04", "text": "How do you react when criticized?", "type": "open"},
            {"id": "emo_05", "text": "'Calm' vs 'Emotional' — which are you closer to?",
             "type": "scale", "left": "Calm", "right": "Emotional"},
        ]
    },
    "cognitive_style": {
        "label": "Cognitive Style",
        "questions": [
            {"id": "cog_01", "text": "When facing a problem, what do you do first?",
             "type": "choice", "options": ["Gather information", "Get the big picture", "Act on instinct", "Consult others"]},
            {"id": "cog_02", "text": "Big-picture thinking or attention to detail — which is your strength?",
             "type": "choice", "options": ["Big picture", "Both", "Details"]},
            {"id": "cog_03", "text": "How do you generate new ideas?", "type": "open"},
            {"id": "cog_04", "text": "'Creative thinking' vs 'Logical thinking' — which is stronger?",
             "type": "scale", "left": "Creative", "right": "Logical"},
            {"id": "cog_05", "text": "What is your most efficient way to learn?",
             "type": "choice", "options": ["Reading books/docs", "Hands-on practice", "Videos/lectures", "Learning from others"]},
        ]
    },
    "life_narrative": {
        "label": "Life Story",
        "questions": [
            {"id": "life_01", "text": "What was the most important event in your life?", "type": "open"},
            {"id": "life_02", "text": "What was your biggest failure? What did you learn from it?", "type": "open"},
            {"id": "life_03", "text": "What is the success you are most proud of?", "type": "open"},
            {"id": "life_04", "text": "Was there a turning point in your life?", "type": "open"},
            {"id": "life_05", "text": "Who has had the greatest influence on your life?", "type": "open"},
        ]
    }
}

# ──────────────────────────────────────────────
# 中国語版質問データベース (40問)
# ──────────────────────────────────────────────
QUESTIONS_ZH = {
    "identity": {
        "label": "身份认同",
        "questions": [
            {"id": "id_01", "text": "你从事什么工作？请介绍你的职业或专业领域。", "type": "open"},
            {"id": "id_02", "text": "你最大的优势是什么？", "type": "open"},
            {"id": "id_03", "text": "你认为自己人生的目的是什么？", "type": "open"},
            {"id": "id_04", "text": "如果用一个词来描述你自己，会是什么？", "type": "open"},
            {"id": "id_05", "text": "五年后，你希望成为什么样的人？", "type": "open"},
            {"id": "id_06", "text": "你最引以为傲的成就是什么？", "type": "open"},
            {"id": "id_07", "text": "别人通常如何评价你？", "type": "open"},
            {"id": "id_08", "text": "工作与私生活，你优先考虑哪个？",
             "type": "choice", "options": ["工作优先", "平衡两者", "私生活优先"]},
            {"id": "id_09", "text": "领导者还是跟随者——哪个更自然？",
             "type": "choice", "options": ["领导者", "视情况而定", "跟随者"]},
            {"id": "id_10", "text": "你的人生座右铭是什么？", "type": "open"},
        ]
    },
    "values": {
        "label": "价值观",
        "questions": [
            {"id": "val_01", "text": "请按重要性排序：诚信、效率、成长、自由、稳定、挑战、影响力",
             "type": "ranking", "items": ["诚信", "效率", "成长", "自由", "稳定", "挑战", "影响力"]},
            {"id": "val_02", "text": "金钱与时间，哪个更重要？",
             "type": "choice", "options": ["金钱", "两者同等", "时间"]},
            {"id": "val_03", "text": "你如何定义成功？", "type": "open"},
            {"id": "val_04", "text": "做正确的事还是做高效的事，你会如何选择？",
             "type": "choice", "options": ["绝对正确", "视情况", "高效优先"]},
            {"id": "val_05", "text": "在人际关系中，你最重视什么？", "type": "open"},
            {"id": "val_06", "text": "完美主义还是差不多就行？",
             "type": "choice", "options": ["完美主义", "视情况", "差不多就行"]},
            {"id": "val_07", "text": "竞争还是合作，哪个更适合你？",
             "type": "choice", "options": ["竞争", "两者皆可", "合作"]},
            {"id": "val_08", "text": "安全的道路还是未知的道路，你会如何选择？",
             "type": "choice", "options": ["安全路", "视情况", "未知路"]},
            {"id": "val_09", "text": "选择工作时，你最看重什么？",
             "type": "choice", "options": ["薪酬", "成就感", "成长机会", "稳定性", "社会贡献"]},
            {"id": "val_10", "text": "对你来说，"幸福"是什么？", "type": "open"},
        ]
    },
    "beliefs": {
        "label": "信念",
        "questions": [
            {"id": "bel_01", "text": ""失败应该避免"还是"失败是学习机会"——哪个更接近你的想法？",
             "type": "scale", "left": "应该避免", "right": "学习机会"},
            {"id": "bel_02", "text": ""人基本上是可以信任的"还是"信任需要被证明"——哪个更接近？",
             "type": "scale", "left": "可以信任", "right": "需要证明"},
            {"id": "bel_03", "text": ""努力一定有回报"还是"有时没有回报"——哪个更接近？",
             "type": "scale", "left": "一定有回报", "right": "有时没有"},
            {"id": "bel_04", "text": ""规则应该遵守"还是"规则应该改变"——哪个更接近？",
             "type": "scale", "left": "应该遵守", "right": "应该改变"},
            {"id": "bel_05", "text": ""命运是注定的"还是"自己创造命运"——哪个更接近？",
             "type": "scale", "left": "注定的", "right": "自己创造"},
            {"id": "bel_06", "text": ""答案只有一个"还是"答案有多个"",
             "type": "scale", "left": "一个答案", "right": "多个有效"},
            {"id": "bel_07", "text": "你最信任哪种信息来源？",
             "type": "choice", "options": ["个人经验", "数据与统计", "专家意见", "直觉"]},
            {"id": "bel_08", "text": ""变化是机遇"还是"变化是风险"",
             "type": "scale", "left": "风险", "right": "机遇"},
            {"id": "bel_09", "text": "在组织中，最重要的是什么？",
             "type": "choice", "options": ["领导力", "团队合作", "制度体系", "个人能力"]},
            {"id": "bel_10", "text": "你绝对不会妥协的信念是什么？", "type": "open"},
        ]
    },
    "decision_style": {
        "label": "决策风格",
        "questions": [
            {"id": "dec_01", "text": "做决策时，你最依赖什么？",
             "type": "choice", "options": ["数据与分析", "直觉与经验", "专家意见", "团队共识"]},
            {"id": "dec_02", "text": "做重要决定时，你会花多长时间？",
             "type": "choice", "options": ["马上决定", "几小时到一天", "几天到一周", "充分考虑"]},
            {"id": "dec_03", "text": "当判断失误时，你会怎么应对？", "type": "open"},
            {"id": "dec_04", "text": "信息不足时，你会做决定吗？",
             "type": "choice", "options": ["马上决定", "有最少信息就决定", "收集足够信息后决定"]},
            {"id": "dec_05", "text": "你做过最艰难的决定是什么？", "type": "open"},
        ]
    },
    "risk_profile": {
        "label": "风险偏好",
        "questions": [
            {"id": "risk_01", "text": "你会选择哪种投资？",
             "type": "choice", "options": ["A: 确定年收益5%", "B: 30%概率年收益50%"]},
            {"id": "risk_02", "text": "新商机：成功率40%，获利100万，损失20万。你会投资吗？",
             "type": "choice", "options": ["投资", "先收集更多信息", "不投资"]},
            {"id": "risk_03", "text": "稳定的工作还是不稳定但潜力大的创业？",
             "type": "choice", "options": ["稳定工作", "视情况", "创业"]},
            {"id": "risk_04", "text": "你最多会把多少比例的资产投入单一投资？",
             "type": "choice", "options": ["10%以下", "10-30%", "30-50%", "50%以上"]},
            {"id": "risk_05", "text": "截止日期临近时，质量和速度哪个更重要？",
             "type": "choice", "options": ["质量", "平衡", "速度"]},
        ]
    },
    "emotional_profile": {
        "label": "情感特征",
        "questions": [
            {"id": "emo_01", "text": "感到压力时，你如何应对？", "type": "open"},
            {"id": "emo_02", "text": "感到愤怒时，你会怎么做？",
             "type": "choice", "options": ["冷静处理", "稍等片刻再回应", "立即表达"]},
            {"id": "emo_03", "text": "高兴时，你如何表达？",
             "type": "choice", "options": ["默默感受", "告诉别人", "大方表现"]},
            {"id": "emo_04", "text": "被批评时，你会如何反应？", "type": "open"},
            {"id": "emo_05", "text": ""冷静"还是"情绪化"——哪个更接近你？",
             "type": "scale", "left": "冷静", "right": "情绪化"},
        ]
    },
    "cognitive_style": {
        "label": "思维风格",
        "questions": [
            {"id": "cog_01", "text": "面对问题时，你首先会做什么？",
             "type": "choice", "options": ["收集信息", "把握全局", "凭直觉行动", "咨询他人"]},
            {"id": "cog_02", "text": "全局思维还是注重细节——哪个是你的强项？",
             "type": "choice", "options": ["全局", "两者皆擅长", "细节"]},
            {"id": "cog_03", "text": "你如何产生新想法？", "type": "open"},
            {"id": "cog_04", "text": ""创意思维"还是"逻辑思维"——哪个更强？",
             "type": "scale", "left": "创意思维", "right": "逻辑思维"},
            {"id": "cog_05", "text": "对你来说，哪种学习方式最有效？",
             "type": "choice", "options": ["阅读书籍/文档", "实际动手", "视频/讲座", "向他人学习"]},
        ]
    },
    "life_narrative": {
        "label": "人生故事",
        "questions": [
            {"id": "life_01", "text": "你人生中最重要的事件是什么？", "type": "open"},
            {"id": "life_02", "text": "你最大的失败是什么？你从中学到了什么？", "type": "open"},
            {"id": "life_03", "text": "你最引以为傲的成功经历是什么？", "type": "open"},
            {"id": "life_04", "text": "你人生中有过转折点吗？", "type": "open"},
            {"id": "life_05", "text": "谁对你的人生影响最大？", "type": "open"},
        ]
    }
}

# 언어別質問マップ
_QUESTIONS_MAP = {
    "ja": QUESTIONS,
    "en": QUESTIONS_EN,
    "zh": QUESTIONS_ZH,
}


def get_questions(lang: str = "ja") -> dict:
    """言語コードに対応する質問データベースを返す"""
    return _QUESTIONS_MAP.get(lang, QUESTIONS)


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

    def __init__(self, session_id: str, mode: str = "boot", lang: str = "ja"):
        self.session_id = session_id
        self.mode = mode  # "boot" (40問) or "deep" (80問)
        self.lang = lang  # 言語コード: ja / en / zh
        self.answers: dict[str, str] = {}
        self.created_at = datetime.now(JST)

        # 言語・モードに応じて質問を選択
        questions_db = get_questions(lang)
        self.question_list = []
        per_category = 5 if mode == "boot" else 10
        for cat_key, cat_data in questions_db.items():
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

    def start_session(self, mode: str = "boot", lang: str = "ja") -> dict:
        """新しいセットアップセッションを開始"""
        session_id = str(uuid.uuid4())
        session = SetupSession(session_id, mode, lang=lang)
        self.sessions[session_id] = session
        logger.info(f"Setup session started: {session_id[:8]} mode={mode} lang={lang}"
                     f" questions={session.total_questions}")
        return {
            "session_id": session_id,
            "mode": mode,
            "lang": lang,
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
