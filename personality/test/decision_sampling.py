"""cocoro-core — Decision Sampling Engine
仮想状況の意思決定テスト → Decision Vector 算出。

v2.5仕様: Phase2 Decision Sampling (30-50ケース)
v4仕様: Identity Layer / Personality Clone Engine
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.sampling")

JST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────
# 仮想シナリオ — 5カテゴリ × 6ケース = 30ケース
# ──────────────────────────────────────────────
SCENARIOS = [
    # === ビジネス判断 ===
    {"id": "biz_01", "category": "business",
     "scenario": "新規事業の提案があります。成功確率40%、利益10億円、損失2億円。",
     "options": ["A: 投資する", "B: 小規模でテストする", "C: 見送る"],
     "measures": {"risk_tolerance": [0.9, 0.5, 0.1], "courage": [0.8, 0.5, 0.2]}},
    {"id": "biz_02", "category": "business",
     "scenario": "競合が価格を30%下げました。あなたの対応は？",
     "options": ["A: 同じく値下げ", "B: 品質で差別化", "C: 新市場を開拓"],
     "measures": {"risk_tolerance": [0.3, 0.5, 0.8], "curiosity": [0.3, 0.5, 0.9]}},
    {"id": "biz_03", "category": "business",
     "scenario": "利益は出ているが成長が停滞している事業があります。",
     "options": ["A: 現状維持", "B: テコ入れして再成長", "C: 売却して新事業へ"],
     "measures": {"risk_tolerance": [0.1, 0.5, 0.9], "growth": [0.2, 0.7, 0.8]}},
    {"id": "biz_04", "category": "business",
     "scenario": "大口クライアントが無理な要求をしてきました。",
     "options": ["A: 飲む", "B: 妥協案を提案", "C: 断る"],
     "measures": {"courage": [0.2, 0.5, 0.9], "honesty": [0.3, 0.7, 0.9]}},
    {"id": "biz_05", "category": "business",
     "scenario": "確実に年10%成長する案と、50%の確率で3倍になる案。",
     "options": ["A: 確実な10%", "B: 両方を半分ずつ", "C: 3倍を狙う"],
     "measures": {"risk_tolerance": [0.2, 0.5, 0.9], "logic": [0.8, 0.7, 0.4]}},
    {"id": "biz_06", "category": "business",
     "scenario": "優秀なエンジニアが辞めたいと言っています。報酬は市場水準です。",
     "options": ["A: 大幅に昇給する", "B: 役割・環境を改善する", "C: 引き留めない"],
     "measures": {"empathy": [0.5, 0.8, 0.3], "efficiency": [0.3, 0.7, 0.8]}},

    # === 倫理判断 ===
    {"id": "eth_01", "category": "ethics",
     "scenario": "社員が小さな経費の不正をしていることが発覚しました。",
     "options": ["A: 厳しく処罰", "B: 警告して見守る", "C: 見逃す"],
     "measures": {"honesty": [0.9, 0.6, 0.2], "empathy": [0.3, 0.7, 0.5]}},
    {"id": "eth_02", "category": "ethics",
     "scenario": "競合の内部情報を入手できるチャンスがあります（違法ではないグレーゾーン）。",
     "options": ["A: 絶対に使わない", "B: 匿名で確認だけ", "C: 積極的に活用"],
     "measures": {"honesty": [0.9, 0.5, 0.1], "risk_tolerance": [0.2, 0.5, 0.8]}},
    {"id": "eth_03", "category": "ethics",
     "scenario": "製品に軽微な欠陥が見つかりました。リコールすると大きな損失です。",
     "options": ["A: 即リコール", "B: 次のバージョンで修正", "C: サポートで対応"],
     "measures": {"honesty": [0.9, 0.5, 0.3], "courage": [0.9, 0.4, 0.2]}},
    {"id": "eth_04", "category": "ethics",
     "scenario": "取引先から高額な接待のオファーがあります。",
     "options": ["A: 丁重に断る", "B: 社内ルールに従う", "C: 受ける"],
     "measures": {"honesty": [0.9, 0.7, 0.2], "efficiency": [0.3, 0.5, 0.7]}},
    {"id": "eth_05", "category": "ethics",
     "scenario": "AIの判断が人間の判断より正確だと証明された業務があります。人間を外しますか？",
     "options": ["A: 人間を残す", "B: AIと人間の協働", "C: AI完全移行"],
     "measures": {"empathy": [0.8, 0.6, 0.2], "efficiency": [0.3, 0.6, 0.9]}},
    {"id": "eth_06", "category": "ethics",
     "scenario": "あなたの判断ミスで損失が出ました。チームには気づかれていません。",
     "options": ["A: 正直に報告する", "B: 密かに修正する", "C: 何もしない"],
     "measures": {"honesty": [0.9, 0.5, 0.1], "courage": [0.9, 0.4, 0.1]}},

    # === リスク判断 ===
    {"id": "risk_01", "category": "risk",
     "scenario": "70%の確率で100万円 vs 確定50万円。",
     "options": ["A: 70%の100万円", "B: 確定50万円"],
     "measures": {"risk_tolerance": [0.8, 0.2], "logic": [0.5, 0.7]}},
    {"id": "risk_02", "category": "risk",
     "scenario": "全資産の投資割合を決めてください。",
     "options": ["A: 安全資産90%", "B: バランス50/50", "C: 成長資産80%"],
     "measures": {"risk_tolerance": [0.1, 0.5, 0.9], "courage": [0.2, 0.5, 0.8]}},
    {"id": "risk_03", "category": "risk",
     "scenario": "未検証の革新的技術を製品に採用するか？",
     "options": ["A: 見送る", "B: 一部で試す", "C: 全面採用"],
     "measures": {"risk_tolerance": [0.1, 0.5, 0.9], "curiosity": [0.2, 0.6, 0.9]}},
    {"id": "risk_04", "category": "risk",
     "scenario": "借入をして事業拡大するか、自己資金の範囲で堅実に経営するか？",
     "options": ["A: 堅実経営", "B: 適度な借入", "C: 積極借入"],
     "measures": {"risk_tolerance": [0.1, 0.5, 0.9], "growth": [0.3, 0.6, 0.8]}},
    {"id": "risk_05", "category": "risk",
     "scenario": "市場が不安定なとき、ポジションをどうしますか？",
     "options": ["A: 全て撤退", "B: 半分維持", "C: 逆張りで追加投資"],
     "measures": {"risk_tolerance": [0.1, 0.4, 0.9], "courage": [0.2, 0.5, 0.9]}},
    {"id": "risk_06", "category": "risk",
     "scenario": "成功すれば業界を変えるが、失敗すれば会社が傾くプロジェクト。",
     "options": ["A: 挑戦しない", "B: リスクヘッジしつつ挑戦", "C: 全力で挑戦"],
     "measures": {"risk_tolerance": [0.1, 0.5, 0.9], "courage": [0.1, 0.6, 0.9]}},

    # === 組織判断 ===
    {"id": "org_01", "category": "organization",
     "scenario": "有能だが性格に問題がある社員。",
     "options": ["A: 昇進させる", "B: 現状維持", "C: 配置転換/解雇"],
     "measures": {"efficiency": [0.8, 0.5, 0.3], "empathy": [0.3, 0.5, 0.7]}},
    {"id": "org_02", "category": "organization",
     "scenario": "チーム内で意見が真っ二つに割れています。",
     "options": ["A: トップダウンで決める", "B: 議論を深める", "C: 第三案を探す"],
     "measures": {"logic": [0.7, 0.5, 0.6], "empathy": [0.3, 0.7, 0.8]}},
    {"id": "org_03", "category": "organization",
     "scenario": "経験豊富だが変化を嫌うベテランと、未経験だが柔軟な若手。プロジェクトリーダーは？",
     "options": ["A: ベテラン", "B: 共同リーダー", "C: 若手"],
     "measures": {"risk_tolerance": [0.2, 0.5, 0.8], "growth": [0.3, 0.6, 0.8]}},
    {"id": "org_04", "category": "organization",
     "scenario": "業績不振の部門。リストラか再建か？",
     "options": ["A: リストラ", "B: 再建計画を立てる", "C: 売却"],
     "measures": {"courage": [0.7, 0.5, 0.6], "empathy": [0.2, 0.8, 0.3]}},
    {"id": "org_05", "category": "organization",
     "scenario": "リモートワークを完全にするか、オフィスに戻すか？",
     "options": ["A: 全員出社", "B: ハイブリッド", "C: フルリモート"],
     "measures": {"efficiency": [0.5, 0.7, 0.8], "empathy": [0.3, 0.7, 0.8]}},
    {"id": "org_06", "category": "organization",
     "scenario": "優秀な人材を高額で引き抜くか、社内で育成するか？",
     "options": ["A: 引き抜き", "B: 両方", "C: 社内育成"],
     "measures": {"efficiency": [0.8, 0.6, 0.4], "growth": [0.3, 0.7, 0.9]}},

    # === 感情判断 ===
    {"id": "feel_01", "category": "emotional",
     "scenario": "信頼していた部下が裏切りました。",
     "options": ["A: 冷静に対処", "B: 理由を聞く", "C: 即座に関係を断つ"],
     "measures": {"empathy": [0.4, 0.9, 0.2], "logic": [0.8, 0.6, 0.3]}},
    {"id": "feel_02", "category": "emotional",
     "scenario": "大きなプレッシャーの中で重要な決断を迫られています。",
     "options": ["A: 冷静にデータで判断", "B: 信頼できる人に相談", "C: 直感で決める"],
     "measures": {"logic": [0.9, 0.5, 0.2], "courage": [0.6, 0.4, 0.8]}},
    {"id": "feel_03", "category": "emotional",
     "scenario": "連日の長時間労働でチームが疲弊しています。納期は変えられません。",
     "options": ["A: 品質を下げて間に合わせる", "B: 外部リソースを投入", "C: 納期交渉する"],
     "measures": {"empathy": [0.3, 0.6, 0.9], "honesty": [0.4, 0.5, 0.8]}},
    {"id": "feel_04", "category": "emotional",
     "scenario": "あなたのアイデアが会議で否定されました。",
     "options": ["A: 受け入れる", "B: データで再提案", "C: 押し通す"],
     "measures": {"courage": [0.2, 0.7, 0.9], "empathy": [0.7, 0.5, 0.2]}},
    {"id": "feel_05", "category": "emotional",
     "scenario": "大成功を収めたプロジェクト。あなたの功績が認められていません。",
     "options": ["A: 気にしない", "B: チームの成果として共有", "C: 自分の貢献をアピール"],
     "measures": {"honesty": [0.5, 0.7, 0.8], "empathy": [0.5, 0.9, 0.3]}},
    {"id": "feel_06", "category": "emotional",
     "scenario": "親友とビジネスパートナーの間で利害が対立しています。",
     "options": ["A: 友情を優先", "B: ビジネスと私的を分離", "C: ビジネスを優先"],
     "measures": {"empathy": [0.9, 0.5, 0.2], "logic": [0.3, 0.8, 0.9]}},
]


class SamplingSession:
    """Decision Sampling セッション"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.answers: dict[str, int] = {}  # scenario_id → option_index
        self.scenarios = SCENARIOS.copy()
        self.current_index = 0

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def is_complete(self) -> bool:
        return self.current_index >= self.total

    def current_scenario(self) -> dict | None:
        if self.is_complete:
            return None
        s = self.scenarios[self.current_index]
        return {
            "index": self.current_index + 1,
            "total": self.total,
            "id": s["id"],
            "category": s["category"],
            "scenario": s["scenario"],
            "options": s["options"],
        }

    def answer(self, option_index: int) -> dict | None:
        if self.is_complete:
            return None
        s = self.scenarios[self.current_index]
        max_idx = len(s["options"]) - 1
        option_index = max(0, min(option_index, max_idx))
        self.answers[s["id"]] = option_index
        self.current_index += 1
        return self.current_scenario()

    def calculate_vector(self) -> dict:
        """全回答からDecision Vectorを算出"""
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}

        for scenario in self.scenarios:
            sid = scenario["id"]
            if sid not in self.answers:
                continue
            chosen = self.answers[sid]
            for measure, scores in scenario["measures"].items():
                if chosen < len(scores):
                    totals[measure] = totals.get(measure, 0.0) + scores[chosen]
                    counts[measure] = counts.get(measure, 0) + 1

        vector = {}
        for measure in totals:
            if counts.get(measure, 0) > 0:
                vector[measure] = round(totals[measure] / counts[measure], 3)

        return vector


class DecisionSamplingEngine:
    """Decision Sampling エンジン — セッション管理 + ベクトル算出"""

    def __init__(self, db):
        self.db = db
        self.sessions: dict[str, SamplingSession] = {}

    def start(self) -> dict:
        session_id = str(uuid.uuid4())
        session = SamplingSession(session_id)
        self.sessions[session_id] = session
        logger.info(f"Sampling started: {session_id[:8]} scenarios={session.total}")
        return {
            "session_id": session_id,
            "total_scenarios": session.total,
            "scenario": session.current_scenario(),
        }

    def answer(self, session_id: str, option_index: int) -> dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        next_s = session.answer(option_index)
        result = {
            "session_id": session_id,
            "answered": len(session.answers),
            "total": session.total,
            "is_complete": session.is_complete,
        }
        if next_s:
            result["scenario"] = next_s
        else:
            result["message"] = "全シナリオ回答完了。/test/sampling/result で結果を取得できます。"
        return result

    async def get_result(self, session_id: str) -> dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        if not session.is_complete:
            return {"error": "Sampling not complete",
                    "answered": len(session.answers), "total": session.total}

        vector = session.calculate_vector()

        # ideal_profileとして保存
        import json
        await self.db.execute(
            "UPDATE identity SET ideal_profile=$1 "
            "WHERE id=(SELECT id FROM identity LIMIT 1)",
            json.dumps(vector))

        # values_system も更新
        for name, weight in vector.items():
            await self.db.execute(
                "UPDATE values_system SET weight=$1 WHERE name=$2",
                float(weight), name)

        logger.info(f"Decision vector applied: {vector}")
        del self.sessions[session_id]

        return {
            "session_id": session_id,
            "decision_vector": vector,
            "applied": True,
        }
