-- ============================================
-- Migration: Audit Log Table
-- cocoro-core セキュリティ監査ログ
-- ============================================

CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    endpoint        TEXT NOT NULL,
    method          TEXT NOT NULL DEFAULT 'GET',
    client_ip       TEXT,
    status_code     INTEGER,
    response_time_ms DOUBLE PRECISION,
    api_key_masked  TEXT,
    user_agent      TEXT,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス (検索・集計用)
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_endpoint    ON audit_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_audit_log_client_ip   ON audit_log(client_ip);
CREATE INDEX IF NOT EXISTS idx_audit_log_status_code ON audit_log(status_code);

-- 古いログの自動削除 (90日保持)
-- (pg_cron が必要、代替としてAPSchedulerで週次削除)
-- DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '90 days';

-- APIキーローテーション用テーブル
CREATE TABLE IF NOT EXISTS api_key_rotation (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    old_key_masked  TEXT,
    new_key_masked  TEXT,
    expires_at      TIMESTAMPTZ,   -- 旧キーの有効期限
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
