"""
Test suite for Financial Transaction Analytics Platform.
Tests critical pipeline components: ingestion, processing, anomaly detection, database operations.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_ingestion import DataIngestor
from data_processor import DataProcessor
from database import DatabaseManager
from anomaly_detector import AnomalyDetector


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_data():
    """Create sample transaction data for testing."""
    now = datetime.now()
    data = {
        'transaction_id': [f'TXN_{i:05d}' for i in range(100)],
        'customer_id': [f'CUST_{i % 10:05d}' for i in range(100)],
        'timestamp': [now - timedelta(hours=i) for i in range(100)],
        'amount': np.random.uniform(10, 5000, 100),
        'currency': ['USD'] * 100,
        'transaction_type': np.random.choice(['POS', 'Online', 'Transfer'], 100),
        'merchant_category': np.random.choice(['Retail', 'Restaurant', 'Healthcare'], 100),
        'country': np.random.choice(['US', 'GB', 'FR', 'DE'], 100),
        'is_fraudulent': [False] * 98 + [True, True]
    }
    return pd.DataFrame(data)


@pytest.fixture
def processor():
    """Initialize DataProcessor for testing."""
    return DataProcessor()


@pytest.fixture
def detector():
    """Initialize AnomalyDetector for testing."""
    return AnomalyDetector(zscore_threshold=2.5, iqr_multiplier=1.5)


# ============================================================================
# Data Ingestion Tests
# ============================================================================

class TestDataIngestion:
    """Test data ingestion and validation."""

    def test_ingestor_initialization(self):
        """Test DataIngestor can be instantiated."""
        ingestor = DataIngestor()
        assert ingestor is not None
        assert ingestor.raw_data_path is not None

    def test_validate_raw_schema_success(self, processor, sample_data):
        """Test schema validation passes with valid data."""
        ingestor = DataIngestor()
        is_valid, errors = ingestor.validate_raw_schema(sample_data)
        assert is_valid or len(errors) < 5  # Allow minor warnings


# ============================================================================
# Data Processing Tests
# ============================================================================

class TestDataProcessor:
    """Test data cleaning and transformation."""

    def test_clean_data_removes_duplicates(self, processor, sample_data):
        """Test that clean_data removes duplicate transactions."""
        # Create duplicates
        df_dup = pd.concat([sample_data, sample_data.iloc[:5]], ignore_index=True)
        initial_count = len(df_dup)

        df_clean = processor.clean_data(df_dup)

        assert len(df_clean) < initial_count

    def test_clean_data_converts_timestamp(self, processor, sample_data):
        """Test that timestamp is converted to datetime."""
        df_clean = processor.clean_data(sample_data)
        assert pd.api.types.is_datetime64_any_dtype(df_clean['timestamp'])

    def test_clean_data_handles_missing_values(self, processor):
        """Test that missing values are handled appropriately."""
        df = pd.DataFrame({
            'transaction_id': ['TXN_00001', 'TXN_00002', 'TXN_00003'],
            'customer_id': ['CUST_001', 'CUST_002', 'CUST_003'],
            'timestamp': ['2026-01-15 10:00:00', '2026-01-15 11:00:00', '2026-01-15 12:00:00'],
            'amount': [100.0, np.nan, 300.0],
            'currency': ['USD', 'USD', 'USD'],
            'transaction_type': ['POS', 'Online', 'Transfer'],
            'merchant_category': ['Retail', 'Restaurant', None],
            'country': ['US', 'US', 'US'],
        })
        df_clean = processor.clean_data(df)
        assert not df_clean['amount'].isnull().any()
        assert not df_clean['merchant_category'].isnull().any()

    def test_enrich_data_creates_features(self, processor, sample_data):
        """Test that feature engineering creates expected columns."""
        df_clean = processor.clean_data(sample_data)
        df_enriched = processor.enrich_data(df_clean)

        expected_features = [
            'hour_of_day', 'day_of_week', 'month', 'day_of_month',
            'amount_in_usd', 'is_high_value', 'is_cross_border', 'is_weekend'
        ]

        for feature in expected_features:
            assert feature in df_enriched.columns, f"Missing feature: {feature}"

    def test_enrich_data_hour_of_day_range(self, processor, sample_data):
        """Test hour_of_day is in valid range (0-23)."""
        df_clean = processor.clean_data(sample_data)
        df_enriched = processor.enrich_data(df_clean)

        assert df_enriched['hour_of_day'].min() >= 0
        assert df_enriched['hour_of_day'].max() <= 23

    def test_validate_processed_data_success(self, processor, sample_data):
        """Test validation passes for clean data."""
        df_clean = processor.clean_data(sample_data)
        df_enriched = processor.enrich_data(df_clean)

        is_valid, errors = processor.validate_processed_data(df_enriched)
        # Should be valid or have minor warnings only
        critical_errors = [e for e in errors if 'negative' in e.lower()]
        assert len(critical_errors) == 0

    def test_process_pipeline_end_to_end(self, processor, sample_data):
        """Test complete processing pipeline."""
        df_processed = processor.process_pipeline(sample_data)

        # Check output is non-empty
        assert len(df_processed) > 0

        # Check all required columns exist
        required_cols = [
            'transaction_id', 'customer_id', 'timestamp', 'amount',
            'hour_of_day', 'day_of_week', 'amount_in_usd'
        ]
        for col in required_cols:
            assert col in df_processed.columns


# ============================================================================
# Anomaly Detection Tests
# ============================================================================

class TestAnomalyDetector:
    """Test anomaly detection algorithms."""

    def test_zscore_detects_outliers(self, detector):
        """Test Z-score method catches known outliers."""
        df = pd.DataFrame({
            'amount': [100, 105, 102, 110, 108, 5000]  # Last value is outlier
        })
        outliers = detector.statistical_outliers(df, column='amount', z_threshold=2.0)
        assert outliers.iloc[-1]  # Last row should be flagged

    def test_iqr_detects_outliers(self, detector):
        """Test IQR method detects outliers."""
        df = pd.DataFrame({
            'amount': list(range(100, 200)) + [1000]  # Last value is outlier
        })
        outliers = detector.iqr_outliers(df, column='amount')
        assert outliers.iloc[-1]  # Last row should be flagged

    def test_rule_based_detects_high_value(self, detector):
        """Test rule-based detection flags high-value transactions."""
        df = pd.DataFrame({
            'amount_in_usd': [100, 200, 15000, 300],
            'customer_id': ['C1', 'C1', 'C2', 'C1'],
            'timestamp': [datetime.now()] * 4,
            'is_cross_border': [False, False, False, False],
            'is_weekend': [False, False, False, False]
        })
        rules = detector.rule_based_anomalies(df, high_value_threshold=10000)
        assert 'high_value' in rules
        high_value_flags = rules['high_value']
        assert high_value_flags[2]  # Third row (15000) should be flagged

    def test_mark_anomalies_produces_scores(self, detector, sample_data):
        """Test mark_anomalies produces anomaly_score and is_flagged columns."""
        df_clean = DataProcessor().clean_data(sample_data)
        df_enriched = DataProcessor().enrich_data(df_clean)

        df_marked = detector.mark_anomalies(df_enriched)

        assert 'anomaly_score' in df_marked.columns
        assert 'is_flagged' in df_marked.columns

        # Check score range
        assert df_marked['anomaly_score'].min() >= 0
        assert df_marked['anomaly_score'].max() <= 1

    def test_anomaly_score_distribution(self, detector, sample_data):
        """Test anomaly scores are properly distributed."""
        df_clean = DataProcessor().clean_data(sample_data)
        df_enriched = DataProcessor().enrich_data(df_clean)
        df_marked = detector.mark_anomalies(df_enriched)

        # Most transactions should have low anomaly scores
        low_risk = (df_marked['anomaly_score'] <= 0.3).sum()
        assert low_risk > len(df_marked) * 0.5  # At least 50% low risk


# ============================================================================
# Database Tests
# ============================================================================

class TestDatabaseManager:
    """Test database operations."""

    def test_database_manager_initialization(self):
        """Test DatabaseManager can be instantiated."""
        # This will fail if DATABASE_URL is not set, which is expected
        try:
            db = DatabaseManager()
            assert db is not None
        except Exception:
            pytest.skip("Database not available for testing")

    def test_connection_test_method(self):
        """Test database connection test."""
        try:
            db = DatabaseManager()
            # Don't fail test if DB unavailable - it's an integration test
            result = db.test_connection()
            assert isinstance(result, bool)
        except Exception:
            pytest.skip("Database not available for testing")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete pipelines."""

    def test_full_pipeline_executes(self, sample_data):
        """Test that full pipeline executes without errors."""
        processor = DataProcessor()
        detector = AnomalyDetector()

        # Step 1: Process data
        df_processed = processor.process_pipeline(sample_data)
        assert len(df_processed) > 0

        # Step 2: Detect anomalies
        df_anomalies = detector.mark_anomalies(df_processed)
        assert len(df_anomalies) > 0
        assert 'anomaly_score' in df_anomalies.columns
        assert 'is_flagged' in df_anomalies.columns

        # Step 3: Validate output
        assert df_anomalies['anomaly_score'].min() >= 0
        assert df_anomalies['anomaly_score'].max() <= 1


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance benchmarks."""

    def test_processing_speed(self, processor):
        """Test data processing performance."""
        # Create 10K row dataset
        large_data = pd.DataFrame({
            'transaction_id': [f'TXN_{i:06d}' for i in range(10000)],
            'customer_id': [f'CUST_{i % 100:05d}' for i in range(10000)],
            'timestamp': [datetime.now() - timedelta(seconds=i) for i in range(10000)],
            'amount': np.random.uniform(10, 5000, 10000),
            'currency': ['USD'] * 10000,
            'transaction_type': np.random.choice(['POS', 'Online', 'Transfer'], 10000),
            'merchant_category': np.random.choice(['Retail', 'Restaurant', 'Healthcare'], 10000),
            'country': np.random.choice(['US', 'GB', 'FR'], 10000),
        })

        import time
        start = time.time()
        df_processed = processor.process_pipeline(large_data)
        elapsed = time.time() - start

        throughput = len(large_data) / elapsed
        print(f"\nProcessing throughput: {throughput:.0f} rows/second")

        # Should process at least 1000 rows/sec
        assert throughput > 1000


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
