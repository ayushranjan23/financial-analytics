# Financial Transaction Analytics Platform

## Project Overview

This is a **Financial Transaction Analytics Platform** designed to ingest, process, and analyze transaction data at scale. The platform implements sophisticated anomaly detection algorithms and provides comprehensive analytical dashboards for fraud prevention, customer insights, and operational monitoring.

### Business Value

- **Fraud Detection:** Real-time anomaly detection catches suspicious transactions before they harm customers
- **Risk Management:** Identifies unusual customer behavior patterns and cross-border risks
- **Business Intelligence:** Comprehensive dashboards for executives to monitor transaction trends and KPIs
- **Scalability:** Built with modern data engineering practices to handle millions of daily transactions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                        │
│              (CSV, APIs, Real-time Streams)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PYTHON ETL PIPELINE                            │
│  • Data Validation    • Cleaning    • Enrichment    • Feature    │
│    Engineering                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  • Staging Tables    • Fact Tables    • Dimension Tables        │
│  • Anomaly Tables    • Optimized for Analytics                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
        Tableau       Python Reports    SQL Queries
      (Dashboards)   (Alerts/Export)   (Ad-hoc Analysis)
```

### Key Components

1. **Data Ingestion Layer (`src/data_ingestion.py`)**: Reads raw CSV files with validation and error handling
2. **ETL Pipeline (`src/data_processor.py`)**: Cleans messy data, handles missing values, engineers features
3. **Anomaly Detection Engine (`src/anomaly_detector.py`)**: Multi-method anomaly scoring (statistical + rule-based)
4. **Database Layer (`src/database.py`)**: Efficient bulk inserts and analytical queries
5. **Orchestration (`src/main.py`)**: Coordinates the entire pipeline execution
6. **SQL Analytics (`sql/queries.sql`)**: Window functions, CTEs, and performance-optimized queries

---

## Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.11+ (if running without Docker)
- PostgreSQL 15+ (if running without Docker)
- Git

### Option 1: Run with Docker (Recommended)

```bash
# Clone the repository
cd financial_transaction_platform

# Start the entire stack (PostgreSQL + Application)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

The application will:
1. Start PostgreSQL on port 5432
2. Create the database schema automatically
3. Ingest sample transaction data
4. Run anomaly detection
5. Generate analytical views for Tableau

### Option 2: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your PostgreSQL connection details

# Run the pipeline
python src/main.py
```

### Option 3: Run Individual Components

```bash
# Only ingest and process data
python -c "from src.main import run_data_pipeline; run_data_pipeline()"

# Generate anomaly detection report
python -c "from src.main import run_anomaly_detection; run_anomaly_detection()"

# Execute specific SQL queries
psql -d financial_db -f sql/queries.sql
```

---

## Anomaly Detection Methodology

The platform employs a **multi-layered anomaly detection approach**:

### 1. Statistical Outlier Detection (Z-Score Method)
- **Threshold:** Z-score > 3 (99.7th percentile)
- **Application:** Detects unusually large transaction amounts
- **Formula:** $Z = \frac{X - \mu}{\sigma}$
- **Advantage:** Fast, interpretable, suitable for known distributions

### 2. Interquartile Range (IQR) Method
- **Threshold:** Values > Q3 + 1.5×IQR
- **Application:** Robust to outliers in the training data
- **Advantage:** Non-parametric, doesn't assume normality

### 3. Rule-Based Anomaly Detection
Business rules capture domain knowledge:
- **High-value threshold:** Transactions > $10,000 flagged for review
- **Velocity anomaly:** >5 transactions from same customer within 1 hour
- **Geographic anomaly:** Cross-border transactions with high amounts
- **Time-based anomaly:** Transactions outside business hours from corporate accounts

### 4. Anomaly Score Calculation
```
Total Anomaly Score = (Statistical_Score × 0.4) + (Rule_Score × 0.6)
- Score Range: 0 to 1
- Score > 0.7: High risk (recommended for manual review)
- Score > 0.5: Medium risk (monitor)
- Score ≤ 0.5: Low risk (proceed normally)
```

### Visualization Example

```
Time-Series Chart: Daily Transaction Volume with Anomaly Annotations
┌─────────────────────────────────────────────────────────────┐
│ Volume ($M)                                                  │
│ 50 ├─────────────────────────────────────────              │
│    │         ╱╲                    🚨 High Anomaly         │
│ 40 ├────────╱  ╲──────────────────────                     │
│    │       ╱    ╲        🚨 🚨                             │
│ 30 ├──────╱      ╲───────────────────                      │
│    │     ╱        ╲                                         │
│ 20 ├────╱──────────╲──────────────────                     │
│    │   ╱            ╲                                       │
│ 10 ├──╱──────────────╲────────────────                     │
│    └─────────────────────────────────────────┘
│      Mon Tue Wed Thu Fri Sat Sun Mon Tue Wed
│
Legend:
  ─ Normal Transactions      🚨 Flagged Anomalies
  ╱╲ Volume Trend           📊 Moving Average (7-day)
```

---

## Project Structure

```
financial_transaction_platform/
├── data/
│   ├── raw/                      # Raw CSV files from data sources
│   │   └── sample_transactions.csv
│   └── processed/                # Cleaned, validated datasets
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration management (Pydantic)
│   ├── data_ingestion.py         # CSV reading with validation
│   ├── data_processor.py         # Pandas-based ETL transformations
│   ├── database.py               # PostgreSQL operations (SQLAlchemy)
│   ├── anomaly_detector.py       # Statistical & rule-based detection
│   └── main.py                   # Pipeline orchestration
│
├── sql/
│   ├── schema.sql                # DDL: fact/dimension tables, indexes
│   ├── queries.sql               # Analytical queries (window functions)
│   └── views.sql                 # Materialized views for Tableau
│
├── tableau/
│   └── README.md                 # Tableau connection guide & dashboard design
│
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py          # Unit tests (pytest)
│
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── Dockerfile                    # Python 3.11 multi-stage build
├── docker-compose.yml            # PostgreSQL + App services
└── README.md                     # This file
```

---

## Key Features & Implementation Details

### 1. Data Quality & Validation

**Input Data Validation** (`src/data_ingestion.py`):
- Required columns check
- Data type validation
- Value range checks
- Duplicate detection

**Output Data Validation** (`src/data_processor.py`):
- No negative amounts
- Dates within valid range
- Required fields not null
- Cardinality validation

### 2. Feature Engineering

Enrichment pipeline creates actionable features:
- `hour_of_day`: Transaction hour (0-23) for time-based patterns
- `day_of_week`: Day of week for weekly seasonality
- `amount_in_usd`: Standardized currency conversion
- `customer_transaction_count_7d`: 7-day rolling customer velocity
- `merchant_category_encoded`: Categorical encoding for ML readiness

### 3. Database Optimization

**Indexes** (for query performance):
```sql
CREATE INDEX idx_transactions_customer_id ON fact_transactions(customer_id);
CREATE INDEX idx_transactions_timestamp ON fact_transactions(transaction_date);
CREATE INDEX idx_anomalies_flag ON anomaly_flags(is_flagged);
```

**Partitioning**: Transactions table partitioned by month for fast queries

**Bulk Inserts**: Uses SQLAlchemy's multi-method for efficient batch inserts (10K rows/second)

### 4. Error Handling & Logging

Every module includes:
- Try/except blocks with specific exception types
- Structured logging (JSON format for ELK/Splunk compatibility)
- Graceful degradation (skip bad records, continue processing)
- Retry logic for network operations

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Starting ETL pipeline")
logger.error("Database connection failed", exc_info=True)
```

### 5. Security Best Practices

- No hardcoded credentials (use `.env` with `python-dotenv`)
- Parameterized SQL queries (prevent SQL injection)
- Environment-based configuration (dev/staging/prod)
- Database user with minimal required permissions

---

## Running the Anomaly Detection Example

### Sample Output

```
2026-01-28 14:32:15 - INFO - Processing 1,247 transactions
2026-01-28 14:32:18 - INFO - Statistical outliers detected: 42 (Z-score > 3)
2026-01-28 14:32:20 - INFO - Rule-based anomalies detected: 156
2026-01-28 14:32:22 - INFO - Combined anomaly score calculated
2026-01-28 14:32:23 - INFO - Inserted 198 flagged transactions into anomaly_flags table
2026-01-28 14:32:24 - INFO - Pipeline completed in 9.23 seconds
```

### Flagged Transaction Example

| Transaction ID | Customer ID | Amount | Type | Anomaly Type | Score | Action |
|---|---|---|---|---|---|---|
| TXN_2847392 | CUST_00421 | $15,430 | Cross-Border | High-Value + Geographic | 0.89 | Manual Review |
| TXN_2847401 | CUST_00518 | $890 | Online | Velocity (6 in 1h) | 0.72 | Monitor |
| TXN_2847415 | CUST_00105 | $340 | POS | Statistical Outlier | 0.61 | Alert |

---

## Tableau Dashboard Design

### Dashboard 1: Executive Summary
- **Metric Cards:** Daily transaction count, volume, anomaly rate
- **Trend Chart:** 30-day transaction volume with 7-day MA
- **Risk Gauge:** Proportion of flagged transactions

### Dashboard 2: Anomaly Investigation
- **Heatmap:** Anomalies by hour of day × transaction type
- **Scatter Plot:** Amount vs. Customer ID (colored by anomaly score)
- **Top Anomalies Table:** Latest high-risk transactions with detail drill-down

### Dashboard 3: Customer Insights
- **Segmentation:** Customer lifetime value vs. anomaly frequency
- **Geo-Visualization:** Transaction heat map by country
- **Cohort Analysis:** Behavior comparison between high-risk and normal customers

---

## Performance Benchmarks

| Operation | Volume | Time | Throughput |
|---|---|---|---|
| Data Ingestion | 10,000 rows | 0.8s | 12.5K rows/s |
| Data Processing | 10,000 rows | 1.2s | 8.3K rows/s |
| Anomaly Detection | 10,000 rows | 2.1s | 4.8K rows/s |
| Database Insert | 10,000 rows | 1.5s | 6.7K rows/s |
| End-to-End Pipeline | 10,000 rows | 5.6s | 1.8K rows/s |

---

## Development & Testing

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_pipeline.py::test_anomaly_detection_catches_outliers -v

# Run with verbose output
pytest tests/ -vv -s
```

### Test Coverage

- `test_data_ingestion_success()`: Validates CSV reading
- `test_data_processor_handles_missing_values()`: Tests null handling
- `test_anomaly_detector_catches_known_outlier()`: Ensures detection works
- `test_database_connection()`: PostgreSQL connectivity
- `test_feature_engineering_creates_expected_columns()`: Output schema validation

---

## Troubleshooting

### Issue: PostgreSQL Connection Failed
```
FileNotFoundError: postgresql://user:pass@localhost/financial_db
```
**Solution:** Ensure PostgreSQL is running and `.env` has correct DATABASE_URL

### Issue: Memory Error with Large CSV
```
MemoryError: Unable to allocate 8.45 GB for an array
```
**Solution:** Process in chunks using `chunksize` parameter in `pd.read_csv()`

### Issue: Anomaly Detection Too Slow
```
Processing 1M rows takes > 5 minutes
```
**Solution:** Use NumPy vectorization, increase `batch_size` in anomaly detection

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Add tests for new functionality
3. Ensure all tests pass: `pytest`
4. Submit a pull request

---

## License

Proprietary - Financial Analytics Platform © 2026

---

## Support & Documentation

- **Email:** data-eng-team@company.com
- **Docs:** See `sql/` and `tableau/` directories for detailed specs
- **Issues:** Report bugs via internal ticketing system

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | Jan 28, 2026 | Initial release - Core ETL, Anomaly Detection, Tableau Integration |
| 0.9.0 | Jan 21, 2026 | Beta release - Database schema finalized |
| 0.1.0 | Jan 10, 2026 | Alpha - Project scaffolding |

---

**Last Updated:** January 28, 2026  
**Maintained By:** Senior Data Engineering Team
