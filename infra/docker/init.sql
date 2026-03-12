-- ============================================
-- cocoro-core — PostgreSQL Schema
-- Personality AI Operating System
-- ============================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

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
    ideal_profile JSONB DEFAULT '{}'::jsonb,
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
-- Sync Rate History: シンクロ率の推移
-- ============================================
CREATE TABLE sync_rate_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_rate REAL NOT NULL CHECK (sync_rate BETWEEN 0.0 AND 100.0),
    current_vector JSONB NOT NULL,
    ideal_vector JSONB NOT NULL,
    delta_detail JSONB DEFAULT '{}',
    trigger_source TEXT DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sync_rate_created ON sync_rate_history(created_at);

-- ============================================
-- Emotion State: 感情の連続値状態
-- ============================================
CREATE TABLE emotion_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    happiness REAL DEFAULT 0.5 CHECK (happiness BETWEEN 0.0 AND 1.0),
    sadness REAL DEFAULT 0.1 CHECK (sadness BETWEEN 0.0 AND 1.0),
    anger REAL DEFAULT 0.0 CHECK (anger BETWEEN 0.0 AND 1.0),
    fear REAL DEFAULT 0.1 CHECK (fear BETWEEN 0.0 AND 1.0),
    trust REAL DEFAULT 0.6 CHECK (trust BETWEEN 0.0 AND 1.0),
    surprise REAL DEFAULT 0.2 CHECK (surprise BETWEEN 0.0 AND 1.0),
    dominant_emotion TEXT DEFAULT 'neutral',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER emotion_state_updated BEFORE UPDATE ON emotion_state
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- 初期感情状態
INSERT INTO emotion_state (happiness, sadness, anger, fear, trust, surprise, dominant_emotion)
VALUES (0.5, 0.1, 0.0, 0.1, 0.6, 0.2, 'neutral');

-- ============================================
-- Emotion History: 感情変化の履歴
-- ============================================
CREATE TABLE emotion_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_event TEXT NOT NULL,
    before_state JSONB NOT NULL,
    after_state JSONB NOT NULL,
    adjustments JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_emotion_history_created ON emotion_history(created_at);

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
    source TEXT NOT NULL CHECK (source IN ('conversation', 'decision', 'task', 'reflection', 'external', 'decision_reflection')),
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
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'running', 'done', 'failed', 'cancelled')),
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
-- v7: Organization — 部門・役職・Agent登録
-- ============================================
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    manager_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT DEFAULT 'worker' CHECK (role IN ('manager', 'lead', 'worker', 'specialist')),
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    capabilities TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'busy')),
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER agent_registry_updated BEFORE UPDATE ON agent_registry
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TABLE task_delegations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 初期Agent登録
INSERT INTO departments (name, description, manager_agent) VALUES
    ('engineering', '開発・技術部門', 'dev'),
    ('sales', '営業・顧客対応部門', 'sales'),
    ('marketing', 'マーケティング・広報部門', 'marketing');

INSERT INTO agent_registry (agent_type, display_name, role, capabilities, department_id) VALUES
    ('dev', 'Dev Agent', 'lead',
     ARRAY['コード生成','API設計','バグ修正','コードレビュー','DB設計','テスト作成'],
     (SELECT id FROM departments WHERE name='engineering')),
    ('sales', 'Sales Agent', 'lead',
     ARRAY['提案書作成','見積作成','顧客分析','商談戦略','KPI分析'],
     (SELECT id FROM departments WHERE name='sales')),
    ('marketing', 'Marketing Agent', 'lead',
     ARRAY['コンテンツ企画','SNS運用','広告運用','SEO','ブランディング','データ分析'],
     (SELECT id FROM departments WHERE name='marketing'));

-- ============================================
-- Schedules: スケジュール管理
-- ============================================
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    is_all_day BOOLEAN DEFAULT FALSE,
    recurrence TEXT DEFAULT 'none' CHECK (recurrence IN ('none', 'daily', 'weekly', 'monthly')),
    reminder_minutes INTEGER DEFAULT 30,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    created_by TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER schedules_updated BEFORE UPDATE ON schedules
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE INDEX idx_schedule_start ON schedules(start_at);

-- ============================================
-- Vector Memory (pgvector + pg_trgm)
-- ============================================
CREATE TABLE knowledge_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768),
    category TEXT DEFAULT 'general',
    source TEXT DEFAULT 'manual',
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_knowledge_content ON knowledge_store USING gin(content gin_trgm_ops);
CREATE INDEX idx_knowledge_embedding ON knowledge_store USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
-- ============================================
-- Self Observations: 自己観察ログ (v5)
-- ============================================
CREATE TABLE self_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    obs_type TEXT NOT NULL CHECK (obs_type IN (
        'conversation', 'decision', 'task_success', 'task_failure',
        'emotion_change', 'learning', 'value_change', 'error')),
    summary TEXT NOT NULL,
    detail JSONB DEFAULT '{}',
    impact_score INTEGER DEFAULT 5 CHECK (impact_score BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_obs_type ON self_observations(obs_type);
CREATE INDEX idx_obs_created ON self_observations(created_at);

-- ============================================
-- Improvement Plans: 改善計画 (v5)
-- ============================================
CREATE TABLE improvement_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_score REAL DEFAULT 0,
    weak_areas JSONB DEFAULT '[]',
    actions JSONB DEFAULT '[]',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'cancelled')),
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_plans_status ON improvement_plans(status);

-- ============================================
-- Knowledge Base: 知識ストア (v5)
-- ============================================
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT DEFAULT 'conversation',
    confidence REAL DEFAULT 0.7 CHECK (confidence BETWEEN 0.0 AND 1.0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_kb_topic ON knowledge_base USING gin(topic gin_trgm_ops);

-- ============================================
-- Skills: スキル管理 (v5)
-- ============================================
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'general',
    proficiency REAL DEFAULT 0.1 CHECK (proficiency BETWEEN 0.0 AND 1.0),
    practice_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER skills_updated BEFORE UPDATE ON skills
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Tool Usage Log: ツール使用ログ (v5)
-- ============================================
CREATE TABLE tool_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name TEXT NOT NULL,
    success BOOLEAN DEFAULT true,
    duration_ms INTEGER DEFAULT 0,
    context TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_tool_usage_name ON tool_usage_log(tool_name);

-- ============================================
-- Goals: 目標管理 (v2/v4 要件)
-- ============================================
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    goal_type TEXT DEFAULT 'short_term' CHECK (goal_type IN ('short_term', 'long_term', 'life_mission')),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'abandoned')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER goals_updated BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- Governance Log: 倫理・安全チェック監査ログ (v4)
-- ============================================
CREATE TABLE governance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_type TEXT NOT NULL,
    input_summary TEXT,
    risk_level TEXT DEFAULT 'safe' CHECK (risk_level IN ('safe', 'caution', 'warning', 'blocked')),
    flags JSONB DEFAULT '[]'::jsonb,
    blocked BOOLEAN DEFAULT FALSE,
    reason TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_governance_created ON governance_log(created_at);
CREATE INDEX idx_governance_blocked ON governance_log(blocked) WHERE blocked = TRUE;

-- ============================================
-- 初期データ
-- ============================================
INSERT INTO identity (owner_name, profile, philosophy) VALUES
    ('Cocoro User', '', '人格の一貫性を最重視する');

-- 8次元 PersonalityVector (v3.5/v4 準拠)
INSERT INTO values_system (name, description, weight, category) VALUES
    ('honesty',        '誠実であること',                 0.9,  'core'),
    ('efficiency',     '効率を重視すること',              0.7,  'work'),
    ('growth',         '継続的に成長すること',             0.8,  'core'),
    ('empathy',        '共感を持って接すること',           0.6,  'social'),
    ('logic',          '論理的に判断すること',             0.8,  'thinking'),
    ('courage',        'リスクを恐れないこと',             0.4,  'core'),
    ('risk_tolerance', '不確実性を受け入れる力',           0.5,  'decision'),
    ('curiosity',      '未知への探究心と学習意欲',         0.7,  'thinking');

INSERT INTO beliefs (statement, confidence, source) VALUES
    ('データに基づく判断は感情的判断より信頼できる', 0.8, 'initial'),
    ('失敗は学習の機会である', 0.9, 'initial'),
    ('継続は最大の競争力である', 0.85, 'initial');

-- 初期目標
INSERT INTO goals (title, description, goal_type, priority) VALUES
    ('人格の一貫性を確立する', '全ての判断において価値観と信念に基づく一貫した応答を行う', 'life_mission', 9),
    ('オーナーの事業成長を支援する', '経営判断、戦略策定、業務効率化を通じて組織に貢献', 'long_term', 8),
    ('知識と判断力を向上させる', '日々の対話と経験から学び、より正確な判断を行う', 'long_term', 7);

-- ============================================
-- Migration: knowledge_base 追加カラム (user_memory 対応)
-- ============================================
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='knowledge_base' AND column_name='category'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN category TEXT DEFAULT 'general';
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='knowledge_base' AND column_name='updated_at'
    ) THEN
        ALTER TABLE knowledge_base ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
        CREATE TRIGGER kb_updated BEFORE UPDATE ON knowledge_base
            FOR EACH ROW EXECUTE FUNCTION update_timestamp();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_kb_source ON knowledge_base (source);
CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base (category);

