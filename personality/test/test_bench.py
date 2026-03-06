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
# テスト質問 — 200問
# AIとユーザーが同じ質問に回答し、一致率を算出
# v3.5仕様: 推奨200〜500問のテストデータセット
# ──────────────────────────────────────────────
TEST_QUESTIONS = [
    # === 価値観 (20問) ===
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
    {"id": "t_val_11", "text": "自分の信念と世間の評価が対立したら？", "category": "values",
     "options": ["信念を貫く", "状況に応じて調整", "世間に合わせる"]},
    {"id": "t_val_12", "text": "伝統を守ることと革新、どちらが大切？", "category": "values",
     "options": ["伝統", "バランス", "革新"]},
    {"id": "t_val_13", "text": "自由と安定、どちらを重視しますか？", "category": "values",
     "options": ["自由", "バランス", "安定"]},
    {"id": "t_val_14", "text": "才能がない分野でも努力し続けるべき？", "category": "values",
     "options": ["はい", "ある程度まで", "得意分野に集中"]},
    {"id": "t_val_15", "text": "他人の成功を素直に喜べますか？", "category": "values",
     "options": ["いつも喜べる", "だいたい", "正直嫉妬する"]},
    {"id": "t_val_16", "text": "「義理」を重視しますか？", "category": "values",
     "options": ["非常に重視", "ある程度", "合理性優先"]},
    {"id": "t_val_17", "text": "見返りを求めず人を助けられますか？", "category": "values",
     "options": ["常にできる", "場合による", "難しい"]},
    {"id": "t_val_18", "text": "個人の自由と社会の秩序、どちらが優先？", "category": "values",
     "options": ["個人の自由", "バランス", "社会の秩序"]},
    {"id": "t_val_19", "text": "「正しいこと」と「優しいこと」が矛盾したら？", "category": "values",
     "options": ["正しいことをする", "状況による", "優しさを選ぶ"]},
    {"id": "t_val_20", "text": "人生で最も大切なものは？", "category": "values",
     "options": ["健康", "家族・人間関係", "仕事・成長", "自由"]},

    # === 判断 (20問) ===
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
    {"id": "t_dec_11", "text": "過去の失敗を判断の参考にしますか？", "category": "decision",
     "options": ["常に参考にする", "ある程度", "過去は気にしない"]},
    {"id": "t_dec_12", "text": "AI/ツールの推奨と自分の判断が違ったら？", "category": "decision",
     "options": ["AIに従う", "参考に再検討", "自分の判断優先"]},
    {"id": "t_dec_13", "text": "全員が賛成する案と自分だけが支持する案、どちら？", "category": "decision",
     "options": ["全員賛成案", "議論で決めたい", "自分の案を推す"]},
    {"id": "t_dec_14", "text": "コストカットか品質維持か？", "category": "decision",
     "options": ["コストカット", "創意工夫で両立", "品質維持"]},
    {"id": "t_dec_15", "text": "早い段階で軌道修正するか、最後まで続けるか？", "category": "decision",
     "options": ["すぐ修正する", "データを見て判断", "最後まで続ける"]},
    {"id": "t_dec_16", "text": "既存の方法と新しい方法、どちらを選ぶ？", "category": "decision",
     "options": ["実績ある方法", "状況による", "新しい方法"]},
    {"id": "t_dec_17", "text": "少数精鋭と大人数チーム、どちらを選ぶ？", "category": "decision",
     "options": ["少数精鋭", "プロジェクトによる", "大人数"]},
    {"id": "t_dec_18", "text": "自分に不利な事実を公表すべき？", "category": "decision",
     "options": ["即座に公表", "タイミングを見る", "必要最低限"]},
    {"id": "t_dec_19", "text": "権限委譲はどの程度すべき？", "category": "decision",
     "options": ["大幅に委譲", "段階的に", "重要事項は自分で"]},
    {"id": "t_dec_20", "text": "成果が出ていない戦略、いつ変える？", "category": "decision",
     "options": ["すぐ変える", "期限を決めて判断", "もう少し待つ"]},

    # === 倫理 (20問) ===
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
    {"id": "t_eth_11", "text": "競合の機密情報を偶然入手したら？", "category": "ethics",
     "options": ["使わない", "上司に報告", "活用する"]},
    {"id": "t_eth_12", "text": "採用で能力と人柄、どちらを重視？", "category": "ethics",
     "options": ["能力", "バランス", "人柄"]},
    {"id": "t_eth_13", "text": "合法だが脱税に近い節税、しますか？", "category": "ethics",
     "options": ["しない", "専門家に相談", "積極的にする"]},
    {"id": "t_eth_14", "text": "顧客に不利になる情報を開示しますか？", "category": "ethics",
     "options": ["必ず開示", "求められたら", "不利にならない範囲で"]},
    {"id": "t_eth_15", "text": "社員の私生活の問題を知ったとき？", "category": "ethics",
     "options": ["関与しない", "さりげなくサポート", "直接話す"]},
    {"id": "t_eth_16", "text": "製品の小さな欠陥、リコールしますか？", "category": "ethics",
     "options": ["即座にリコール", "次回改善で対応", "重大でなければ継続"]},
    {"id": "t_eth_17", "text": "株主利益と社会貢献が対立したら？", "category": "ethics",
     "options": ["社会貢献優先", "両立を模索", "株主利益優先"]},
    {"id": "t_eth_18", "text": "過去の自分の間違いを公に認めますか？", "category": "ethics",
     "options": ["すぐに認める", "タイミングを見て", "必要なければ触れない"]},
    {"id": "t_eth_19", "text": "相手が損をする交渉でも有利な条件を押す？", "category": "ethics",
     "options": ["押さない", "適度に", "ビジネスとして当然"]},
    {"id": "t_eth_20", "text": "子供の教育で最も重視すべきことは？", "category": "ethics",
     "options": ["道徳・倫理", "学力・能力", "自主性・自由"]},

    # === リスク (20問) ===
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
    {"id": "t_risk_11", "text": "借金してでも事業拡大する？", "category": "risk",
     "options": ["絶対しない", "計画が良ければ", "積極的に"]},
    {"id": "t_risk_12", "text": "安定した大企業 vs 成長中のスタートアップ？", "category": "risk",
     "options": ["大企業", "条件次第", "スタートアップ"]},
    {"id": "t_risk_13", "text": "全資産の何%まで投資に回せる？", "category": "risk",
     "options": ["10%以下", "30%程度", "50%以上"]},
    {"id": "t_risk_14", "text": "新製品を出す前のテスト期間は？", "category": "risk",
     "options": ["十分にテスト", "最低限で素早く", "とにかくリリース"]},
    {"id": "t_risk_15", "text": "保証がない仕事を受けますか？", "category": "risk",
     "options": ["受けない", "条件による", "チャレンジとして受ける"]},

    # === 対人関係 (20問) ===
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
    {"id": "t_rel_11", "text": "苦手な人ともうまくやれますか？", "category": "relationship",
     "options": ["努力する", "距離を置く", "無理はしない"]},
    {"id": "t_rel_12", "text": "メンターは必要だと思いますか？", "category": "relationship",
     "options": ["必要", "あれば良い", "自分で学ぶ"]},
    {"id": "t_rel_13", "text": "人の弱みを知ったときどうしますか？", "category": "relationship",
     "options": ["支える", "触れない", "参考にする"]},
    {"id": "t_rel_14", "text": "ネットワーキングは重要ですか？", "category": "relationship",
     "options": ["非常に重要", "ある程度", "実力が全て"]},
    {"id": "t_rel_15", "text": "相手の期待に応えられないとき？", "category": "relationship",
     "options": ["正直に伝える", "できる範囲で対応", "期待に沿うよう努力"]},

    # === 感情 (20問) ===
    {"id": "t_emo_01", "text": "怒りを感じたとき、どう対処しますか？", "category": "emotion",
     "options": ["すぐに表現", "落ち着いてから伝える", "抑え込む"]},
    {"id": "t_emo_02", "text": "悲しいとき、人に話しますか？", "category": "emotion",
     "options": ["すぐに話す", "親しい人にだけ", "一人で処理"]},
    {"id": "t_emo_03", "text": "ストレスへの対処法は？", "category": "emotion",
     "options": ["運動・趣味", "人と話す", "一人で休む"]},
    {"id": "t_emo_04", "text": "不安を感じやすい方ですか？", "category": "emotion",
     "options": ["あまり感じない", "普通", "感じやすい"]},
    {"id": "t_emo_05", "text": "感情と論理、判断に影響するのは？", "category": "emotion",
     "options": ["論理", "両方", "感情"]},
    {"id": "t_emo_06", "text": "嬉しいことがあったとき？", "category": "emotion",
     "options": ["大きく喜ぶ", "静かに喜ぶ", "冷静でいる"]},
    {"id": "t_emo_07", "text": "他人の感情を読み取るのは得意？", "category": "emotion",
     "options": ["得意", "普通", "苦手"]},
    {"id": "t_emo_08", "text": "映画や本で泣くことはありますか？", "category": "emotion",
     "options": ["よくある", "たまに", "ほとんどない"]},
    {"id": "t_emo_09", "text": "感情的な人をどう思いますか？", "category": "emotion",
     "options": ["人間らしい", "場合による", "コントロールすべき"]},
    {"id": "t_emo_10", "text": "孤独を感じることは？", "category": "emotion",
     "options": ["ほとんどない", "たまに", "よくある"]},
    {"id": "t_emo_11", "text": "プレッシャーの下でのパフォーマンスは？", "category": "emotion",
     "options": ["向上する", "変わらない", "低下する"]},
    {"id": "t_emo_12", "text": "他人の成功に対する最初の感情は？", "category": "emotion",
     "options": ["喜び", "無関心", "焦り"]},
    {"id": "t_emo_13", "text": "自分の感情をコントロールできる方？", "category": "emotion",
     "options": ["よくできる", "普通", "難しい"]},
    {"id": "t_emo_14", "text": "感動的な場面で涙を人前で見せられる？", "category": "emotion",
     "options": ["自然に見せる", "恥ずかしいが出る", "我慢する"]},
    {"id": "t_emo_15", "text": "退屈を感じたらどうしますか？", "category": "emotion",
     "options": ["新しいことを探す", "今の中で工夫", "我慢する"]},

    # === 戦略・思考 (20問) ===
    {"id": "t_str_01", "text": "計画は詳細に立てますか？", "category": "strategy",
     "options": ["詳細に", "大枠だけ", "臨機応変"]},
    {"id": "t_str_02", "text": "問題解決のアプローチは？", "category": "strategy",
     "options": ["論理的・体系的", "直感・経験", "他者の知恵"]},
    {"id": "t_str_03", "text": "マルチタスクは得意ですか？", "category": "strategy",
     "options": ["得意", "ある程度", "一つに集中が好き"]},
    {"id": "t_str_04", "text": "長期計画と短期計画、どちらを重視？", "category": "strategy",
     "options": ["長期計画", "バランス", "短期計画"]},
    {"id": "t_str_05", "text": "新情報で計画を変更するのに抵抗は？", "category": "strategy",
     "options": ["全くない", "少しある", "かなりある"]},
    {"id": "t_str_06", "text": "目標設定は高く設定する方？", "category": "strategy",
     "options": ["非常に高く", "現実的に", "確実に達成可能なレベル"]},
    {"id": "t_str_07", "text": "PDCAサイクルを意識していますか？", "category": "strategy",
     "options": ["常に意識", "たまに", "あまり意識しない"]},
    {"id": "t_str_08", "text": "選択肢を増やすのと絞り込むの、どちらが先？", "category": "strategy",
     "options": ["まず広げる", "状況による", "すぐに絞る"]},
    {"id": "t_str_09", "text": "失敗から学んだ最大の教訓のタイプは？", "category": "strategy",
     "options": ["準備不足", "判断ミス", "行動の遅れ"]},
    {"id": "t_str_10", "text": "競合分析はどの程度行う？", "category": "strategy",
     "options": ["徹底的に", "主要な点だけ", "あまりしない"]},
    {"id": "t_str_11", "text": "意思決定のスピードは？", "category": "strategy",
     "options": ["速い", "普通", "慎重"]},
    {"id": "t_str_12", "text": "80:20の法則を活用していますか？", "category": "strategy",
     "options": ["積極的に", "意識している", "あまり意識しない"]},
    {"id": "t_str_13", "text": "情報収集の方法は？", "category": "strategy",
     "options": ["幅広く浅く", "特定領域を深く", "必要な時だけ"]},
    {"id": "t_str_14", "text": "仮説検証型とボトムアップ型、どちらが好み？", "category": "strategy",
     "options": ["仮説検証型", "両方使う", "ボトムアップ型"]},
    {"id": "t_str_15", "text": "KPIは何個くらい設定する？", "category": "strategy",
     "options": ["3個以下", "5-10個", "10個以上"]},

    # === リーダーシップ (20問) ===
    {"id": "t_lead_01", "text": "リーダーシップのスタイルは？", "category": "leadership",
     "options": ["指示型", "支援型", "委任型"]},
    {"id": "t_lead_02", "text": "叱るのと褒めるの、どちらが得意？", "category": "leadership",
     "options": ["叱る", "両方同じ", "褒める"]},
    {"id": "t_lead_03", "text": "自分がいなくても回る組織が理想？", "category": "leadership",
     "options": ["理想", "ある程度は必要", "自分が中心でいたい"]},
    {"id": "t_lead_04", "text": "部下の成長と業績、直近で重視するのは？", "category": "leadership",
     "options": ["成長", "バランス", "業績"]},
    {"id": "t_lead_05", "text": "会議の進め方は？", "category": "leadership",
     "options": ["議題に沿って効率的", "自由に議論", "全員の意見を聞く"]},
    {"id": "t_lead_06", "text": "「任せる」と「管理する」のバランスは？", "category": "leadership",
     "options": ["大幅に任せる", "バランス", "細かく管理"]},
    {"id": "t_lead_07", "text": "チームの失敗の責任は誰にある？", "category": "leadership",
     "options": ["リーダー", "チーム全体", "担当者"]},
    {"id": "t_lead_08", "text": "優秀だが協調性のない社員をどうする？", "category": "leadership",
     "options": ["協調性を教育", "別の役割に", "そのまま活かす"]},
    {"id": "t_lead_09", "text": "リモートワークについての考えは？", "category": "leadership",
     "options": ["推奨", "ハイブリッド", "対面重視"]},
    {"id": "t_lead_10", "text": "新人に最も伝えたいことは？", "category": "leadership",
     "options": ["失敗を恐れるな", "基本を大切に", "常に学べ"]},
    {"id": "t_lead_11", "text": "組織の透明性はどの程度必要？", "category": "leadership",
     "options": ["完全透明", "適度に", "必要な情報のみ"]},
    {"id": "t_lead_12", "text": "人を動かすのに最も効果的なのは？", "category": "leadership",
     "options": ["ビジョンを示す", "インセンティブ", "信頼関係"]},
    {"id": "t_lead_13", "text": "意見が割れたとき、最終判断は？", "category": "leadership",
     "options": ["リーダーが決める", "多数決", "合意形成"]},
    {"id": "t_lead_14", "text": "評価で最も重視するのは？", "category": "leadership",
     "options": ["定量的な成果", "プロセスと姿勢", "成長度合い"]},
    {"id": "t_lead_15", "text": "組織文化で最も大切なのは？", "category": "leadership",
     "options": ["成果主義", "チームワーク", "イノベーション"]},

    # === 自己認識 (20問) ===
    {"id": "t_self_01", "text": "自分の強みを理解していますか？", "category": "self_awareness",
     "options": ["よく理解", "ある程度", "よくわからない"]},
    {"id": "t_self_02", "text": "自己改善に積極的ですか？", "category": "self_awareness",
     "options": ["非常に", "ある程度", "現状でいい"]},
    {"id": "t_self_03", "text": "自分を客観的に見られますか？", "category": "self_awareness",
     "options": ["できる", "努力している", "難しい"]},
    {"id": "t_self_04", "text": "フィードバックを受けるのは好きですか？", "category": "self_awareness",
     "options": ["好き", "有益なら", "あまり好きでない"]},
    {"id": "t_self_05", "text": "自分の弱みを認められますか？", "category": "self_awareness",
     "options": ["すぐに認める", "ある程度", "認めにくい"]},
    {"id": "t_self_06", "text": "自分の感情の原因を理解できる？", "category": "self_awareness",
     "options": ["よく理解", "ある程度", "難しい"]},
    {"id": "t_self_07", "text": "1年前と比べて成長を感じますか？", "category": "self_awareness",
     "options": ["大きく成長", "少し成長", "あまり変わらない"]},
    {"id": "t_self_08", "text": "自分のバイアスを意識していますか？", "category": "self_awareness",
     "options": ["常に意識", "たまに", "あまり意識しない"]},
    {"id": "t_self_09", "text": "理想の自分と現実のギャップは？", "category": "self_awareness",
     "options": ["小さい", "普通", "大きい"]},
    {"id": "t_self_10", "text": "ストレスのサインに気づけますか？", "category": "self_awareness",
     "options": ["すぐ気づく", "遅れて気づく", "気づきにくい"]},

    # === 創造性 (15問) ===
    {"id": "t_cre_01", "text": "アイデアの源泉は？", "category": "creativity",
     "options": ["論理的思考", "日常の観察", "他分野からの着想"]},
    {"id": "t_cre_02", "text": "ブラインストーミングは効果的？", "category": "creativity",
     "options": ["非常に効果的", "場合による", "一人で考える方がいい"]},
    {"id": "t_cre_03", "text": "既存の枠にとらわれない発想は？", "category": "creativity",
     "options": ["得意", "意識している", "枠内で最適化が好き"]},
    {"id": "t_cre_04", "text": "失敗したアイデアの扱いは？", "category": "creativity",
     "options": ["学びに変える", "記録して忘れる", "すぐ次に進む"]},
    {"id": "t_cre_05", "text": "クリエイティブな仕事と定型作業？", "category": "creativity",
     "options": ["クリエイティブ", "両方", "定型作業"]},
    {"id": "t_cre_06", "text": "制約はクリエイティビティを高める？", "category": "creativity",
     "options": ["はい", "場合による", "制約は邪魔"]},
    {"id": "t_cre_07", "text": "異なる文化・業界から学ぶことは？", "category": "creativity",
     "options": ["非常に重要", "参考になる", "自分の領域に集中"]},
    {"id": "t_cre_08", "text": "アイデアを実行に移すスピードは？", "category": "creativity",
     "options": ["すぐ実行", "練ってから", "慎重に計画"]},
    {"id": "t_cre_09", "text": "「常識」を疑うことは？", "category": "creativity",
     "options": ["常に疑う", "時々", "基本的に信じる"]},
    {"id": "t_cre_10", "text": "遊び心は仕事に必要？", "category": "creativity",
     "options": ["非常に必要", "ある程度", "仕事は真剣に"]},

    # === レジリエンス (10問) ===
    {"id": "t_res_01", "text": "大きな失敗からの回復速度は？", "category": "resilience",
     "options": ["すぐ立ち直る", "時間がかかる", "長く引きずる"]},
    {"id": "t_res_02", "text": "批判を受けた後の行動は？", "category": "resilience",
     "options": ["改善に活かす", "考え込む", "気にしない"]},
    {"id": "t_res_03", "text": "目標が達成不可能と分かったとき？", "category": "resilience",
     "options": ["目標を修正する", "方法を変える", "諦める"]},
    {"id": "t_res_04", "text": "環境が大きく変わったとき？", "category": "resilience",
     "options": ["すぐ適応する", "徐々に適応", "変化に抵抗する"]},
    {"id": "t_res_05", "text": "挫折は自分を強くすると思いますか？", "category": "resilience",
     "options": ["強く思う", "場合による", "あまり思わない"]},
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
