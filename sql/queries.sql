-- ============================================================================
-- Financial Transaction Analytics Platform - Analytical Queries
-- Complex queries for business intelligence and decision making
-- ============================================================================

-- ============================================================================
-- Query 1: Daily Transaction Trend with 7-Day Moving Average
-- ============================================================================
-- Shows daily transaction volume with 7-day moving average and YoY comparison
SELECT
    t.transaction_date,
    COUNT(*) as daily_transaction_count,
    SUM(t.amount_in_usd) as daily_volume,
    AVG(t.amount_in_usd) as avg_transaction_amount,
    -- 7-day moving average
    AVG(COUNT(*)) OVER (
        ORDER BY t.transaction_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as ma7_transaction_count,
    AVG(SUM(t.amount_in_usd)) OVER (
        ORDER BY t.transaction_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as ma7_daily_volume,
    -- Day of week for seasonality analysis
    EXTRACT(DOW FROM t.transaction_date) as day_of_week,
    -- Count anomalies
    COUNT(af.anomaly_id) as flagged_transactions,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_percent
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
GROUP BY
    t.transaction_date
ORDER BY
    t.transaction_date DESC;

-- ============================================================================
-- Query 2: Top 10 Customers by Spend and Anomaly Rate
-- ============================================================================
-- Identifies high-value customers and their risk profile
SELECT
    t.customer_id,
    COUNT(*) as transaction_count,
    SUM(t.amount_in_usd) as total_spend,
    AVG(t.amount_in_usd) as avg_transaction_size,
    MAX(t.amount_in_usd) as max_transaction,
    STDDEV(t.amount_in_usd) as spend_stddev,
    -- Anomaly metrics
    COUNT(af.anomaly_id) as flagged_transactions,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_percent,
    AVG(af.anomaly_score) as avg_anomaly_score,
    MAX(af.anomaly_score) as max_anomaly_score,
    -- Customer segmentation
    CASE
        WHEN SUM(t.amount_in_usd) > 50000 THEN 'Platinum'
        WHEN SUM(t.amount_in_usd) > 20000 THEN 'Gold'
        WHEN SUM(t.amount_in_usd) > 5000 THEN 'Silver'
        ELSE 'Bronze'
    END as customer_segment,
    -- Risk score
    CASE
        WHEN COUNT(af.anomaly_id)::FLOAT / COUNT(*) > 0.1 THEN 'High'
        WHEN COUNT(af.anomaly_id)::FLOAT / COUNT(*) > 0.05 THEN 'Medium'
        ELSE 'Low'
    END as risk_category
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
GROUP BY
    t.customer_id
HAVING
    COUNT(*) >= 3  -- Customers with at least 3 transactions
ORDER BY
    total_spend DESC
LIMIT 10;

-- ============================================================================
-- Query 3: Anomaly Breakdown by Hour and Transaction Type
-- ============================================================================
-- Identifies when and how anomalies typically occur
SELECT
    t.hour_of_day,
    t.transaction_type,
    COUNT(*) as total_transactions,
    COUNT(af.anomaly_id) as flagged_count,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_percent,
    AVG(af.anomaly_score) as avg_anomaly_score,
    COUNT(DISTINCT CASE WHEN af.anomaly_score > 0.7 THEN af.transaction_id END) as high_risk_count,
    -- Top merchants in this hour/type combo
    ARRAY_AGG(DISTINCT t.merchant_category) as top_merchants
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id AND af.is_flagged = TRUE
WHERE
    t.hour_of_day IS NOT NULL
    AND t.transaction_type IS NOT NULL
GROUP BY
    t.hour_of_day,
    t.transaction_type
ORDER BY
    anomaly_rate_percent DESC,
    total_transactions DESC;

-- ============================================================================
-- Query 4: Velocity Analysis - Customers with Multiple Transactions in Short Time
-- ============================================================================
-- Detects transaction velocity patterns that may indicate fraud
WITH customer_txn_windows AS (
    SELECT
        t1.customer_id,
        t1.transaction_id as first_txn,
        t2.transaction_id as second_txn,
        COUNT(*) OVER (
            PARTITION BY t1.customer_id
            ORDER BY t2.timestamp
            ROWS BETWEEN CURRENT ROW AND 1 FOLLOWING
        ) as txn_in_window,
        EXTRACT(EPOCH FROM (t2.timestamp - t1.timestamp)) / 60 as minutes_between,
        t1.amount_in_usd as first_amount,
        t2.amount_in_usd as second_amount
    FROM
        fact_transactions t1
    JOIN
        fact_transactions t2 ON t1.customer_id = t2.customer_id
        AND t2.timestamp > t1.timestamp
        AND t2.timestamp <= t1.timestamp + INTERVAL '1 hour'
)
SELECT
    customer_id,
    COUNT(DISTINCT first_txn) as velocity_violations,
    AVG(minutes_between) as avg_minutes_between,
    MIN(minutes_between) as min_minutes_between,
    SUM(first_amount + second_amount) as total_amount_in_window,
    STRING_AGG(DISTINCT CAST(txn_in_window AS VARCHAR), ', ') as transaction_counts
FROM
    customer_txn_windows
WHERE
    txn_in_window >= 3  -- 3+ transactions within 1 hour
GROUP BY
    customer_id
ORDER BY
    velocity_violations DESC
LIMIT 20;

-- ============================================================================
-- Query 5: Geographic Analysis - Cross-Border High-Value Transactions
-- ============================================================================
-- Highlights geographic risk patterns
SELECT
    t.country,
    COUNT(*) as total_transactions,
    COUNT(DISTINCT t.customer_id) as unique_customers,
    SUM(t.amount_in_usd) as total_volume,
    AVG(t.amount_in_usd) as avg_transaction,
    -- Cross-border metrics
    COUNT(CASE WHEN t.is_cross_border = TRUE THEN 1 END) as cross_border_count,
    ROUND(100.0 * COUNT(CASE WHEN t.is_cross_border = TRUE THEN 1 END) / COUNT(*), 2) as cross_border_pct,
    -- High-value metrics
    COUNT(CASE WHEN t.is_high_value = TRUE THEN 1 END) as high_value_count,
    -- Anomaly rate by country
    COUNT(af.anomaly_id) as flagged_transactions,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate_percent,
    -- Risk rank
    RANK() OVER (ORDER BY COUNT(af.anomaly_id) DESC) as risk_rank
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
WHERE
    t.country IS NOT NULL
GROUP BY
    t.country
ORDER BY
    anomaly_rate_percent DESC;

-- ============================================================================
-- Query 6: Merchant Category Risk Profile
-- ============================================================================
-- Analyzes which merchant categories have highest fraud/anomaly rates
SELECT
    t.merchant_category,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT t.customer_id) as unique_merchants,
    SUM(t.amount_in_usd) as total_volume,
    AVG(t.amount_in_usd) as avg_amount,
    STDDEV(t.amount_in_usd) as amount_stddev,
    -- Anomaly metrics
    COUNT(af.anomaly_id) as flagged_count,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate,
    COUNT(CASE WHEN af.anomaly_score > 0.7 THEN 1 END) as high_risk_count,
    AVG(af.anomaly_score) as avg_anomaly_score,
    -- Business metrics
    COUNT(CASE WHEN t.transaction_type = 'POS' THEN 1 END) as pos_count,
    COUNT(CASE WHEN t.transaction_type = 'Online' THEN 1 END) as online_count,
    COUNT(CASE WHEN t.transaction_type = 'Transfer' THEN 1 END) as transfer_count
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
WHERE
    t.merchant_category IS NOT NULL
GROUP BY
    t.merchant_category
HAVING
    COUNT(*) >= 10  -- Categories with at least 10 transactions
ORDER BY
    anomaly_rate DESC;

-- ============================================================================
-- Query 7: Time-Based Anomaly Patterns (Weekend vs Weekday)
-- ============================================================================
-- Identifies temporal patterns in transaction behavior
SELECT
    CASE
        WHEN t.is_weekend = TRUE THEN 'Weekend'
        ELSE 'Weekday'
    END as day_type,
    CASE
        WHEN t.hour_of_day BETWEEN 6 AND 11 THEN 'Morning (6-11)'
        WHEN t.hour_of_day BETWEEN 12 AND 17 THEN 'Afternoon (12-17)'
        WHEN t.hour_of_day BETWEEN 18 AND 23 THEN 'Evening (18-23)'
        ELSE 'Night (0-5)'
    END as time_period,
    COUNT(*) as transaction_count,
    SUM(t.amount_in_usd) as total_volume,
    AVG(t.amount_in_usd) as avg_amount,
    COUNT(af.anomaly_id) as flagged_count,
    ROUND(100.0 * COUNT(af.anomaly_id) / COUNT(*), 2) as anomaly_rate,
    STRING_AGG(DISTINCT t.transaction_type, ', ') as transaction_types
FROM
    fact_transactions t
LEFT JOIN
    anomaly_flags af ON t.transaction_id = af.transaction_id
GROUP BY
    day_type,
    time_period
ORDER BY
    anomaly_rate DESC;

-- ============================================================================
-- Query 8: Most Recent High-Risk Transactions (Last 7 Days)
-- ============================================================================
-- Operational query for daily monitoring
SELECT
    af.transaction_id,
    af.customer_id,
    af.transaction_amount,
    af.anomaly_score,
    af.anomaly_type,
    af.rules_triggered,
    af.detected_at,
    af.reviewed,
    t.transaction_type,
    t.merchant_category,
    t.country,
    af.review_action,
    af.review_notes
FROM
    anomaly_flags af
JOIN
    fact_transactions t ON af.transaction_id = t.transaction_id
WHERE
    af.detected_at >= CURRENT_DATE - INTERVAL '7 days'
    AND af.is_flagged = TRUE
    AND af.anomaly_score > 0.7
ORDER BY
    af.anomaly_score DESC,
    af.detected_at DESC
LIMIT 100;
