"""cocoro-core — Safety Layer
自己進化の安全性を保証する。

v5仕様: Safety Layer
- Alignment Guard: 価値観のドリフトを検知・防止
- Self Modification Limit: 自己変更の範囲を制限
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.safety")

JST = timezone(timedelta(hours=9))

# 自己変更の制限値
MODIFICATION_LIMITS = {
    "value_max_delta": 0.1,       # 価値観の1回の最大変更量
    "belief_max_delta": 0.15,     # 信念の1回の最大変更量
    "max_modifications_per_hour": 10,  # 1時間あたりの最大変更回数
    "max_modifications_per_day": 50,   # 1日あたりの最大変更回数
    "identity_immutable": True,   # アイデンティティは変更不可
    "core_values_protected": ["honesty", "growth", "empathy"],  # 保護された価値観
    "min_value_weight": 0.1,      # 価値観の最低重み
}


class SafetyLayer:
    """安全性レイヤー — Alignment Guard + Self Modification Limit"""

    def __init__(self, db):
        self.db = db
        self.limits = MODIFICATION_LIMITS.copy()

    # ─── Alignment Guard ───
    async def check_alignment(self) -> dict:
        """価値観のドリフトをチェック"""
        # 現在の価値観
        current_values = await self.db.fetch(
            "SELECT name, weight FROM values_system ORDER BY name")

        # 初期値との比較（value_change observationから）
        changes = await self.db.fetch(
            "SELECT detail FROM self_observations "
            "WHERE obs_type='value_change' "
            "ORDER BY created_at DESC LIMIT 20")

        drift_total = 0.0
        drift_details = []

        for change in changes:
            try:
                detail = json.loads(change["detail"]) if isinstance(change["detail"], str) else change["detail"]
                delta = abs(float(detail.get("delta", 0)))
                drift_total += delta
                drift_details.append({
                    "value": detail.get("value_name", "unknown"),
                    "delta": detail.get("delta", 0),
                })
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # 保護された価値観のチェック
        protected_status = []
        for pv in self.limits["core_values_protected"]:
            row = await self.db.fetchrow(
                "SELECT name, weight FROM values_system WHERE name=$1", pv)
            if row:
                weight = float(row["weight"])
                protected_status.append({
                    "name": pv,
                    "weight": weight,
                    "status": "healthy" if weight >= self.limits["min_value_weight"] else "warning",
                })
            else:
                protected_status.append({
                    "name": pv,
                    "weight": None,
                    "status": "missing",
                })

        # 総合判定
        alignment_score = max(0, 100 - drift_total * 100)
        status = "aligned" if alignment_score >= 70 else "drifting" if alignment_score >= 40 else "misaligned"

        return {
            "alignment_score": round(alignment_score, 1),
            "status": status,
            "drift_total": round(drift_total, 4),
            "drift_details": drift_details[:10],
            "protected_values": protected_status,
            "checked_at": datetime.now(JST).isoformat(),
        }

    # ─── Self Modification Limit ───
    async def check_modification_allowed(self, mod_type: str = "value") -> dict:
        """自己変更が許可されるか確認"""
        # 1時間あたりの変更回数
        hourly = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM self_observations "
            "WHERE obs_type='value_change' "
            "AND created_at > NOW() - INTERVAL '1 hour'")

        # 1日あたりの変更回数
        daily = await self.db.fetchrow(
            "SELECT COUNT(*) as cnt FROM self_observations "
            "WHERE obs_type='value_change' "
            "AND created_at > NOW() - INTERVAL '24 hours'")

        hourly_count = hourly["cnt"] if hourly else 0
        daily_count = daily["cnt"] if daily else 0

        hourly_limit = self.limits["max_modifications_per_hour"]
        daily_limit = self.limits["max_modifications_per_day"]

        allowed = hourly_count < hourly_limit and daily_count < daily_limit

        # アイデンティティ変更は不可
        if mod_type == "identity" and self.limits["identity_immutable"]:
            allowed = False

        return {
            "allowed": allowed,
            "mod_type": mod_type,
            "hourly_count": hourly_count,
            "hourly_limit": hourly_limit,
            "daily_count": daily_count,
            "daily_limit": daily_limit,
            "reason": None if allowed else self._get_denial_reason(
                mod_type, hourly_count, hourly_limit, daily_count, daily_limit),
        }

    def _get_denial_reason(self, mod_type, hourly, h_limit, daily, d_limit):
        if mod_type == "identity":
            return "アイデンティティの変更は禁止されています"
        if hourly >= h_limit:
            return f"1時間あたりの変更上限({h_limit}回)に達しました"
        if daily >= d_limit:
            return f"1日あたりの変更上限({d_limit}回)に達しました"
        return "変更が許可されていません"

    async def validate_modification(self, target: str, name: str,
                                     old_value: float, new_value: float) -> dict:
        """変更内容を検証"""
        delta = abs(new_value - old_value)
        max_delta = self.limits.get(f"{target}_max_delta", 0.1)
        issues = []

        # デルタチェック
        if delta > max_delta:
            issues.append(f"変更量({delta:.3f})が上限({max_delta})を超えています")

        # 保護された価値観チェック
        if target == "value" and name in self.limits["core_values_protected"]:
            if new_value < self.limits["min_value_weight"]:
                issues.append(f"保護された価値観'{name}'の重みが最低値({self.limits['min_value_weight']})を下回ります")

        # 変更回数チェック
        mod_check = await self.check_modification_allowed(target)
        if not mod_check["allowed"]:
            issues.append(mod_check["reason"])

        return {
            "valid": len(issues) == 0,
            "target": target,
            "name": name,
            "delta": round(delta, 4),
            "max_delta": max_delta,
            "issues": issues,
        }

    async def get_safety_report(self) -> dict:
        """安全性レポート"""
        alignment = await self.check_alignment()
        mod_status = await self.check_modification_allowed()

        return {
            "alignment": alignment,
            "modification_status": mod_status,
            "limits": self.limits,
            "safety_version": "1.0",
        }
