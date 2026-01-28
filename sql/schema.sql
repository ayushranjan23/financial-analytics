-- ============================================================================
-- Financial Transaction Analytics Platform - Database Schema
-- PostgreSQL DDL for creating fact and dimension tables
-- ============================================================================

-- Drop existing tables if they exist (for fresh setup)
DROP TABLE IF EXISTS anomaly_flags CASCADE;
DROP TABLE IF EXISTS fact_transactions CASCADE;
DROP TABLE IF EXISTS dim_customers CASCADE;

-- ============================================================================
-- Dimension: Customers
-- ============================================================================
CREATE TABLE dim_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_count INT DEFAULT 0,
    total_spend NUMERIC(15, 2) DEFAULT 0,
    customer_segment VARCHAR(50),
    risk_score NUMERIC(3, 2) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_customers_first_seen ON dim_customers(first_seen);
CREATE INDEX idx_dim_customers_risk_score ON dim_customers(risk_score);

-- ============================================================================
-- Fact: Transactions
-- ============================================================================
CREATE TABLE fact_transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    transaction_date DATE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    amount_in_usd NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3),
    transaction_type VARCHAR(50),
    merchant_category VARCHAR(100),
    country VARCHAR(2),
    hour_of_day INT,
    day_of_week INT,
    month INT,
    day_of_month INT,
    is_high_value BOOLEAN DEFAULT FALSE,
    is_cross_border BOOLEAN DEFAULT FALSE,
    is_weekend BOOLEAN DEFAULT FALSE,
    customer_transaction_count_7d INT DEFAULT 0,
    merchant_category_lower VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id) ON DELETE CASCADE
);

-- Indexes for query performance
CREATE INDEX idx_transactions_customer_id ON fact_transactions(customer_id);
CREATE INDEX idx_transactions_timestamp ON fact_transactions(timestamp);
CREATE INDEX idx_transactions_transaction_date ON fact_transactions(transaction_date);
CREATE INDEX idx_transactions_amount ON fact_transactions(amount_in_usd);
CREATE INDEX idx_transactions_country ON fact_transactions(country);
CREATE INDEX idx_transactions_transaction_type ON fact_transactions(transaction_type);
CREATE INDEX idx_transactions_merchant_category ON fact_transactions(merchant_category);
CREATE INDEX idx_transactions_is_high_value ON fact_transactions(is_high_value);
CREATE INDEX idx_transactions_is_cross_border ON fact_transactions(is_cross_border);

-- ============================================================================
-- Fact: Anomaly Flags
-- ============================================================================
CREATE TABLE anomaly_flags (
    anomaly_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    transaction_timestamp TIMESTAMP NOT NULL,
    transaction_amount NUMERIC(12, 2) NOT NULL,
    anomaly_type VARCHAR(100),
    anomaly_score NUMERIC(3, 2),
    rules_triggered INT DEFAULT 0,
    is_flagged BOOLEAN DEFAULT TRUE,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE,
    review_action VARCHAR(50),
    review_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES fact_transactions(transaction_id) ON DELETE CASCADE
);

CREATE INDEX idx_anomaly_flags_transaction_id ON anomaly_flags(transaction_id);
CREATE INDEX idx_anomaly_flags_customer_id ON anomaly_flags(customer_id);
CREATE INDEX idx_anomaly_flags_detected_at ON anomaly_flags(detected_at);
CREATE INDEX idx_anomaly_flags_anomaly_score ON anomaly_flags(anomaly_score);
CREATE INDEX idx_anomaly_flags_reviewed ON anomaly_flags(reviewed);

-- ============================================================================
-- Materialized View: Daily Statistics (for performance)
-- ============================================================================
CREATE TABLE daily_statistics (
    statistic_date DATE PRIMARY KEY,
    transaction_count INT,
    total_volume NUMERIC(15, 2),
    avg_transaction NUMERIC(12, 2),
    max_transaction NUMERIC(12, 2),
    min_transaction NUMERIC(12, 2),
    unique_customers INT,
    high_value_count INT,
    anomaly_count INT,
    anomaly_rate NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daily_stats_date ON daily_statistics(statistic_date);

-- ============================================================================
-- Transaction Metadata
-- ============================================================================
COMMENT ON TABLE fact_transactions IS
'Core fact table for all transactions. Contains processed, enriched transaction data.';

COMMENT ON TABLE dim_customers IS
'Customer dimension table. One row per unique customer with aggregate metrics.';

COMMENT ON TABLE anomaly_flags IS
'Anomaly detection results. Tracks flagged transactions and their risk scores.';

COMMENT ON COLUMN fact_transactions.amount_in_usd IS
'Transaction amount normalized to USD for cross-currency analysis.';

COMMENT ON COLUMN fact_transactions.customer_transaction_count_7d IS
'Number of transactions from this customer in the 7 days preceding this transaction.';

COMMENT ON COLUMN anomaly_flags.anomaly_score IS
'Composite anomaly score (0.0 to 1.0). Score > 0.7 indicates high risk.';

-- ============================================================================
-- Grant Permissions (for application user)
-- ============================================================================
-- Uncomment and modify for production:
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ============================================================================
-- Schema Version
-- ============================================================================
CREATE TABLE schema_version (
    version_id SERIAL PRIMARY KEY,
    version_number VARCHAR(20),
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version_number, description)
VALUES ('1.0.0', 'Initial schema with transactions, customers, and anomalies');
