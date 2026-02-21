-- Oasis Rides Fraud Detection - Supabase Schema
-- Run this in the Supabase SQL Editor

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    driver_id VARCHAR(50) NOT NULL,
    card_last4 VARCHAR(4) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    pickup_city VARCHAR(100) NOT NULL,
    pickup_country VARCHAR(50) NOT NULL,
    pickup_lat DOUBLE PRECISION NOT NULL,
    pickup_lng DOUBLE PRECISION NOT NULL,
    dropoff_city VARCHAR(100) NOT NULL,
    dropoff_lat DOUBLE PRECISION NOT NULL,
    dropoff_lng DOUBLE PRECISION NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL,
    duration_minutes INTEGER NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'completed',
    is_fraudulent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk assessments table
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(50) REFERENCES transactions(transaction_id),
    risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(20) NOT NULL,
    velocity_score DOUBLE PRECISION DEFAULT 0,
    geographic_score DOUBLE PRECISION DEFAULT 0,
    amount_score DOUBLE PRECISION DEFAULT 0,
    card_testing_score DOUBLE PRECISION DEFAULT 0,
    collusion_score DOUBLE PRECISION DEFAULT 0,
    ato_score DOUBLE PRECISION DEFAULT 0,
    fraud_ring_score DOUBLE PRECISION DEFAULT 0,
    ml_score DOUBLE PRECISION DEFAULT NULL,
    triggered_rules JSONB DEFAULT '[]',
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline state table
CREATE TABLE IF NOT EXISTS pipeline_state (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'stopped',
    transactions_processed INTEGER DEFAULT 0,
    last_processed_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ML models table
CREATE TABLE IF NOT EXISTS ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    precision_score DOUBLE PRECISION,
    recall_score DOUBLE PRECISION,
    f1_score DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_card_last4 ON transactions(card_last4);
CREATE INDEX IF NOT EXISTS idx_transactions_device_id ON transactions(device_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_driver_id ON transactions(driver_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_level ON risk_assessments(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_score ON risk_assessments(risk_score);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_transaction_id ON risk_assessments(transaction_id);

-- RPC function: get unprocessed transactions
CREATE OR REPLACE FUNCTION get_unprocessed_transactions(batch_limit INTEGER DEFAULT 50)
RETURNS SETOF transactions AS $$
BEGIN
    RETURN QUERY
    SELECT t.*
    FROM transactions t
    LEFT JOIN risk_assessments r ON t.transaction_id = r.transaction_id
    WHERE r.id IS NULL
    ORDER BY t.timestamp ASC
    LIMIT batch_limit;
END;
$$ LANGUAGE plpgsql;

-- RPC function: get user transactions in time window
CREATE OR REPLACE FUNCTION get_user_transactions_window(p_user_id VARCHAR, p_hours INTEGER DEFAULT 24)
RETURNS SETOF transactions AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM transactions
    WHERE user_id = p_user_id
    AND timestamp >= NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- RPC function: get card transactions in time window
CREATE OR REPLACE FUNCTION get_card_transactions_window(p_card_last4 VARCHAR, p_hours INTEGER DEFAULT 24)
RETURNS SETOF transactions AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM transactions
    WHERE card_last4 = p_card_last4
    AND timestamp >= NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- RPC function: get device transactions in time window
CREATE OR REPLACE FUNCTION get_device_transactions_window(p_device_id VARCHAR, p_hours INTEGER DEFAULT 24)
RETURNS SETOF transactions AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM transactions
    WHERE device_id = p_device_id
    AND timestamp >= NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- RPC function: get driver-passenger pairs
CREATE OR REPLACE FUNCTION get_driver_passenger_pairs(p_days INTEGER DEFAULT 7)
RETURNS TABLE(user_id VARCHAR, driver_id VARCHAR, ride_count BIGINT, total_amount DOUBLE PRECISION) AS $$
BEGIN
    RETURN QUERY
    SELECT t.user_id, t.driver_id, COUNT(*) as ride_count, SUM(t.amount) as total_amount
    FROM transactions t
    WHERE t.timestamp >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY t.user_id, t.driver_id
    HAVING COUNT(*) >= 5
    ORDER BY ride_count DESC;
END;
$$ LANGUAGE plpgsql;

-- RPC function: dashboard metrics
CREATE OR REPLACE FUNCTION get_dashboard_metrics()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_transactions', (SELECT COUNT(*) FROM transactions),
        'processed_transactions', (SELECT COUNT(*) FROM risk_assessments),
        'high_risk_count', (SELECT COUNT(*) FROM risk_assessments WHERE risk_level = 'high_risk'),
        'medium_risk_count', (SELECT COUNT(*) FROM risk_assessments WHERE risk_level = 'medium_risk'),
        'low_risk_count', (SELECT COUNT(*) FROM risk_assessments WHERE risk_level = 'low_risk'),
        'avg_risk_score', (SELECT COALESCE(AVG(risk_score), 0) FROM risk_assessments)
    ) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Enable RLS (Row Level Security) - disabled for this demo
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_models ENABLE ROW LEVEL SECURITY;

-- Allow all access for this demo (use proper policies in production)
CREATE POLICY "Allow all on transactions" ON transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on risk_assessments" ON risk_assessments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on pipeline_state" ON pipeline_state FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on ml_models" ON ml_models FOR ALL USING (true) WITH CHECK (true);
