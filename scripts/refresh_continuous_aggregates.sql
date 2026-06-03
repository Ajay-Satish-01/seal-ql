-- Re-materialize Timescale continuous aggregates (events hypertable).
-- Called from seed.sql after inserts; use manually: make refresh-cagg

CALL refresh_continuous_aggregate('events_hourly', NULL, NULL);
CALL refresh_continuous_aggregate('events_daily', NULL, NULL);
