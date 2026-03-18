-- ============================================
-- Migration v007: Org Hierarchy Structure
-- agent_registry に階層構造カラムを追加
-- ============================================

ALTER TABLE agent_registry
    ADD COLUMN IF NOT EXISTS parent_agent_id TEXT,
    ADD COLUMN IF NOT EXISTS level            INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_subordinates INTEGER DEFAULT 5;

-- インデックス: 階層検索用
CREATE INDEX IF NOT EXISTS idx_agent_registry_level
    ON agent_registry (level);

CREATE INDEX IF NOT EXISTS idx_agent_registry_parent
    ON agent_registry (parent_agent_id);

-- 既存エージェントをlevel=1（Director）に設定
UPDATE agent_registry
SET level = 1
WHERE agent_type IN ('dev', 'marketing', 'sales');

COMMENT ON COLUMN agent_registry.level IS '0=CEO, 1=Director, 2=Manager, 3=Worker';
COMMENT ON COLUMN agent_registry.parent_agent_id IS '親エージェントのagent_type';
COMMENT ON COLUMN agent_registry.max_subordinates IS '最大直属部下数';
