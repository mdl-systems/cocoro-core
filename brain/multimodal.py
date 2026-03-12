"""cocoro-core — Multimodal Engine
Gemini API を使用した音声転写・画像解析処理。

Features:
  - transcribe_audio(): base64音声データ → テキスト（Gemini audio）
  - analyze_image(): base64画像データ → 説明・提案（Gemini vision）

Gemini 2.0 Flash / 2.5 Flash Lite はどちらもネイティブ multimodal に対応。
サポート形式:
  Audio: wav, mp3, aiff, aac, ogg, flac, webm, m4a
  Image: png, jpg, gif, webp, bmp
"""
import base64
import logging
import os
import asyncio

logger = logging.getLogger("cocoro.multimodal")

# 対応音声フォーマット (mime_type)
AUDIO_MIME_TYPES = {
    "wav":  "audio/wav",
    "mp3":  "audio/mpeg",
    "mpeg": "audio/mpeg",
    "ogg":  "audio/ogg",
    "webm": "audio/webm",
    "flac": "audio/flac",
    "aac":  "audio/aac",
    "aiff": "audio/aiff",
    "m4a":  "audio/mp4",
}

# 音声認識プロンプト
TRANSCRIBE_SYSTEM = (
    "あなたは高精度な音声認識AIです。"
    "与えられた音声データを正確にテキストに転写してください。"
    "句読点・改行も適切に付与してください。"
    "転写結果のテキストのみを出力し、余計な説明は不要です。"
)

# 画像解析プロンプトテンプレート
ANALYZE_SYSTEM = (
    "あなたはUIや画面コンテキストを分析する専門AIです。"
    "ユーザーの質問に基づいて画面内容を解析し、"
    "実用的な提案を日本語で提供してください。"
)


class MultimodalEngine:
    """Gemini Multimodal API ラッパー"""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        # 音声転写は gemini-2.0-flash-exp が最も安定しているが
        # 現環境の GEMINI_MODEL を使用（2.5-flash-lite も対応）
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    def _get_model(self):
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_key)
        return genai.GenerativeModel(self.model_name)

    async def transcribe_audio(
        self,
        audio_base64: str,
        language: str = "ja",
        audio_format: str = "wav",
    ) -> dict:
        """base64エンコードされた音声データをテキストに転写する。

        Args:
            audio_base64: base64エンコードされた音声データ
            language: 言語コード（デフォルト "ja"）
            audio_format: 音声フォーマット（wav/mp3/webm等）

        Returns:
            {"text": str, "confidence": float, "language": str}
        """
        if not self.gemini_key:
            raise RuntimeError("GEMINI_API_KEY が設定されていません")

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            raise ValueError(f"base64デコードに失敗しました: {e}")

        mime_type = AUDIO_MIME_TYPES.get(audio_format.lower(), "audio/wav")

        lang_hint = f"言語: {language}。" if language else ""
        prompt = (
            f"{lang_hint}"
            "この音声を正確にテキストに転写してください。"
            "転写テキストのみを返してください。"
        )

        def _sync_transcribe():
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=TRANSCRIBE_SYSTEM,
            )
            audio_part = {"mime_type": mime_type, "data": audio_bytes}
            response = model.generate_content([audio_part, prompt])
            return response.text if response.text else ""

        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, _sync_transcribe)
            text = text.strip()

            # 簡易的な信頼度推定（空でなければ 0.9 とする）
            confidence = 0.90 if len(text) > 3 else 0.30

            logger.info(f"Voice transcribed: {len(text)} chars [{language}]")
            return {
                "text": text,
                "confidence": confidence,
                "language": language,
                "char_count": len(text),
            }
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"音声転写に失敗しました: {e}")

    async def analyze_image(
        self,
        image_base64: str,
        question: str = "この画面について説明してください。",
        image_format: str = "png",
    ) -> dict:
        """base64エンコードされた画像を解析する。

        Args:
            image_base64: base64エンコードされた画像データ
            question: 画像についての質問
            image_format: 画像フォーマット（png/jpg/webp等）

        Returns:
            {"analysis": str, "suggestions": list[str]}
        """
        if not self.gemini_key:
            raise RuntimeError("GEMINI_API_KEY が設定されていません")

        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise ValueError(f"base64デコードに失敗しました: {e}")

        mime_map = {
            "png":  "image/png",
            "jpg":  "image/jpeg",
            "jpeg": "image/jpeg",
            "gif":  "image/gif",
            "webp": "image/webp",
            "bmp":  "image/bmp",
        }
        mime_type = mime_map.get(image_format.lower(), "image/png")

        prompt = (
            f"質問: {question}\n\n"
            "1. まず画面/画像の内容を簡潔に説明してください。\n"
            "2. 次に、ユーザーへの具体的な提案を3つ、"
            "「---SUGGESTIONS---」の後に箇条書きで列挙してください。\n"
            "例:\n"
            "---SUGGESTIONS---\n"
            "- 提案1\n"
            "- 提案2\n"
            "- 提案3"
        )

        def _sync_analyze():
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=ANALYZE_SYSTEM,
            )
            image_part = {"mime_type": mime_type, "data": image_bytes}
            response = model.generate_content([image_part, prompt])
            return response.text if response.text else ""

        try:
            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(None, _sync_analyze)
            raw_text = raw_text.strip()

            # 分析とサジェスチョンを分割
            if "---SUGGESTIONS---" in raw_text:
                parts = raw_text.split("---SUGGESTIONS---", 1)
                analysis = parts[0].strip()
                suggestions_raw = parts[1].strip()
                suggestions = [
                    s.lstrip("- •・").strip()
                    for s in suggestions_raw.splitlines()
                    if s.strip() and s.strip() not in ("-", "•", "・")
                ]
            else:
                analysis = raw_text
                suggestions = []

            logger.info(f"Image analyzed: {len(suggestions)} suggestions")
            return {
                "analysis": analysis,
                "suggestions": suggestions[:5],  # 最大5件
                "question": question,
            }
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise RuntimeError(f"画像解析に失敗しました: {e}")
