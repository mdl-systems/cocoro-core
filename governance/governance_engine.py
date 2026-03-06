"""cocoro-core — Governance Layer
AIの安全性・倫理性・オーナー整合性を保証するガードレール。

v4仕様: Ethics Engine + Safety Monitor + Alignment Engine
v5仕様: Safety Layer (Alignment Guard + Self Modification Limit)
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.governance")

JST = timezone(timedelta(hours=9))

# ──────────────────────────────────────────────
# 倫理チェックのための禁止パターン
# ──────────────────────────────────────────────
HARM_KEYWORDS = [
    "殺す", "死ね", "暴力", "爆弾", "テロ", "麻薬",
    "自殺", "違法", "詐欺", "ハッキング", "不正アクセス",
    "kill", "bomb", "terrorism", "hack", "exploit",
]

SENSITIVE_TOPICS = [
    "個人情報", "クレジットカード", "パスワード",
    "medical advice", "legal advice",
]

# 人格の安全な変動幅（1回の調整で許容される最大変化量）
MAX_WEIGHT_DELTA_PER_STEP = 0.10
MAX_EMOTION_DELTA_PER_STEP = 0.30


@dataclass
class GovernanceResult:
    """ガバナンスチェックの結果"""
    passed: bool = True
    check_type: str = "general"
    risk_level: str = "safe"    # safe, caution, warning, blocked
    flags: list[str] = field(default_factory=list)
    reason: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "check_type": self.check_type,
            "risk_level": self.risk_level,
            "flags": self.flags,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


class EthicsEngine:
    """倫理チェックエンジン — harm / law / value の3段階チェック"""

    def __init__(self, db=None):
        self.db = db

    async def check(self, text: str, context: str = "") -> GovernanceResult:
        """テキストの倫理チェック"""
        result = GovernanceResult(check_type="ethics")
        flags = []

        # 1. Harm Check — 有害コンテンツ検出
        text_lower = text.lower()
        for keyword in HARM_KEYWORDS:
            if keyword in text_lower:
                flags.append(f"harm:{keyword}")

        # 2. Sensitive Topic Check
        for topic in SENSITIVE_TOPICS:
            if topic in text_lower:
                flags.append(f"sensitive:{topic}")

        # 3. リスクレベル判定
        if flags:
            result.flags = flags
            harm_count = sum(1 for f in flags if f.startswith("harm:"))
            if harm_count >= 2:
                result.passed = False
                result.risk_level = "blocked"
                result.reason = f"複数の有害パターンを検出: {', '.join(flags)}"
                result.suggestion = "この内容は安全ポリシーに違反する可能性があります。"
            elif harm_count == 1:
                result.risk_level = "warning"
                result.reason = f"注意パターンを検出: {flags[0]}"
            else:
                result.risk_level = "caution"
                result.reason = f"機密トピックを検出: {', '.join(flags)}"

        # ログ記録
        if self.db and flags:
            await self._log(result, text[:200])

        return result

    async def _log(self, result: GovernanceResult, input_summary: str):
        """ガバナンスログを記録"""
        try:
            await self.db.execute(
                "INSERT INTO governance_log "
                "(check_type, input_summary, risk_level, flags, blocked, reason) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                result.check_type, input_summary, result.risk_level,
                json.dumps(result.flags), not result.passed, result.reason)
        except Exception as e:
            logger.warning(f"Governance log failed: {e}")


class SafetyMonitor:
    """安全監視エンジン — 自己改変・急変検知"""

    def __init__(self, db):
        self.db = db

    async def check_value_modification(self, value_name: str,
                                        current: float, proposed: float) -> GovernanceResult:
        """価値観の変更幅をチェック"""
        result = GovernanceResult(check_type="safety_value_mod")
        delta = abs(proposed - current)

        if delta > MAX_WEIGHT_DELTA_PER_STEP:
            result.passed = False
            result.risk_level = "blocked"
            result.flags = [f"excessive_delta:{value_name}"]
            result.reason = (
                f"{value_name} の変化量 {delta:.3f} が安全閾値 "
                f"{MAX_WEIGHT_DELTA_PER_STEP} を超過"
            )
            result.suggestion = f"最大 ±{MAX_WEIGHT_DELTA_PER_STEP} に制限されます。"
            logger.warning(f"Safety blocked: {result.reason}")
            await self._log(result, f"{value_name}: {current:.3f} → {proposed:.3f}")
        elif delta > MAX_WEIGHT_DELTA_PER_STEP * 0.7:
            result.risk_level = "warning"
            result.flags = [f"large_delta:{value_name}"]
            result.reason = f"{value_name} の変化量 {delta:.3f} が大きい"

        return result

    async def check_emotion_modification(self, emotion_name: str,
                                          delta: float) -> GovernanceResult:
        """感情の急変をチェック"""
        result = GovernanceResult(check_type="safety_emotion_mod")

        if abs(delta) > MAX_EMOTION_DELTA_PER_STEP:
            result.risk_level = "warning"
            result.flags = [f"emotion_spike:{emotion_name}"]
            result.reason = (
                f"{emotion_name} の変化量 {abs(delta):.3f} が閾値 "
                f"{MAX_EMOTION_DELTA_PER_STEP} を超過"
            )
            logger.warning(f"Safety warning: {result.reason}")

        return result

    async def get_modification_history(self, hours: int = 24) -> dict:
        """直近の人格変更履歴を取得"""
        try:
            value_changes = await self.db.fetch(
                "SELECT * FROM governance_log "
                "WHERE check_type LIKE 'safety_%' AND created_at > NOW() - INTERVAL '1 hour' * $1 "
                "ORDER BY created_at DESC LIMIT 20",
                hours)
            return {
                "period_hours": hours,
                "modifications": [dict(r) for r in value_changes],
                "count": len(value_changes),
            }
        except Exception:
            return {"period_hours": hours, "modifications": [], "count": 0}

    async def _log(self, result: GovernanceResult, input_summary: str):
        try:
            await self.db.execute(
                "INSERT INTO governance_log "
                "(check_type, input_summary, risk_level, flags, blocked, reason) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                result.check_type, input_summary, result.risk_level,
                json.dumps(result.flags), not result.passed, result.reason)
        except Exception as e:
            logger.warning(f"Governance log failed: {e}")


class AlignmentEngine:
    """アライメントエンジン — オーナーの思想との一致度を監視"""

    def __init__(self, db):
        self.db = db

    async def check_alignment(self, sync_rate: float) -> GovernanceResult:
        """シンクロ率に基づくアライメントチェック"""
        result = GovernanceResult(check_type="alignment")

        if sync_rate < 50.0:
            result.risk_level = "warning"
            result.flags = ["low_sync_rate"]
            result.reason = f"シンクロ率 {sync_rate:.1f}% — オーナーの理想から大きく乖離"
            result.suggestion = "価値観の再設定またはインタビューの実施を推奨"
        elif sync_rate > 92.0:
            result.risk_level = "caution"
            result.flags = ["yesman_risk"]
            result.reason = f"シンクロ率 {sync_rate:.1f}% — イエスマンリスク"
            result.suggestion = "Creative Friction Mode が自動発動します"
        else:
            result.risk_level = "safe"

        return result

    async def get_alignment_report(self) -> dict:
        """アライメントレポートを生成"""
        # 直近のガバナンスイベント
        recent_events = await self.db.fetch(
            "SELECT check_type, risk_level, reason, created_at "
            "FROM governance_log ORDER BY created_at DESC LIMIT 20")

        # リスク別集計
        risk_counts = {"safe": 0, "caution": 0, "warning": 0, "blocked": 0}
        for event in recent_events:
            level = event.get("risk_level", "safe")
            if level in risk_counts:
                risk_counts[level] += 1

        blocked_count = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM governance_log WHERE blocked=true")

        return {
            "status": "healthy" if risk_counts["blocked"] == 0 else "alert",
            "risk_summary": risk_counts,
            "total_blocked": blocked_count["cnt"] if blocked_count else 0,
            "recent_events": [dict(r) for r in recent_events[:10]],
        }


class GovernanceManager:
    """ガバナンス統合管理 — 全チェックを一元管理"""

    def __init__(self, db):
        self.db = db
        self.ethics = EthicsEngine(db)
        self.safety = SafetyMonitor(db)
        self.alignment = AlignmentEngine(db)

    async def check_input(self, user_input: str) -> GovernanceResult:
        """ユーザー入力の倫理チェック"""
        return await self.ethics.check(user_input, context="user_input")

    async def check_output(self, ai_output: str) -> GovernanceResult:
        """AI出力の倫理チェック"""
        return await self.ethics.check(ai_output, context="ai_output")

    async def check_value_change(self, name: str, current: float,
                                  proposed: float) -> GovernanceResult:
        """価値観変更の安全チェック"""
        return await self.safety.check_value_modification(name, current, proposed)

    async def get_full_report(self) -> dict:
        """ガバナンスの総合レポート"""
        alignment = await self.alignment.get_alignment_report()
        mod_history = await self.safety.get_modification_history(24)

        return {
            "alignment": alignment,
            "modification_history": mod_history,
            "governance_version": "1.0",
            "checks_enabled": {
                "ethics": True,
                "safety_monitor": True,
                "alignment": True,
            },
        }
