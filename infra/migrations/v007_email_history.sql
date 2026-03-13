-- ============================================
-- Migration: Email History Table
-- ============================================

CREATE TABLE IF NOT EXISTS email_history (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    to_addresses  TEXT[] NOT NULL,
    subject       TEXT NOT NULL,
    template      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'sent', 'failed', 'error', 'skipped')),
    resend_id     TEXT,             -- Resend API から返されるID
    error_msg     TEXT,
    triggered_by  TEXT DEFAULT 'api', -- api / scheduler_daily / auto_milestone / etc.
    sent_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_history_sent_at  ON email_history(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_history_template ON email_history(template);
CREATE INDEX IF NOT EXISTS idx_email_history_status   ON email_history(status);
