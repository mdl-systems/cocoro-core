-- ============================================
-- Migration v010: Node Registry Table
-- 複数miniPCノード管理テーブル
-- ============================================

-- ノード登録テーブル (cocoro_nodes)
CREATE TABLE IF NOT EXISTS cocoro_nodes (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    node_id         TEXT NOT NULL UNIQUE,          -- 例: "minipc-engineer"
    name            TEXT NOT NULL DEFAULT '',       -- 表示名
    ip              TEXT NOT NULL,                  -- 例: "192.168.50.86"
    port            INTEGER NOT NULL DEFAULT 8001,  -- cocoro-core/agent ポート
    agent_port      INTEGER NOT NULL DEFAULT 8002,  -- cocoro-agent ポート
    roles           TEXT[] NOT NULL DEFAULT '{}',   -- 担当ロールID一覧
    status          TEXT NOT NULL DEFAULT 'unknown' -- online / offline / unknown
        CHECK (status IN ('online', 'offline', 'unknown')),
    last_seen       TIMESTAMPTZ,                    -- 最後にオンライン確認した日時
    registered_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_cocoro_nodes_status  ON cocoro_nodes(status);
CREATE INDEX IF NOT EXISTS idx_cocoro_nodes_roles   ON cocoro_nodes USING GIN(roles);

-- 更新トリガー
CREATE OR REPLACE FUNCTION update_cocoro_nodes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cocoro_nodes_updated ON cocoro_nodes;
CREATE TRIGGER cocoro_nodes_updated
    BEFORE UPDATE ON cocoro_nodes
    FOR EACH ROW EXECUTE FUNCTION update_cocoro_nodes_updated_at();

-- agent_registry にノードIDカラムを追加（ノードとエージェントの紐付け用）
ALTER TABLE agent_registry
    ADD COLUMN IF NOT EXISTS node_id TEXT REFERENCES cocoro_nodes(node_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_agent_registry_node_id ON agent_registry(node_id);
