"""cocoro-core — Personality Clone Engine
人格のバックアップ・リストア・クローン機能。

v4仕様 Layer 4: Identity Layer
- Personality Clone Engine: 人格の完全バックアップ
- Personality Restore: バックアップからの復元
- Personality Export: 他のインスタンスへの移植
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("cocoro.clone")

JST = timezone(timedelta(hours=9))


class PersonalityCloneEngine:
    """人格クローンエンジン — バックアップ / リストア / エクスポート"""

    def __init__(self, db):
        self.db = db

    async def backup(self) -> dict:
        """現在の人格を完全バックアップ"""
        # Identity
        identity = await self.db.fetchrow(
            "SELECT owner_name, profile, philosophy FROM identity LIMIT 1")

        # Values
        values = await self.db.fetch(
            "SELECT name, weight, category, description FROM values_system "
            "ORDER BY weight DESC")

        # Beliefs
        beliefs = await self.db.fetch(
            "SELECT statement, confidence, source, evidence_count "
            "FROM beliefs ORDER BY confidence DESC")

        # Emotion State
        emotion = await self.db.fetchrow(
            "SELECT happiness, sadness, anger, fear, surprise, trust "
            "FROM emotion_state ORDER BY updated_at DESC LIMIT 1")

        # Goals
        goals = await self.db.fetch(
            "SELECT title, description, goal_type, priority, status "
            "FROM goals ORDER BY priority DESC")

        # Ideal Profile
        ideal = await self.db.fetchrow(
            "SELECT ideal_profile FROM identity LIMIT 1")
        ideal_profile = None
        if ideal and ideal["ideal_profile"]:
            try:
                ideal_profile = json.loads(ideal["ideal_profile"]) if isinstance(ideal["ideal_profile"], str) else ideal["ideal_profile"]
            except (json.JSONDecodeError, TypeError):
                pass

        # Sync rate
        sync = await self.db.fetchrow(
            "SELECT sync_rate FROM sync_rate_history "
            "ORDER BY measured_at DESC LIMIT 1")

        backup_data = {
            "version": "1.0",
            "backed_up_at": datetime.now(JST).isoformat(),
            "identity": {
                "owner_name": identity["owner_name"] if identity else "",
                "profile": identity["profile"] if identity else "",
                "philosophy": identity["philosophy"] if identity else "",
            },
            "values": [
                {"name": v["name"], "weight": float(v["weight"]),
                 "category": v["category"], "description": v["description"]}
                for v in values
            ],
            "beliefs": [
                {"statement": b["statement"],
                 "confidence": float(b["confidence"]),
                 "source": b["source"],
                 "evidence_count": b["evidence_count"]}
                for b in beliefs
            ],
            "emotion": {
                "happiness": float(emotion["happiness"]) if emotion else 0.5,
                "sadness": float(emotion["sadness"]) if emotion else 0.1,
                "anger": float(emotion["anger"]) if emotion else 0.0,
                "fear": float(emotion["fear"]) if emotion else 0.1,
                "surprise": float(emotion["surprise"]) if emotion else 0.2,
                "trust": float(emotion["trust"]) if emotion else 0.6,
            },
            "goals": [
                {"title": g["title"], "description": g["description"],
                 "goal_type": g["goal_type"], "priority": g["priority"],
                 "status": g["status"]}
                for g in goals
            ],
            "ideal_profile": ideal_profile,
            "sync_rate": float(sync["sync_rate"]) if sync else None,
        }

        # バックアップ記録
        await self.db.execute(
            "INSERT INTO life_history (event_type, title, description, impact_score) "
            "VALUES ('milestone', $1, $2, 3)",
            "personality_backup",
            json.dumps({
                "values_count": len(values),
                "beliefs_count": len(beliefs),
                "goals_count": len(goals),
            }, ensure_ascii=False))

        return backup_data

    async def restore(self, backup_data: dict) -> dict:
        """バックアップからの人格復元"""
        restored = {"identity": False, "values": False,
                    "beliefs": False, "emotion": False, "goals": False}

        try:
            # Identity復元
            if "identity" in backup_data:
                ident = backup_data["identity"]
                await self.db.execute(
                    "UPDATE identity SET owner_name=$1, profile=$2, philosophy=$3",
                    ident.get("owner_name", ""),
                    ident.get("profile", ""),
                    ident.get("philosophy", ""))
                restored["identity"] = True

            # Values復元
            if "values" in backup_data:
                for v in backup_data["values"]:
                    await self.db.execute(
                        "UPDATE values_system SET weight=$1 WHERE name=$2",
                        v.get("weight", 0.5), v.get("name", ""))
                restored["values"] = True

            # Beliefs復元
            if "beliefs" in backup_data:
                for b in backup_data["beliefs"]:
                    await self.db.execute(
                        "UPDATE beliefs SET confidence=$1 WHERE statement=$2",
                        b.get("confidence", 0.5), b.get("statement", ""))
                restored["beliefs"] = True

            # Emotion復元
            if "emotion" in backup_data:
                e = backup_data["emotion"]
                await self.db.execute(
                    "UPDATE emotion_state SET "
                    "happiness=$1, sadness=$2, anger=$3, "
                    "fear=$4, surprise=$5, trust=$6",
                    e.get("happiness", 0.5), e.get("sadness", 0.1),
                    e.get("anger", 0.0), e.get("fear", 0.1),
                    e.get("surprise", 0.2), e.get("trust", 0.6))
                restored["emotion"] = True

            # Goals復元
            if "goals" in backup_data:
                for g in backup_data["goals"]:
                    exists = await self.db.fetchrow(
                        "SELECT id FROM goals WHERE title=$1",
                        g.get("title", ""))
                    if not exists:
                        await self.db.execute(
                            "INSERT INTO goals (title, description, goal_type, priority, status) "
                            "VALUES ($1, $2, $3, $4, $5)",
                            g.get("title", ""), g.get("description", ""),
                            g.get("goal_type", "short_term"),
                            g.get("priority", 5),
                            g.get("status", "active"))
                restored["goals"] = True

            # 復元記録
            await self.db.execute(
                "INSERT INTO life_history (event_type, title, description, impact_score) "
                "VALUES ('milestone', $1, $2, 7)",
                "personality_restore",
                json.dumps(restored, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"success": False, "error": str(e), "restored": restored}

        return {
            "success": True,
            "restored": restored,
            "restored_at": datetime.now(JST).isoformat(),
        }

    async def get_diff(self, backup_data: dict) -> dict:
        """現在の人格とバックアップの差分を表示"""
        current = await self.backup()
        diffs = []

        # Values差分
        backup_values = {v["name"]: v["weight"] for v in backup_data.get("values", [])}
        current_values = {v["name"]: v["weight"] for v in current.get("values", [])}
        for name in set(list(backup_values.keys()) + list(current_values.keys())):
            bv = backup_values.get(name, 0)
            cv = current_values.get(name, 0)
            if abs(bv - cv) > 0.01:
                diffs.append({
                    "type": "value",
                    "name": name,
                    "backup": round(bv, 3),
                    "current": round(cv, 3),
                    "delta": round(cv - bv, 3),
                })

        # Beliefs差分
        backup_beliefs = {b["statement"]: b["confidence"]
                          for b in backup_data.get("beliefs", [])}
        current_beliefs = {b["statement"]: b["confidence"]
                          for b in current.get("beliefs", [])}
        for stmt in set(list(backup_beliefs.keys()) + list(current_beliefs.keys())):
            bb = backup_beliefs.get(stmt, 0)
            cb = current_beliefs.get(stmt, 0)
            if abs(bb - cb) > 0.01:
                diffs.append({
                    "type": "belief",
                    "statement": stmt,
                    "backup": round(bb, 3),
                    "current": round(cb, 3),
                    "delta": round(cb - bb, 3),
                })

        return {
            "total_diffs": len(diffs),
            "diffs": diffs,
            "backup_time": backup_data.get("backed_up_at"),
            "current_time": current.get("backed_up_at"),
        }
