-- ============================================
-- Migration v006: Add agent_port to cocoro_nodes
-- cocoro-agent (port 8002) へのルーティング用カラム追加
-- ============================================

-- agent_port カラムを追加（既存テーブルへの差分適用）
ALTER TABLE cocoro_nodes
    ADD COLUMN IF NOT EXISTS agent_port INTEGER NOT NULL DEFAULT 8002;

COMMENT ON COLUMN cocoro_nodes.agent_port IS 'cocoro-agent ポート (デフォルト: 8002)';
