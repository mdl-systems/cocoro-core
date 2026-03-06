"""cocoro-core — Voice Interface (C-8)
音声インターフェースのバックエンド。
Web Speech API連携用の設定管理・音声コマンド解析・応答音声パラメータ生成。
"""
import logging
import re

logger = logging.getLogger("cocoro.voice")


class VoiceInterface:
    """音声インターフェース管理"""

    # 感情→音声パラメータマッピング
    EMOTION_VOICE_MAP = {
        "neutral":   {"rate": 1.0, "pitch": 1.0, "volume": 0.8},
        "happiness": {"rate": 1.1, "pitch": 1.15, "volume": 0.9},
        "sadness":   {"rate": 0.85, "pitch": 0.85, "volume": 0.6},
        "anger":     {"rate": 1.15, "pitch": 1.2, "volume": 1.0},
        "fear":      {"rate": 1.2, "pitch": 1.3, "volume": 0.5},
        "trust":     {"rate": 0.95, "pitch": 1.0, "volume": 0.85},
        "surprise":  {"rate": 1.25, "pitch": 1.3, "volume": 0.95},
    }

    # 音声コマンドパターン
    COMMAND_PATTERNS = [
        (r"(?:感情|気持ち|気分).*(?:教えて|どう|は)", "emotion_check"),
        (r"(?:名前|誰).*(?:は|ですか)", "identity"),
        (r"(?:タスク|仕事|やること).*(?:ある|ある？|は)", "task_list"),
        (r"(?:記憶|覚えて|メモ)", "memory_action"),
        (r"(?:設定|変更|切り替え)", "settings"),
        (r"(?:ありがとう|助かった|感謝)", "gratitude"),
        (r"(?:おはよう|こんにちは|こんばんは)", "greeting"),
        (r"(?:さようなら|バイバイ|じゃあね|おやすみ)", "farewell"),
        (r"(?:ヘルプ|助けて|使い方)", "help"),
        (r"(?:黙って|静かに|ミュート)", "mute"),
    ]

    def __init__(self):
        self.enabled = True
        self.language = "ja-JP"
        self.voice_name = ""  # ブラウザのデフォルト
        self.base_rate = 1.0
        self.base_pitch = 1.0
        self.base_volume = 0.8
        self.muted = False
        self._command_history: list[dict] = []

    def get_voice_params(self, emotion: str = "neutral",
                         intensity: float = 0.0) -> dict:
        """感情に基づく音声パラメータを生成"""
        base = self.EMOTION_VOICE_MAP.get(
            emotion, self.EMOTION_VOICE_MAP["neutral"]
        ).copy()

        # 感情強度でブレンド
        neutral = self.EMOTION_VOICE_MAP["neutral"]
        if intensity < 0.2:
            blend = intensity / 0.2
            for key in ["rate", "pitch", "volume"]:
                base[key] = neutral[key] + (base[key] - neutral[key]) * blend

        # ベース設定を適用
        base["rate"] *= self.base_rate
        base["pitch"] *= self.base_pitch
        base["volume"] = min(1.0, base["volume"] * (self.base_volume / 0.8))

        return {
            "rate": round(base["rate"], 2),
            "pitch": round(base["pitch"], 2),
            "volume": round(base["volume"], 2),
            "lang": self.language,
            "voice": self.voice_name,
            "muted": self.muted,
        }

    def parse_command(self, text: str) -> dict:
        """音声テキストからコマンドを解析"""
        text = text.strip()
        for pattern, cmd_type in self.COMMAND_PATTERNS:
            if re.search(pattern, text):
                cmd = {
                    "type": cmd_type,
                    "original_text": text,
                    "matched_pattern": pattern,
                }
                self._command_history.append(cmd)
                return cmd

        return {
            "type": "conversation",
            "original_text": text,
        }

    def set_settings(self, **kwargs) -> dict:
        """音声設定を変更"""
        if "language" in kwargs:
            self.language = kwargs["language"]
        if "voice_name" in kwargs:
            self.voice_name = kwargs["voice_name"]
        if "rate" in kwargs:
            self.base_rate = max(0.5, min(2.0, float(kwargs["rate"])))
        if "pitch" in kwargs:
            self.base_pitch = max(0.5, min(2.0, float(kwargs["pitch"])))
        if "volume" in kwargs:
            self.base_volume = max(0.0, min(1.0, float(kwargs["volume"])))
        if "muted" in kwargs:
            self.muted = bool(kwargs["muted"])
        if "enabled" in kwargs:
            self.enabled = bool(kwargs["enabled"])
        return self.get_settings()

    def get_settings(self) -> dict:
        """現在の音声設定"""
        return {
            "enabled": self.enabled,
            "language": self.language,
            "voice_name": self.voice_name,
            "rate": self.base_rate,
            "pitch": self.base_pitch,
            "volume": self.base_volume,
            "muted": self.muted,
        }

    def get_command_history(self, limit: int = 20) -> list[dict]:
        """コマンド履歴"""
        return self._command_history[-limit:]

    def prepare_speech(self, text: str, emotion: str = "neutral",
                       intensity: float = 0.0) -> dict:
        """テキスト読み上げ準備（フロントエンド用データ生成）"""
        params = self.get_voice_params(emotion, intensity)
        # 長いテキストは分割
        chunks = self._split_text(text)
        return {
            "text": text,
            "chunks": chunks,
            "voice_params": params,
            "chunk_count": len(chunks),
        }

    def _split_text(self, text: str, max_length: int = 200) -> list[str]:
        """テキストを適切なポイントで分割"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        # 句点・読点・改行で分割
        sentences = re.split(r'([。！？\n])', text)
        current = ""
        for i, part in enumerate(sentences):
            if current and len(current + part) > max_length:
                chunks.append(current.strip())
                current = part
            else:
                current += part
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text]

    def get_stats(self) -> dict:
        """統計"""
        return {
            "enabled": self.enabled,
            "muted": self.muted,
            "language": self.language,
            "commands_processed": len(self._command_history),
            "settings": self.get_settings(),
        }
