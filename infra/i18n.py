"""cocoro-core — Multi-Language Support (D-8)
多言語対応 (i18n) レイヤー。
システムメッセージやレスポンスの言語切替を管理。
"""
import logging

logger = logging.getLogger("cocoro.i18n")


# === 多言語メッセージ辞書 ===
MESSAGES = {
    "ja": {
        "greeting": "こんにちは！何かお手伝いしましょうか？",
        "farewell": "またお話しましょう！",
        "thinking": "考えています...",
        "error": "エラーが発生しました: {detail}",
        "not_found": "見つかりませんでした",
        "success": "完了しました",
        "emotion.happy": "嬉しそうですね！",
        "emotion.sad": "大丈夫ですか？",
        "emotion.neutral": "落ち着いています",
        "memory.saved": "記憶に保存しました",
        "memory.recalled": "{count}件の記憶を参照しました",
        "consolidation.start": "記憶の統合を開始します",
        "consolidation.done": "記憶の統合が完了しました",
        "growth.report": "成長率: {rate:.1f}%",
        "scheduler.started": "スケジューラーが開始しました: {name}",
        "scheduler.triggered": "{name}を手動実行しました",
        "security.blocked": "アクセスがブロックされました",
        "security.rate_limited": "リクエスト制限を超えました",
        "template.applied": "テンプレート「{name}」を適用しました",
        "integration.sent": "{platform}にメッセージを送信しました",
        "monitor.alert": "アラート: {name} ({severity})",
    },
    "en": {
        "greeting": "Hello! How can I help you?",
        "farewell": "Let's talk again!",
        "thinking": "Thinking...",
        "error": "An error occurred: {detail}",
        "not_found": "Not found",
        "success": "Completed successfully",
        "emotion.happy": "You seem happy!",
        "emotion.sad": "Are you okay?",
        "emotion.neutral": "Calm and collected",
        "memory.saved": "Saved to memory",
        "memory.recalled": "Referenced {count} memories",
        "consolidation.start": "Starting memory consolidation",
        "consolidation.done": "Memory consolidation complete",
        "growth.report": "Growth rate: {rate:.1f}%",
        "scheduler.started": "Scheduler started: {name}",
        "scheduler.triggered": "Manually triggered: {name}",
        "security.blocked": "Access blocked",
        "security.rate_limited": "Rate limit exceeded",
        "template.applied": "Template '{name}' applied",
        "integration.sent": "Message sent to {platform}",
        "monitor.alert": "Alert: {name} ({severity})",
    },
    "zh": {
        "greeting": "你好！有什么可以帮助你的？",
        "farewell": "下次再聊！",
        "thinking": "正在思考...",
        "error": "发生错误：{detail}",
        "not_found": "未找到",
        "success": "已完成",
        "emotion.happy": "你看起来很开心！",
        "emotion.sad": "你还好吗？",
        "emotion.neutral": "平静状态",
        "memory.saved": "已保存到记忆中",
        "memory.recalled": "参考了{count}条记忆",
        "consolidation.start": "开始记忆整合",
        "consolidation.done": "记忆整合完成",
        "growth.report": "成长率：{rate:.1f}%",
        "scheduler.started": "调度器已启动：{name}",
        "scheduler.triggered": "手动触发了：{name}",
        "security.blocked": "访问被阻止",
        "security.rate_limited": "超出请求限制",
        "template.applied": "已应用模板「{name}」",
        "integration.sent": "消息已发送至{platform}",
        "monitor.alert": "警报：{name}（{severity}）",
    },
    "ko": {
        "greeting": "안녕하세요! 무엇을 도와드릴까요?",
        "farewell": "다음에 또 이야기해요!",
        "thinking": "생각 중...",
        "error": "오류가 발생했습니다: {detail}",
        "not_found": "찾을 수 없습니다",
        "success": "완료되었습니다",
        "emotion.happy": "기분이 좋아 보이시네요!",
        "emotion.sad": "괜찮으세요?",
        "emotion.neutral": "차분한 상태입니다",
        "memory.saved": "기억에 저장했습니다",
        "memory.recalled": "{count}개의 기억을 참조했습니다",
        "consolidation.start": "기억 통합을 시작합니다",
        "consolidation.done": "기억 통합이 완료되었습니다",
        "growth.report": "성장률: {rate:.1f}%",
        "scheduler.started": "스케줄러 시작: {name}",
        "scheduler.triggered": "{name}을(를) 수동 실행했습니다",
        "security.blocked": "접근이 차단되었습니다",
        "security.rate_limited": "요청 제한을 초과했습니다",
        "template.applied": "템플릿 '{name}'이(가) 적용되었습니다",
        "integration.sent": "{platform}에 메시지를 전송했습니다",
        "monitor.alert": "알림: {name} ({severity})",
    },
}


class I18nManager:
    """多言語管理"""

    def __init__(self, default_lang: str = "ja"):
        self.default_lang = default_lang
        self._user_langs: dict[str, str] = {}

    @property
    def supported_languages(self) -> list[dict]:
        lang_names = {"ja": "日本語", "en": "English", "zh": "中文", "ko": "한국어"}
        return [
            {"code": code, "name": lang_names.get(code, code),
             "message_count": len(msgs)}
            for code, msgs in MESSAGES.items()
        ]

    def get_message(self, key: str, lang: str = None, **kwargs) -> str:
        """メッセージ取得 (フォールバック付き)"""
        lang = lang or self.default_lang
        msgs = MESSAGES.get(lang, MESSAGES.get(self.default_lang, {}))
        template = msgs.get(key)
        if not template:
            # fallback to default lang
            template = MESSAGES.get(self.default_lang, {}).get(key, key)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

    def set_user_language(self, user_id: str, lang: str) -> dict:
        """ユーザーの言語設定"""
        if lang not in MESSAGES:
            return {"error": f"Unsupported language: {lang}",
                    "supported": list(MESSAGES.keys())}
        self._user_langs[user_id] = lang
        return {"user_id": user_id, "language": lang, "set": True}

    def get_user_language(self, user_id: str) -> str:
        """ユーザーの言語取得"""
        return self._user_langs.get(user_id, self.default_lang)

    def translate_response(self, key: str, user_id: str = None, **kwargs) -> str:
        """ユーザーの言語設定に基づいてメッセージ翻訳"""
        lang = self.get_user_language(user_id) if user_id else self.default_lang
        return self.get_message(key, lang, **kwargs)

    def get_all_messages(self, lang: str = None) -> dict:
        """指定言語の全メッセージ返却"""
        lang = lang or self.default_lang
        return MESSAGES.get(lang, {})
