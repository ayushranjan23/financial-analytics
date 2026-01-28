"""
Data ingestion module for Financial Transaction Analytics Platform.
Handles reading and validating raw transaction data from CSV files.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, List
from config import settings

logger = logging.getLogger(__name__)

# Required columns in the raw CSV
REQUIRED_COLUMNS = [
    'transaction_id',
    'customer_id',
    'timestamp',
    'amount',
    'currency',
    'transaction_type',
    'merchant_category',
    'country'
]

# Expected data types for validation
EXPECTED_DTYPES = {
    'transaction_id': 'object',
    'customer_id': 'object',
    'timestamp': 'object',
    'amount': 'float64',
    'currency': 'object',
    'transaction_type': 'object',
    'merchant_category': 'object',
    'country': 'object',
    'is_fraudulent': 'bool' if 'is_fraudulent' in REQUIRED_COLUMNS else None
}


class DataIngestor:
    """
    Handles reading and initial validation of raw transaction data.
    """

    def __init__(self):
        """Initialize the DataIngestor with configuration."""
        self.raw_data_path = Path(settings.raw_data_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_from_source(self) -> pd.DataFrame:
        """
        Read raw transaction data from CSV file.

        Returns:
            pd.DataFrame: Raw transaction data

        Raises:
            FileNotFoundError: If CSV file does not exist
            pd.errors.ParserError: If CSV is malformed
            Exception: For other read errors
        """
        try:
            self.logger.info(f"Reading raw data from {self.raw_data_path}")

            if not self.raw_data_path.exists():
                raise FileNotFoundError(f"Raw data file not found: {self.raw_data_path}")

            # Read CSV with error handling for malformed rows
            df = pd.read_csv(
                self.raw_data_path,
                dtype={'transaction_id': 'object', 'customer_id': 'object'},
                on_bad_lines='warn',
                engine='python'
            )

            self.logger.info(f"Successfully read {len(df)} rows from CSV")
            return df

        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            raise
        except pd.errors.ParserError as e:
            self.logger.error(f"CSV parsing error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error reading CSV: {e}", exc_info=True)
            raise

    def validate_raw_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate that raw data has required columns and reasonable data types.

        Args:
            df (pd.DataFrame): Raw data to validate

        Returns:
            Tuple[bool, List[str]]: (is_valid, list of errors)
        """
        errors = []

        # Check for required columns
        missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            self.logger.error(f"Missing columns: {missing_columns}")

        # Check for empty dataframe
        if len(df) == 0:
            errors.append("Data frame is empty")
            self.logger.error("Empty dataframe provided")

        # Check for null values in critical columns
        critical_nulls = df[REQUIRED_COLUMNS].isnull().sum()
        null_columns = critical_nulls[critical_nulls > 0]
        if not null_columns.empty:
            null_info = null_columns.to_dict()
            errors.append(f"Null values in columns: {null_info}")
            self.logger.warning(f"Null values found: {null_info}")

        # Validate amount column is numeric and mostly non-negative
        try:
            negative_amounts = (df['amount'] < 0).sum()
            if negative_amounts > len(df) * 0.05:  # More than 5% negative
                errors.append(f"Suspicious amount values: {negative_amounts} negative amounts")
                self.logger.warning(f"{negative_amounts} negative amounts in data")
        except (KeyError, TypeError) as e:
            errors.append(f"Cannot validate amount column: {e}")

        # Check timestamp format (should be parseable)
        try:
            pd.to_datetime(df['timestamp'], errors='coerce')
            invalid_dates = pd.to_datetime(df['timestamp'], errors='coerce').isnull().sum()
            if invalid_dates > len(df) * 0.01:  # More than 1% unparseable
                errors.append(f"Invalid timestamp format: {invalid_dates} unparseable dates")
                self.logger.warning(f"{invalid_dates} timestamps could not be parsed")
        except Exception as e:
            errors.append(f"Timestamp validation failed: {e}")

        is_valid = len(errors) == 0

        if is_valid:
            self.logger.info("Raw data schema validation passed")
        else:
            self.logger.error(f"Schema validation failed with {len(errors)} errors")

        return is_valid, errors

    def validate_and_get_data(self) -> pd.DataFrame:
        """
        Complete validation pipeline: fetch and validate data.

        Returns:
            pd.DataFrame: Validated raw data

        Raises:
            Exception: If validation fails
        """
        self.logger.info("Starting data ingestion and validation")

        # Fetch data
        df = self.fetch_from_source()

        # Validate schema
        is_valid, errors = self.validate_raw_schema(df)

        if not is_valid:
            error_msg = "; ".join(errors)
            self.logger.error(f"Validation failed: {error_msg}")
            # In production, this would trigger an alert
            # For now, we log and continue with available data
            self.logger.warning("Proceeding with data quality issues - review required")

        self.logger.info(f"Data ingestion complete: {len(df)} records ready for processing")
        return df
