-- Migration v006: Add agent_port column to cocoro_nodes
-- agent_portはcoreポート(port)と別にagentのポートを管理するために追加
ALTER TABLE cocoro_nodes ADD COLUMN IF NOT EXISTS agent_port INTEGER NOT NULL DEFAULT 8002;
