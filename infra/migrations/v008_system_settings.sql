-- ============================================
-- Migration: System Settings Table
-- 言語設定など汎用システム設定を保存するテーブル
-- ============================================

CREATE TABLE IF NOT EXISTS system_settings (
    setting_key     TEXT PRIMARY KEY,
    setting_value   TEXT NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- デフォルト言語設定 (日本語)
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES ('language', 'ja', 'System language: ja/en/zh/ko')
ON CONFLICT (setting_key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key);
