-- Seed data for intelligence_connector demo
-- Creates a realistic e-commerce dataset with:
--   - Regular tables (orders, products, customers)
--   - Materialized views (product_performance)
--   - TimescaleDB hypertables (events)
--   - Continuous aggregates (events_hourly)

-- ============================================================
-- REGULAR TABLES
-- ============================================================

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    cost NUMERIC(10, 2) NOT NULL
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    segment VARCHAR(30) NOT NULL,
    joined_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    amount NUMERIC(10, 2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    region VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Insert products
INSERT INTO products (name, category, price, cost) VALUES
    ('Wireless Headphones', 'Electronics', 79.99, 35.00),
    ('USB-C Hub', 'Electronics', 49.99, 18.00),
    ('Mechanical Keyboard', 'Electronics', 129.99, 55.00),
    ('Standing Desk Mat', 'Office', 39.99, 12.00),
    ('Ergonomic Chair', 'Office', 399.99, 180.00),
    ('LED Desk Lamp', 'Office', 59.99, 22.00),
    ('Running Shoes', 'Sports', 119.99, 48.00),
    ('Yoga Mat', 'Sports', 29.99, 8.00),
    ('Water Bottle', 'Sports', 24.99, 6.00),
    ('Backpack', 'Accessories', 89.99, 32.00)
ON CONFLICT DO NOTHING;

-- Insert customers
INSERT INTO customers (name, email, segment, joined_at) VALUES
    ('Alice Johnson', 'alice@example.com', 'Enterprise', '2024-01-15'),
    ('Bob Smith', 'bob@example.com', 'SMB', '2024-02-20'),
    ('Carol Williams', 'carol@example.com', 'Enterprise', '2024-03-10'),
    ('David Brown', 'david@example.com', 'Startup', '2024-04-05'),
    ('Eve Davis', 'eve@example.com', 'SMB', '2024-05-12'),
    ('Frank Miller', 'frank@example.com', 'Enterprise', '2024-06-18'),
    ('Grace Wilson', 'grace@example.com', 'Startup', '2024-07-22'),
    ('Henry Taylor', 'henry@example.com', 'SMB', '2024-08-30'),
    ('Ivy Anderson', 'ivy@example.com', 'Enterprise', '2024-09-14'),
    ('Jack Thomas', 'jack@example.com', 'Startup', '2024-10-25')
ON CONFLICT DO NOTHING;

-- Generate orders across 12 months with realistic distribution
INSERT INTO orders (customer_id, product_id, amount, quantity, status, region, created_at)
SELECT
    (random() * 9 + 1)::int AS customer_id,
    p.id AS product_id,
    p.price * (random() * 3 + 1)::int AS amount,
    (random() * 3 + 1)::int AS quantity,
    CASE
        WHEN random() < 0.85 THEN 'completed'
        WHEN random() < 0.95 THEN 'pending'
        ELSE 'cancelled'
    END AS status,
    (ARRAY['North America', 'Europe', 'Asia Pacific', 'Latin America'])[floor(random() * 4 + 1)::int] AS region,
    DATE '2024-01-01' + (random() * 364)::int * INTERVAL '1 day' + (random() * 86400)::int * INTERVAL '1 second' AS created_at
FROM products p, generate_series(1, 50) AS s
ON CONFLICT DO NOTHING;

-- ============================================================
-- MATERIALIZED VIEW
-- ============================================================

-- Pre-aggregated product performance — demonstrates matview introspection
CREATE MATERIALIZED VIEW IF NOT EXISTS product_performance AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    p.category,
    COUNT(o.id) AS total_orders,
    SUM(o.amount) AS total_revenue,
    AVG(o.amount) AS avg_order_value,
    SUM(o.amount) - (COUNT(o.id) * p.cost) AS estimated_profit
FROM products p
LEFT JOIN orders o ON o.product_id = p.id AND o.status = 'completed'
GROUP BY p.id, p.name, p.category, p.cost
WITH DATA;

-- Create an index on the matview for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_performance_id
    ON product_performance (product_id);

-- ============================================================
-- REGULAR VIEW
-- ============================================================

-- A simple view showing customer order summaries
CREATE OR REPLACE VIEW customer_summary AS
SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    c.segment,
    COUNT(o.id) AS order_count,
    COALESCE(SUM(o.amount), 0) AS total_spent,
    MAX(o.created_at) AS last_order_at
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'completed'
GROUP BY c.id, c.name, c.segment;

-- ============================================================
-- TIMESCALEDB EXTENSION + HYPERTABLE
-- ============================================================

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Events table — will be converted to a hypertable
-- Represents application/product events for time-series analytics
CREATE TABLE IF NOT EXISTS events (
    time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    customer_id INTEGER,
    product_id INTEGER,
    properties JSONB DEFAULT '{}',
    value NUMERIC(10, 2) DEFAULT 0
);

-- Convert to hypertable (partitioned by time, 7-day chunks)
SELECT create_hypertable('events', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Seed event data across 90 days
INSERT INTO events (time, event_type, customer_id, product_id, properties, value)
SELECT
    NOW() - (random() * 90)::int * INTERVAL '1 day' - (random() * 86400)::int * INTERVAL '1 second',
    (ARRAY['page_view', 'add_to_cart', 'purchase', 'search', 'review'])[floor(random() * 5 + 1)::int],
    (random() * 9 + 1)::int,
    (random() * 9 + 1)::int,
    jsonb_build_object(
        'source', (ARRAY['web', 'mobile', 'api'])[floor(random() * 3 + 1)::int],
        'country', (ARRAY['US', 'UK', 'DE', 'JP', 'BR'])[floor(random() * 5 + 1)::int]
    ),
    round((random() * 500)::numeric, 2)
FROM generate_series(1, 5000);

-- ============================================================
-- CONTINUOUS AGGREGATE
-- ============================================================

-- Hourly event aggregation — automatically refreshed by TimescaleDB
CREATE MATERIALIZED VIEW IF NOT EXISTS events_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    event_type,
    COUNT(*) AS event_count,
    SUM(value) AS total_value,
    AVG(value) AS avg_value
FROM events
GROUP BY bucket, event_type
WITH DATA;

-- Add a refresh policy: refresh every 30 minutes, covering the last 3 hours
SELECT add_continuous_aggregate_policy('events_hourly',
    start_offset    => INTERVAL '3 hours',
    end_offset      => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists   => TRUE
);

-- Daily event aggregation — another continuous aggregate for coarser granularity
CREATE MATERIALIZED VIEW IF NOT EXISTS events_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    event_type,
    COUNT(*) AS event_count,
    SUM(value) AS total_value,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value
FROM events
GROUP BY bucket, event_type
WITH DATA;

SELECT add_continuous_aggregate_policy('events_daily',
    start_offset    => INTERVAL '3 days',
    end_offset      => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists   => TRUE
);

-- Enable compression on the events hypertable (compress chunks older than 30 days)
ALTER TABLE events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'event_type'
);

SELECT add_compression_policy('events', INTERVAL '30 days', if_not_exists => TRUE);
