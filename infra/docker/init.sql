-- ============================================
-- cocoro-core — PostgreSQL Schema
-- Personality AI Operating System
-- ============================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Identity: 人格の核
-- ============================================
CREATE TABLE identity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_name TEXT NOT NULL,
    profile TEXT DEFAULT '',
    philosophy TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER identity_updated BEFORE UPDATE ON identity
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Values: 価値観 (判断基準)
-- ============================================
CREATE TABLE values_system (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    weight REAL DEFAULT 0.5 CHECK (weight BETWEEN 0.0 AND 1.0),
    category TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER values_updated BEFORE UPDATE ON values_system
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Beliefs: 信念
-- ============================================
CREATE TABLE beliefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement TEXT NOT NULL,
    confidence REAL DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
    source TEXT DEFAULT 'initial',
    evidence_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER beliefs_updated BEFORE UPDATE ON beliefs
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Life History: 人生経験
-- ============================================
CREATE TABLE life_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN ('experience', 'achievement', 'failure', 'learning', 'milestone')),
    title TEXT NOT NULL,
    description TEXT,
    impact_score INTEGER DEFAULT 5 CHECK (impact_score BETWEEN 1 AND 10),
    lessons_learned TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Memory: Long-Term (会話・思考・判断)
-- ============================================
CREATE TABLE conversation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'cocoro', 'system')),
    content TEXT NOT NULL,
    emotion TEXT DEFAULT 'neutral',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_conv_session ON conversation_log(session_id);
CREATE INDEX idx_conv_created ON conversation_log(created_at DESC);

CREATE TABLE thought_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID,
    thought_type TEXT NOT NULL CHECK (thought_type IN ('reasoning', 'analysis', 'planning', 'reflection', 'intuition')),
    input_summary TEXT NOT NULL,
    reasoning_chain TEXT NOT NULL,
    conclusion TEXT,
    confidence REAL DEFAULT 0.0,
    values_applied TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE decision_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    context TEXT DEFAULT '{}',
    options TEXT DEFAULT '[]',
    decision TEXT NOT NULL,
    reasoning TEXT,
    values_used TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.0,
    outcome TEXT CHECK (outcome IN ('success', 'failure', 'pending', 'unknown')),
    reflection TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER decision_updated BEFORE UPDATE ON decision_log
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Learning: 学習記録
-- ============================================
CREATE TABLE learning_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('conversation', 'decision', 'task', 'reflection', 'external')),
    source_id UUID,
    lesson TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    importance INTEGER DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    applied_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Tasks: タスク管理
-- ============================================
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'done', 'failed', 'cancelled')),
    assigned_agent TEXT,
    result TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER tasks_updated BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE INDEX idx_task_status ON tasks(status);

-- ============================================
-- Vector Memory (簡易版 — pg_trgm利用)
-- ============================================
CREATE TABLE knowledge_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    source TEXT DEFAULT 'manual',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_knowledge_content ON knowledge_store USING gin(content gin_trgm_ops);

-- ============================================
-- 初期データ
-- ============================================
INSERT INTO identity (owner_name, profile, philosophy) VALUES
    ('Cocoro User', '', '人格の一貫性を最重視する');

INSERT INTO values_system (name, description, weight, category) VALUES
    ('honesty',    '誠実であること',           0.9, 'core'),
    ('efficiency', '効率を重視すること',        0.7, 'work'),
    ('growth',     '継続的に成長すること',       0.8, 'core'),
    ('empathy',    '共感を持って接すること',     0.6, 'social'),
    ('logic',      '論理的に判断すること',       0.8, 'thinking'),
    ('courage',    'リスクを恐れないこと',      0.4, 'core');

INSERT INTO beliefs (statement, confidence, source) VALUES
    ('データに基づく判断は感情的判断より信頼できる', 0.8, 'initial'),
    ('失敗は学習の機会である', 0.9, 'initial'),
    ('継続は最大の競争力である', 0.85, 'initial');
