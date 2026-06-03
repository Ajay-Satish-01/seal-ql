-- Chat session history (CHAT_SESSION_STORE=postgres). Applied by PostgresSessionStore.ensure_schema.
CREATE SCHEMA IF NOT EXISTS seal_app;

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
    ON seal_app.chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated
    ON seal_app.chat_sessions (updated_at DESC);
