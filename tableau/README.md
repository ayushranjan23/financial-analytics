# Connecting Tableau to Financial Transaction Analytics Platform

## Overview

This guide explains how to connect Tableau Desktop or Tableau Server to the PostgreSQL database powering the Financial Transaction Analytics Platform. The platform provides pre-built views optimized for Tableau visualizations.

---

## Prerequisites

- Tableau Desktop (2021.1 or later) or Tableau Server
- PostgreSQL database with the Financial Transaction Analytics Platform schema loaded
- Network access to the PostgreSQL instance (port 5432 by default)
- Database user credentials with SELECT permissions on views

---

## Connection Setup

### Step 1: Open Tableau and Create New Data Source

1. Launch Tableau Desktop
2. Click **Data** → **New Data Source**
3. Select **PostgreSQL**

### Step 2: Configure PostgreSQL Connection

Fill in the connection parameters:

| Parameter | Value | Notes |
|---|---|---|
| **Server** | `localhost` or IP | Use `localhost` if running locally |
| **Port** | `5432` | Default PostgreSQL port |
| **Database** | `financial_db` | Database name created by docker-compose |
| **Username** | `postgres` | Default user (customize for production) |
| **Password** | `postgres` | Default password (change in production) |
| **SSL** | Unchecked | Enable for production environments |

### Step 3: Test Connection

Click **Test Connection** to verify:
- ✓ PostgreSQL server is running
- ✓ Network connectivity
- ✓ Credentials are correct

---

## Available Data Sources

The platform provides the following views optimized for Tableau:

### Core Views (Recommended)

#### 1. **v_dashboard_summary**
Single-row view with key metrics for KPI cards.

**Usage:** Executive Summary Dashboard (metric cards, gauges)

**Key Columns:**
- `total_transactions`: Overall transaction count
- `total_customers`: Unique customer count
- `total_volume_usd`: Sum of all transaction amounts
- `anomaly_rate_pct`: Percentage of flagged transactions
- `high_risk_count`: Number of critical anomalies

#### 2. **v_daily_kpi_summary**
Time-series view with daily metrics and anomaly tracking.

**Usage:** Trend analysis, time-series line charts

**Key Columns:**
- `transaction_date`: Date for grouping
- `txn_count`: Daily transaction count
- `daily_volume_usd`: Daily transaction volume
- `anomaly_rate_pct`: Daily anomaly percentage
- `high_risk_txn`: Critical anomalies per day

#### 3. **v_customer_risk_profile**
Customer-level analytics with segmentation and risk scoring.

**Usage:** Customer Insights dashboard, cohort analysis

**Key Columns:**
- `customer_id`: Unique customer identifier
- `customer_segment`: Platinum/Gold/Silver/Bronze
- `lifetime_spend_usd`: Total spend per customer
- `risk_rating`: Low/Medium/High/Critical
- `anomaly_rate_pct`: Customer's personal anomaly rate

#### 4. **v_anomaly_investigation**
Detailed anomaly records with full transaction context.

**Usage:** Fraud Investigation dashboard (drill-down table)

**Key Columns:**
- `transaction_id`: Unique transaction
- `anomaly_score`: Risk score (0-1)
- `anomaly_type`: Type of anomaly detected
- `review_action`: Analyst actions (Approve/Decline/Under Review)
- `customer_total_txns`: Historical context
- `customer_txns_7d`: Recent activity

#### 5. **v_merchant_risk_heatmap**
Merchant category by geography risk analysis.

**Usage:** Heatmap visualization for merchant monitoring

**Key Columns:**
- `merchant_category`: Type of merchant
- `country`: Geographic location
- `anomaly_rate_pct`: Risk percentage
- `risk_level`: Color coding (Red/Orange/Yellow/Green)

#### 6. **v_geographic_heatmap**
Country-level transaction and risk data.

**Usage:** World map visualization, geographic risk analysis

**Key Columns:**
- `country`: ISO country code
- `anomaly_rate_pct`: Country risk rate
- `total_volume_usd`: Country transaction volume
- `risk_intensity`: Visual intensity level

#### 7. **v_hourly_trend_analysis**
Hourly transaction patterns (updated daily).

**Usage:** Operational monitoring dashboard

**Key Columns:**
- `hour_of_day`: Hour of transaction (0-23)
- `transaction_type`: POS/Online/Transfer
- `anomaly_rate_pct`: Hourly risk rate
- `hour_over_hour_change_pct`: Trend compared to previous hour

#### 8. **v_executive_summary_30day**
30-day aggregate metrics for high-level reporting.

**Usage:** Monthly reports, KPI dashboards

**Key Columns:**
- `total_transactions`: 30-day total
- `anomaly_rate_30day_pct`: Monthly anomaly percentage
- `transaction_trend`: Increasing/Stable indicator

### Raw Fact Tables (Advanced Users)

For custom analysis, you can also access raw tables:

| Table | Purpose | Row Count | Primary Key |
|---|---|---|---|
| `fact_transactions` | All transactions | 1000s+ | `transaction_id` |
| `anomaly_flags` | Flagged anomalies | 100s+ | `anomaly_id` |
| `dim_customers` | Customer master | 100s | `customer_id` |

---

## Dashboard Design Recommendations

### Dashboard 1: Executive Summary
**Target Audience:** C-Suite, Business Leaders  
**Refresh Rate:** Daily

**Components:**
1. **Metric Cards** (v_dashboard_summary)
   - Total Transactions (last 24h)
   - Total Volume ($M)
   - Active Customers
   - Anomaly Rate %

2. **Trend Chart** (v_daily_kpi_summary)
   - 30-day transaction volume line chart
   - Overlay: anomaly rate as secondary axis
   - Color: Green (normal) → Red (elevated anomalies)

3. **Risk Gauge** (v_dashboard_summary)
   - Needle gauge showing anomaly rate
   - Red zone: > 10%
   - Yellow zone: 5-10%
   - Green zone: < 5%

4. **KPI Change Indicator**
   - Compare this month vs. last month
   - Show % change in transaction volume

---

### Dashboard 2: Anomaly Investigation
**Target Audience:** Risk Analysts, Fraud Prevention Team  
**Refresh Rate:** Real-time (hourly)

**Components:**
1. **Heatmap** (v_hourly_trend_analysis)
   - Rows: Hours of day (0-23)
   - Columns: Transaction types (POS, Online, Transfer)
   - Cells colored by anomaly rate
   - Color: Green → Yellow → Red

2. **Scatter Plot** (fact_transactions + anomaly_flags join)
   - X-axis: Customer ID
   - Y-axis: Transaction amount
   - Color: Anomaly score (0-1 gradient)
   - Size: Transaction frequency
   - Allows drill-down to anomaly details

3. **Anomaly Details Table** (v_anomaly_investigation)
   - Sortable columns:
     - Transaction ID
     - Customer ID
     - Amount
     - Anomaly Score
     - Anomaly Type
     - Review Status
   - Conditional formatting:
     - Red: Score > 0.8
     - Orange: Score 0.6-0.8
     - Yellow: Score 0.5-0.6

4. **Geographic Anomalies** (v_geographic_heatmap)
   - World map shaded by anomaly rate
   - Click to drill down to country details

5. **Top Merchants at Risk** (v_merchant_risk_heatmap)
   - Bar chart: Top 10 merchant categories by anomaly rate
   - Tooltip shows transaction count, volume, flagged count

---

### Dashboard 3: Customer Insights
**Target Audience:** Business Development, Customer Risk Management  
**Refresh Rate:** Daily

**Components:**
1. **Customer Segmentation Scatter**
   - X-axis: Lifetime spend ($)
   - Y-axis: Anomaly rate (%)
   - Color: Customer segment (Platinum/Gold/Silver/Bronze)
   - Size: Transaction count
   - Allows drill-down to customer profile

2. **Risk Distribution**
   - Pie/Donut chart: Customers by risk rating
     - Low (green)
     - Medium (yellow)
     - High (orange)
     - Critical (red)

3. **Customer Detail Table** (v_customer_risk_profile)
   - Top 100 high-value customers
   - Columns:
     - Customer ID
     - Segment
     - Lifetime Spend
     - Risk Rating
     - Anomaly Rate %
     - Days Active

4. **Geographic Customer Spread** (v_geographic_heatmap)
   - Map showing customer distribution by country
   - Intensity: Number of customers per country

5. **Cohort Analysis**
   - Comparison of high-risk vs. low-risk customers
   - Average transaction size
   - Average transaction frequency
   - Cross-border transaction %

---

## Creating Custom Calculations in Tableau

### Useful Custom Fields

```
// Risk Category (for alerts)
IF [Anomaly Score] > 0.7 THEN "Critical"
ELSEIF [Anomaly Score] > 0.5 THEN "Medium"
ELSE "Low" END

// Business Impact
[Transaction Amount] * [Anomaly Score]

// Anomaly Cost (flagged amount)
IF [Is Flagged] THEN [Transaction Amount] ELSE 0 END

// Days Since First Transaction
DATEDIFF('day', [First Transaction Date], TODAY())

// Expected vs. Actual Volume
[Daily Volume] / [30-Day Average Volume]
```

---

## Performance Tips

### Query Optimization

1. **Use Pre-Built Views**: Views are indexed and optimized. Prefer them over raw tables.
   
2. **Filter by Date**: Always filter by `transaction_date` when using v_daily_kpi_summary
   ```
   WHERE transaction_date >= TODAY() - 90  // Last 90 days
   ```

3. **Limit Raw Table Queries**: If using fact_transactions directly, specify date ranges:
   ```
   WHERE transaction_date >= TODAY() - 30  // Limits to 30 days
   ```

4. **Use Aggregations**: Tableau's aggregate functionality leverages database-level aggregation.

### Refresh Strategy

- **Executive Summary**: Daily (off-peak hours, e.g., 6 AM)
- **Anomaly Investigation**: Every 2 hours
- **Customer Insights**: Daily
- **Real-time Monitors**: Hourly or on-demand

### Dashboard Performance Optimization

1. **Reduce View Count**: Limit each sheet to 1-2 data sources
2. **Use Filters**: Apply filters at the data source level, not visualization level
3. **Limit Rows**: Use TOP N functions or date filters to cap result sets
4. **Cache Results**: Set "Refresh every X hours" for heavy queries

---

## Troubleshooting

### Issue: "Cannot connect to database"
**Solution:**
- Verify PostgreSQL is running: `psql -U postgres -d financial_db`
- Check firewall allows port 5432
- Confirm database name: `CREATE DATABASE financial_db;`

### Issue: "Views not appearing in data source"
**Solution:**
- Refresh Tableau data source
- Views require SELECT privilege: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO tableau_user;`

### Issue: "Dashboard is slow"
**Solution:**
- Use pre-built views instead of raw tables
- Add date filters to limit data
- Increase PostgreSQL work_mem: `SET work_mem = '256MB';`
- Create additional indexes on frequently filtered columns

### Issue: "Anomaly score showing as NULL"
**Solution:**
- Ensure anomaly_detector.py has completed
- Check: `SELECT COUNT(*) FROM anomaly_flags;`
- Re-run: `python src/main.py`

---

## Sample Tableau Expressions

### Top Customers by Risk
```sql
SELECT 
  customer_id,
  SUM(transaction_amount) as spend,
  COUNT(*) as txn_count,
  COUNT(CASE WHEN is_flagged THEN 1 END) as flagged
FROM anomaly_flags
GROUP BY customer_id
ORDER BY flagged DESC
LIMIT 10;
```

### Anomaly Spike Detection
```sql
SELECT 
  transaction_date,
  COUNT(*) as daily_anomalies,
  LAG(COUNT(*)) OVER (ORDER BY transaction_date) as prev_day,
  100.0 * (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY transaction_date)) 
    / LAG(COUNT(*)) OVER (ORDER BY transaction_date) as pct_change
FROM anomaly_flags
WHERE is_flagged = TRUE
GROUP BY transaction_date
ORDER BY pct_change DESC;
```

---

## Security Best Practices

1. **Use Read-Only User**: Create Tableau user with SELECT only privileges
   ```sql
   CREATE USER tableau_user WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE financial_db TO tableau_user;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO tableau_user;
   ```

2. **Enable SSL**: For production Tableau Server
   ```
   SSL: Yes
   SSL Mode: require
   ```

3. **Rotate Credentials**: Change database passwords quarterly

4. **Audit Access**: Monitor Tableau Server access logs

---

## Additional Resources

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Tableau Help**: https://help.tableau.com/
- **Financial Analytics Best Practices**: Internal wiki (link needed)

---

**Last Updated:** January 28, 2026  
**Maintained By:** Data Engineering Team
