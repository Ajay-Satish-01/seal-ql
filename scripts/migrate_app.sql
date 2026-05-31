-- Primary workspace storage for dashboard settings and catalog description overrides.
-- Keys: workspace_settings, catalog_overrides (JSONB). Applied on API startup.
-- config/workspace.json is a read fallback when rows are empty; .env is the base layer.
CREATE SCHEMA IF NOT EXISTS seal_app;

CREATE TABLE IF NOT EXISTS seal_app.workspace_kv (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
