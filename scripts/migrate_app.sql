-- Primary workspace storage for dashboard settings and catalog description overrides.
-- Keys: workspace_settings, catalog_overrides (JSONB). Applied on API startup.
-- config/workspace.json is a read fallback when rows are empty; .env is the base layer.
CREATE SCHEMA IF NOT EXISTS seal_app;

CREATE TABLE IF NOT EXISTS seal_app.workspace_kv (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chat session history (CHAT_SESSION_STORE=postgres).
-- Keep in sync with migrate_chat_sessions.sql (which is also applied by
-- PostgresSessionStore.ensure_schema via asyncpg at API startup).
CREATE TABLE IF NOT EXISTS seal_app.chat_sessions (
    session_id UUID PRIMARY KEY,
    title TEXT,
    database_id TEXT,
    summary TEXT,
    summary_through_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seal_app.chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES seal_app.chat_sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    explainability JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE seal_app.chat_messages
    ADD COLUMN IF NOT EXISTS explainability JSONB;

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
    ON seal_app.chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated
    ON seal_app.chat_sessions (updated_at DESC);
