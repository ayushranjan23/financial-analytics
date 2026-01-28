"""
Main orchestration script for Financial Transaction Analytics Platform.
Coordinates the entire ETL pipeline: ingestion -> processing -> DB -> anomaly detection.
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from data_ingestion import DataIngestor
from data_processor import DataProcessor
from database import DatabaseManager
from anomaly_detector import AnomalyDetector

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)

logger = logging.getLogger(__name__)


def setup_database() -> DatabaseManager:
    """Initialize database and create schema."""
    logger.info("=" * 60)
    logger.info("STEP 1: DATABASE SETUP")
    logger.info("=" * 60)

    db_manager = DatabaseManager()

    # Test connection
    if not db_manager.test_connection():
        logger.error("Cannot connect to database. Check DATABASE_URL in .env")
        raise ConnectionError("Database connection failed")

    # Create schema
    if not db_manager.create_tables():
        logger.error("Failed to create database schema")
        # Continue anyway - tables might already exist

    return db_manager


def run_data_ingestion() -> object:
    """Read and validate raw data."""
    logger.info("=" * 60)
    logger.info("STEP 2: DATA INGESTION")
    logger.info("=" * 60)

    ingestor = DataIngestor()
    df_raw = ingestor.validate_and_get_data()

    logger.info(f"Ingested {len(df_raw)} raw transaction records")
    logger.info(f"Columns: {list(df_raw.columns)}")

    return df_raw


def run_data_processing(df_raw: object) -> object:
    """Clean, transform, and enrich data."""
    logger.info("=" * 60)
    logger.info("STEP 3: DATA PROCESSING & FEATURE ENGINEERING")
    logger.info("=" * 60)

    processor = DataProcessor()
    df_processed = processor.process_pipeline(df_raw)

    logger.info(f"Processed {len(df_processed)} records")
    logger.info(f"Created {df_processed.shape[1]} features")

    # Show sample processed record
    logger.debug(f"Sample processed record:\n{df_processed.iloc[0]}")

    return df_processed


def run_database_insert(db_manager: object, df_processed: object) -> None:
    """Insert processed data into database."""
    logger.info("=" * 60)
    logger.info("STEP 4: DATABASE INSERTION")
    logger.info("=" * 60)

    success, rows_inserted = db_manager.insert_dataframe(
        table_name='transactions',
        df=df_processed,
        if_exists='append'
    )

    if not success:
        logger.error("Database insert failed")
        raise Exception("Failed to insert data into database")

    logger.info(f"Successfully inserted {rows_inserted} transactions")

    # Verify insert
    count = db_manager.get_table_count('transactions')
    logger.info(f"Total transactions in database: {count}")


def run_anomaly_detection(db_manager: object, df_processed: object) -> object:
    """Detect anomalies and insert flagged transactions."""
    logger.info("=" * 60)
    logger.info("STEP 5: ANOMALY DETECTION")
    logger.info("=" * 60)

    detector = AnomalyDetector(
        zscore_threshold=settings.zscore_threshold,
        iqr_multiplier=settings.iqr_multiplier
    )

    # Mark anomalies
    df_with_anomalies = detector.mark_anomalies(df_processed)

    # Statistics
    flagged_count = df_with_anomalies['is_flagged'].sum()
    high_risk = (df_with_anomalies['anomaly_score'] > 0.7).sum()
    medium_risk = (
        (df_with_anomalies['anomaly_score'] > 0.5) &
        (df_with_anomalies['anomaly_score'] <= 0.7)
    ).sum()

    logger.info(f"Anomaly Detection Summary:")
    logger.info(f"  - High Risk (score > 0.7): {high_risk}")
    logger.info(f"  - Medium Risk (0.5-0.7): {medium_risk}")
    logger.info(f"  - Total Flagged: {flagged_count}")
    logger.info(f"  - Anomaly Rate: {(flagged_count / len(df_with_anomalies) * 100):.2f}%")

    # Extract flagged transactions for separate table
    if flagged_count > 0:
        df_flagged = df_with_anomalies[df_with_anomalies['is_flagged']].copy()

        # Prepare anomaly records
        df_anomalies = df_flagged[[
            'transaction_id',
            'customer_id',
            'timestamp',
            'amount_in_usd',
            'anomaly_score',
            'rules_triggered',
            'is_flagged'
        ]].copy()

        df_anomalies.rename(columns={
            'amount_in_usd': 'transaction_amount',
            'timestamp': 'transaction_timestamp'
        }, inplace=True)

        df_anomalies['detected_at'] = datetime.now()
        df_anomalies['anomaly_type'] = df_anomalies.apply(
            lambda row: 'HIGH_VALUE' if row['anomaly_score'] > 0.7 else 'MEDIUM_RISK',
            axis=1
        )

        # Insert into anomaly_flags table
        success, rows = db_manager.insert_dataframe(
            table_name='anomaly_flags',
            df=df_anomalies,
            if_exists='append'
        )

        if success:
            logger.info(f"Inserted {rows} flagged transactions into anomaly_flags table")
        else:
            logger.warning("Failed to insert anomaly flags")

    return df_with_anomalies


def generate_reports(db_manager: object) -> None:
    """Generate analytical reports and views."""
    logger.info("=" * 60)
    logger.info("STEP 6: ANALYTICS & VIEWS")
    logger.info("=" * 60)

    try:
        # Execute SQL views
        logger.info("Creating analytical views...")

        with open('sql/views.sql', 'r') as f:
            views_sql = f.read()

        statements = [s.strip() for s in views_sql.split(';') if s.strip()]
        for stmt in statements:
            db_manager.execute_insert(stmt)

        logger.info(f"Created {len(statements)} analytical views")

    except FileNotFoundError:
        logger.warning("views.sql not found, skipping view creation")
    except Exception as e:
        logger.error(f"Error creating views: {e}")


def main() -> None:
    """Execute complete pipeline."""
    start_time = time.time()

    try:
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║  FINANCIAL TRANSACTION ANALYTICS PLATFORM - PIPELINE   ║")
        logger.info("║  Started: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " * 28 + "║")
        logger.info("╚" + "=" * 58 + "╝")

        # Step 1: Database Setup
        db_manager = setup_database()

        # Step 2: Data Ingestion
        df_raw = run_data_ingestion()

        # Step 3: Data Processing
        df_processed = run_data_processing(df_raw)

        # Step 4: Database Insert
        run_database_insert(db_manager, df_processed)

        # Step 5: Anomaly Detection
        df_with_anomalies = run_anomaly_detection(db_manager, df_processed)

        # Step 6: Generate Reports
        generate_reports(db_manager)

        # Cleanup
        db_manager.close()

        # Summary
        elapsed_time = time.time() - start_time

        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total Time: {elapsed_time:.2f} seconds")
        logger.info(f"Throughput: {len(df_processed) / elapsed_time:.0f} rows/second")
        logger.info(f"Status: SUCCESS ✓")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        logger.error("STATUS: FAILED ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
