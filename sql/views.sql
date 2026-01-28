-- ============================================================================
-- Financial Transaction Analytics Platform - Database Views
-- Materialized and regular views for Tableau and reporting
-- ============================================================================

-- ============================================================================
-- View 1: Dashboard Summary (For Tableau Executive Dashboard)
-- ============================================================================
CREATE OR REPLACE VIEW v_dashboard_summary AS
SELECT
    CAST(CURRENT_DATE AS DATE) as dashboard_date,
    (SELECT COUNT(*) FROM fact_transactions) as total_transactions,
    (SELECT COUNT(DISTINCT customer_id) FROM fact_transactions) as total_customers,
    (SELECT SUM(amount_in_usd) FROM fact_transactions) as total_volume_usd,
    (SELECT AVG(amount_in_usd) FROM fact_transactions) as avg_transaction_usd,
    (SELECT COUNT(*) FROM anomaly_flags WHERE is_flagged = TRUE) as total_flagged,
    (SELECT ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM fact_transactions), 0), 2)
     FROM anomaly_flags WHERE is_flagged = TRUE) as anomaly_rate_pct,
    (SELECT COUNT(*) FROM anomaly_flags WHERE anomaly_score > 0.7) as high_risk_count,
    (SELECT COUNT(DISTINCT customer_id) FROM anomaly_flags WHERE is_flagged = TRUE) as at_risk_customers;

-- ============================================================================
-- View 2: Daily KPI Summary (Time-Series for Dashboard)
-- ============================================================================
CREATE OR REPLACE VIEW v_daily_kpi_summary AS
SELECT
    t.transaction_date,
    COUNT(*) as txn_count,
    COUNT(DISTINCT t.customer_id) as unique_customers,
    SUM(t.amount_in_usd) as daily_volume_usd,
    AVG(t.amount_in_usd) as avg_txn_usd,
    MAX(t.amount_in_usd) as max_txn_usd,
    MIN(t.amount_in_usd) as min_txn_usd,
    COUNT(CASE WHEN t.is_high_value = TRUE THEN 1 END) as high_value_txn,
    COUNT(CASE WHEN t.is_cross_border = TRUE THEN 1 END) as cross_border_txn,
    COUNT(af.anomaly_id) as flagged_txn,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_pct,
    COUNT(CASE WHEN af.anomaly_score > 0.7 THEN 1 END) as high_risk_txn
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
GROUP BY
    t.transaction_date
ORDER BY
    t.transaction_date DESC;

-- ============================================================================
-- View 3: Customer Segmentation and Risk (For Customer Insights Dashboard)
-- ============================================================================
CREATE OR REPLACE VIEW v_customer_risk_profile AS
SELECT
    t.customer_id,
    COUNT(*) as lifetime_transactions,
    COUNT(DISTINCT t.transaction_date) as active_days,
    SUM(t.amount_in_usd) as lifetime_spend_usd,
    AVG(t.amount_in_usd) as avg_transaction_usd,
    MAX(t.amount_in_usd) as max_transaction_usd,
    MIN(t.transaction_date) as first_transaction_date,
    MAX(t.transaction_date) as last_transaction_date,
    -- Segmentation
    CASE
        WHEN SUM(t.amount_in_usd) > 50000 THEN 'Platinum'
        WHEN SUM(t.amount_in_usd) > 20000 THEN 'Gold'
        WHEN SUM(t.amount_in_usd) > 5000 THEN 'Silver'
        ELSE 'Bronze'
    END as customer_segment,
    -- Risk metrics
    COUNT(af.anomaly_id) as flagged_transactions,
    COUNT(CASE WHEN af.anomaly_score > 0.7 THEN 1 END) as high_risk_flags,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_pct,
    AVG(af.anomaly_score) as avg_anomaly_score,
    -- Risk rating
    CASE
        WHEN COUNT(af.anomaly_id)::FLOAT / COUNT(*) > 0.15 THEN 'Critical'
        WHEN COUNT(af.anomaly_id)::FLOAT / COUNT(*) > 0.10 THEN 'High'
        WHEN COUNT(af.anomaly_id)::FLOAT / COUNT(*) > 0.05 THEN 'Medium'
        ELSE 'Low'
    END as risk_rating,
    -- Geographic diversity
    COUNT(DISTINCT t.country) as countries_active,
    COUNT(CASE WHEN t.is_cross_border = TRUE THEN 1 END) as cross_border_transactions
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
GROUP BY
    t.customer_id;

-- ============================================================================
-- View 4: Anomaly Investigation Details (For Fraud Investigation Dashboard)
-- ============================================================================
CREATE OR REPLACE VIEW v_anomaly_investigation AS
SELECT
    af.anomaly_id,
    af.transaction_id,
    af.customer_id,
    af.transaction_timestamp,
    af.transaction_amount,
    af.anomaly_score,
    af.anomaly_type,
    af.rules_triggered,
    af.detected_at,
    af.reviewed,
    af.review_action,
    t.transaction_type,
    t.merchant_category,
    t.country,
    t.hour_of_day,
    t.day_of_week,
    t.is_high_value,
    t.is_cross_border,
    -- Customer context
    (SELECT COUNT(*) FROM fact_transactions WHERE customer_id = af.customer_id) as customer_total_txns,
    (SELECT AVG(amount_in_usd) FROM fact_transactions WHERE customer_id = af.customer_id) as customer_avg_amount,
    (SELECT COUNT(*)
     FROM fact_transactions
     WHERE customer_id = af.customer_id
       AND transaction_date >= af.transaction_timestamp::DATE - INTERVAL '7 days'
    ) as customer_txns_7d,
    -- Days since first transaction
    (SELECT EXTRACT(DAY FROM CURRENT_TIMESTAMP - MIN(timestamp))
     FROM fact_transactions WHERE customer_id = af.customer_id) as customer_age_days
FROM
    anomaly_flags af
LEFT JOIN
    fact_transactions t ON af.transaction_id = t.transaction_id;

-- ============================================================================
-- View 5: Merchant Risk Heatmap (For Merchant Monitoring)
-- ============================================================================
CREATE OR REPLACE VIEW v_merchant_risk_heatmap AS
SELECT
    t.merchant_category,
    t.country,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT t.customer_id) as unique_customers,
    SUM(t.amount_in_usd) as total_volume_usd,
    AVG(t.amount_in_usd) as avg_amount_usd,
    COUNT(af.anomaly_id) as flagged_count,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_pct,
    AVG(af.anomaly_score) as avg_anomaly_score,
    -- Risk color coding (for visualization)
    CASE
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 15 THEN 'Red'
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 10 THEN 'Orange'
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 5 THEN 'Yellow'
        ELSE 'Green'
    END as risk_level
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
WHERE
    t.merchant_category IS NOT NULL
    AND t.country IS NOT NULL
GROUP BY
    t.merchant_category,
    t.country
HAVING
    COUNT(*) >= 5
ORDER BY
    anomaly_rate_pct DESC;

-- ============================================================================
-- View 6: Hourly Trend Analysis (For Operational Monitoring)
-- ============================================================================
CREATE OR REPLACE VIEW v_hourly_trend_analysis AS
SELECT
    CAST(CURRENT_DATE AS DATE) as analysis_date,
    t.hour_of_day,
    t.transaction_type,
    COUNT(*) as txn_count,
    SUM(t.amount_in_usd) as volume_usd,
    AVG(t.amount_in_usd) as avg_amount_usd,
    COUNT(DISTINCT t.customer_id) as unique_customers,
    COUNT(af.anomaly_id) as flagged_count,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_pct,
    MAX(af.anomaly_score) as max_anomaly_score,
    -- Expected vs actual
    LAG(COUNT(*)) OVER (PARTITION BY t.transaction_type ORDER BY t.hour_of_day) as prev_hour_txn_count,
    ROUND(100.0 * (COUNT(*) - LAG(COUNT(*)) OVER (PARTITION BY t.transaction_type ORDER BY t.hour_of_day))
          / NULLIF(LAG(COUNT(*)) OVER (PARTITION BY t.transaction_type ORDER BY t.hour_of_day), 0), 2) as hour_over_hour_change_pct
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
WHERE
    t.transaction_date = CAST(CURRENT_DATE AS DATE)
GROUP BY
    t.hour_of_day,
    t.transaction_type
ORDER BY
    t.hour_of_day,
    t.transaction_type;

-- ============================================================================
-- View 7: Geographic Heat Map (World Map Visualization)
-- ============================================================================
CREATE OR REPLACE VIEW v_geographic_heatmap AS
SELECT
    t.country,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT t.customer_id) as unique_customers,
    SUM(t.amount_in_usd) as total_volume_usd,
    AVG(t.amount_in_usd) as avg_transaction_usd,
    COUNT(af.anomaly_id) as flagged_transactions,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_pct,
    -- Intensity for heat map coloring
    CASE
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 20 THEN 'Critical'
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 15 THEN 'High'
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 10 THEN 'Elevated'
        WHEN ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) > 5 THEN 'Moderate'
        ELSE 'Low'
    END as risk_intensity
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
WHERE
    t.country IS NOT NULL
GROUP BY
    t.country
ORDER BY
    anomaly_rate_pct DESC;

-- ============================================================================
-- View 8: Executive Summary Report (30-Day Trends)
-- ============================================================================
CREATE OR REPLACE VIEW v_executive_summary_30day AS
WITH daily_data AS (
    SELECT
        t.transaction_date,
        COUNT(*) as daily_txns,
        SUM(t.amount_in_usd) as daily_volume,
        COUNT(af.anomaly_id) as daily_flagged
    FROM
        fact_transactions t
    LEFT JOIN
        anomaly_flags af ON t.transaction_id = af.transaction_id
    WHERE
        t.transaction_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY
        t.transaction_date
)
SELECT
    MIN(d.transaction_date) as period_start,
    MAX(d.transaction_date) as period_end,
    COUNT(*) as days_with_data,
    SUM(d.daily_txns) as total_transactions,
    ROUND(AVG(d.daily_txns), 0) as avg_daily_transactions,
    MAX(d.daily_txns) as peak_daily_transactions,
    MIN(d.daily_txns) as min_daily_transactions,
    SUM(d.daily_volume) as total_volume_usd,
    ROUND(AVG(d.daily_volume), 2) as avg_daily_volume_usd,
    SUM(d.daily_flagged) as total_flagged_30day,
    ROUND(100.0 * SUM(d.daily_flagged) / SUM(d.daily_txns), 2) as anomaly_rate_30day_pct,
    -- Trend indicator
    CASE
        WHEN SUM(d.daily_txns) > (SELECT SUM(COUNT(*))
                                   FROM fact_transactions
                                   WHERE transaction_date BETWEEN CURRENT_DATE - INTERVAL '60 days' AND CURRENT_DATE - INTERVAL '30 days'
                                   GROUP BY transaction_date)
        THEN 'Increasing'
        ELSE 'Stable'
    END as transaction_trend
FROM
    daily_data d;

-- ============================================================================
-- Indexes for View Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_anomaly_flags_score_reviewed ON anomaly_flags(anomaly_score, reviewed);
CREATE INDEX IF NOT EXISTS idx_fact_transactions_date_customer ON fact_transactions(transaction_date, customer_id);
