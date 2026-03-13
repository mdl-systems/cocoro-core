-- ============================================
-- Migration: Public Registration & API Keys
-- 対象テーブル:
--   agent_registrations  — 外部からのエージェント登録申請
--   agent_contacts       — エージェントへの問い合わせ
--   api_keys             — 発行済みAPIキー管理
-- ============================================

-- エージェント登録申請テーブル
CREATE TABLE IF NOT EXISTS agent_registrations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    email            TEXT NOT NULL,
    specialty        TEXT NOT NULL,
    description      TEXT DEFAULT '',
    node_url         TEXT,
    api_key_request  BOOLEAN DEFAULT FALSE,
    is_public        BOOLEAN DEFAULT TRUE,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected', 'suspended')),
    rejection_reason TEXT,
    approved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_reg_status   ON agent_registrations(status);
CREATE INDEX IF NOT EXISTS idx_agent_reg_email    ON agent_registrations(email);
CREATE INDEX IF NOT EXISTS idx_agent_reg_public   ON agent_registrations(is_public, status);

CREATE OR REPLACE TRIGGER agent_reg_updated
    BEFORE UPDATE ON agent_registrations
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();


-- エージェントへの問い合わせテーブル
CREATE TABLE IF NOT EXISTS agent_contacts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id       UUID NOT NULL REFERENCES agent_registrations(id) ON DELETE CASCADE,
    message        TEXT NOT NULL,
    contact_email  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'received'
                   CHECK (status IN ('received', 'replied', 'closed', 'spam')),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_contacts_agent ON agent_contacts(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_contacts_status ON agent_contacts(status);


-- APIキー管理テーブル
CREATE TABLE IF NOT EXISTS api_keys (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label            TEXT NOT NULL,
    key_value        TEXT NOT NULL UNIQUE,   -- 実際のキー値を保存
    key_prefix       TEXT NOT NULL,          -- 表示用プレフィックス（先頭12文字）
    scopes           TEXT[] DEFAULT '{chat}',
    registration_id  UUID REFERENCES agent_registrations(id) ON DELETE SET NULL,
    expires_at       TIMESTAMPTZ,
    is_active        BOOLEAN DEFAULT TRUE,
    last_used_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_active  ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_value   ON api_keys(key_value);
CREATE INDEX IF NOT EXISTS idx_api_keys_reg     ON api_keys(registration_id);
