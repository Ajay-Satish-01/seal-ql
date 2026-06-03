-- Truncate mutable demo facts before re-seeding (orders/events append on plain seed.sql re-run).
-- Products and customers use ON CONFLICT DO NOTHING in seed.sql and are left intact.
-- Timescale continuous aggregates are refreshed at the end of seed.sql after new events load.

TRUNCATE TABLE events;
TRUNCATE TABLE orders RESTART IDENTITY CASCADE;

REFRESH MATERIALIZED VIEW product_performance;
