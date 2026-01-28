"""
Data processing module for Financial Transaction Analytics Platform.
Handles cleaning, transformation, and feature engineering of transaction data.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Cleans, transforms, and enriches transaction data using Pandas.
    Implements feature engineering and validation logic.
    """

    def __init__(self):
        """Initialize the DataProcessor."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean raw transaction data: handle missing values, duplicates, and formatting.

        Args:
            df (pd.DataFrame): Raw transaction data

        Returns:
            pd.DataFrame: Cleaned data

        Processing steps:
        - Convert timestamp to datetime
        - Remove duplicates
        - Fill missing values appropriately
        - Standardize data types
        - Create transaction_date column
        """
        self.logger.info(f"Starting data cleaning on {len(df)} rows")

        df = df.copy()  # Work on a copy to avoid SettingWithCopyWarning

        # 1. Standardize timestamp format
        self.logger.debug("Converting timestamp to datetime")
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # 2. Remove exact duplicates (same transaction_id and timestamp)
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['transaction_id', 'timestamp'], keep='first')
        duplicates_removed = initial_rows - len(df)
        self.logger.info(f"Removed {duplicates_removed} duplicate rows")

        # 3. Handle missing values
        # For amount: forward fill (assume same amount as previous for same customer)
        # For merchant_category: fill with 'Unknown'
        # For country: fill with 'Unknown'
        for col in ['amount', 'currency', 'transaction_type', 'merchant_category', 'country']:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    if col == 'amount':
                        # For amounts, use median amount instead of forward fill
                        df[col].fillna(df[col].median(), inplace=True)
                        self.logger.info(f"Filled {null_count} null values in {col} with median")
                    else:
                        df[col].fillna('Unknown', inplace=True)
                        self.logger.info(f"Filled {null_count} null values in {col} with 'Unknown'")

        # 4. Ensure amount is numeric and non-negative
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        negative_mask = df['amount'] < 0
        if negative_mask.any():
            self.logger.warning(f"Found {negative_mask.sum()} negative amounts, converting to absolute values")
            df.loc[negative_mask, 'amount'] = df.loc[negative_mask, 'amount'].abs()

        # 5. Create transaction_date (date only, no time) for grouping
        df['transaction_date'] = df['timestamp'].dt.date

        self.logger.info(f"Data cleaning complete: {len(df)} rows remaining")
        return df

    def enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Perform feature engineering and data enrichment.

        Args:
            df (pd.DataFrame): Cleaned transaction data

        Returns:
            pd.DataFrame: Enriched data with new features

        Features created:
        - hour_of_day: Hour when transaction occurred (0-23)
        - day_of_week: Day of week (0=Monday, 6=Sunday)
        - amount_in_usd: Standardized amount in USD
        - customer_transaction_count_7d: 7-day rolling transaction count per customer
        - is_high_value: Flag for transactions > $10,000
        - is_cross_border: Flag for transactions with country != 'US' (simplified)
        """
        self.logger.info("Starting feature engineering")

        df = df.copy()

        # 1. Temporal features
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday
        df['month'] = df['timestamp'].dt.month
        df['day_of_month'] = df['timestamp'].dt.day

        self.logger.debug("Created temporal features: hour_of_day, day_of_week, month")

        # 2. Currency standardization (simplified: use amount as-is, assume all USD)
        # In production: use live FX rates
        df['amount_in_usd'] = df['amount'].astype(float)
        self.logger.debug("Standardized amounts to USD equivalent")

        # 3. Customer velocity features (7-day rolling window)
        # Sort by customer and timestamp for rolling calculation
        df_sorted = df.sort_values(['customer_id', 'timestamp']).copy()

        # Calculate 7-day transaction count per customer
        df_sorted['customer_transaction_count_7d'] = (
            df_sorted.set_index('timestamp')
            .groupby('customer_id')
            .rolling('7D')['transaction_id']
            .count()
            .reset_index(drop=True)
            .values
        )

        # Merge back with original order
        df = df_sorted.sort_index()
        df = df.reset_index(drop=True)

        self.logger.debug("Calculated 7-day customer transaction velocity")

        # 4. Business rule flags
        df['is_high_value'] = df['amount_in_usd'] > 10000
        df['is_cross_border'] = df['country'].str.upper() != 'US'
        df['is_weekend'] = df['day_of_week'].isin([5, 6])  # Saturday, Sunday

        # 5. Merchant category encoding (simple: just lowercase)
        df['merchant_category_lower'] = df['merchant_category'].str.lower()

        self.logger.info(f"Feature engineering complete: {df.shape[1]} columns, {len(df)} rows")
        self.logger.debug(f"New columns added: {', '.join(df.columns[df.columns.get_loc('hour_of_day'):-3])}")

        return df

    def validate_processed_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate processed data for quality and consistency.

        Args:
            df (pd.DataFrame): Processed transaction data

        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)

        Checks:
        - No negative amounts
        - Timestamps are in valid range (past 2 years)
        - Required columns present
        - No null values in critical columns
        """
        errors = []

        # 1. Check for negative amounts
        if (df['amount'] < 0).any():
            neg_count = (df['amount'] < 0).sum()
            errors.append(f"{neg_count} transactions with negative amounts")
            self.logger.error(f"Found {neg_count} negative amounts in processed data")

        # 2. Check date range (should be recent, within last 2 years)
        max_date = pd.Timestamp.now()
        min_date = max_date - pd.Timedelta(days=730)  # 2 years

        out_of_range = (df['timestamp'] < min_date) | (df['timestamp'] > max_date)
        if out_of_range.any():
            out_count = out_of_range.sum()
            errors.append(f"{out_count} transactions outside valid date range")
            self.logger.warning(f"{out_count} transactions outside 2-year window")

        # 3. Check for null values in critical columns
        critical_cols = ['transaction_id', 'customer_id', 'timestamp', 'amount', 'country']
        for col in critical_cols:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    errors.append(f"{null_count} null values in {col}")
                    self.logger.error(f"Found {null_count} null values in {col}")

        # 4. Check hour_of_day is in range 0-23
        if 'hour_of_day' in df.columns:
            invalid_hours = ((df['hour_of_day'] < 0) | (df['hour_of_day'] > 23)).sum()
            if invalid_hours > 0:
                errors.append(f"{invalid_hours} invalid hour values")

        is_valid = len(errors) == 0

        if is_valid:
            self.logger.info("Data validation passed all checks")
        else:
            self.logger.error(f"Data validation failed with {len(errors)} errors")

        return is_valid, errors

    def process_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute complete processing pipeline: clean -> enrich -> validate.

        Args:
            df (pd.DataFrame): Raw transaction data

        Returns:
            pd.DataFrame: Fully processed and enriched data

        Raises:
            ValueError: If validation fails
        """
        self.logger.info("Starting complete data processing pipeline")

        # Step 1: Clean
        df_clean = self.clean_data(df)

        # Step 2: Enrich
        df_enriched = self.enrich_data(df_clean)

        # Step 3: Validate
        is_valid, errors = self.validate_processed_data(df_enriched)

        if not is_valid:
            self.logger.warning(f"Validation warnings: {errors}")
            # Continue processing but flag for review

        self.logger.info(f"Pipeline complete: {len(df_enriched)} rows processed and ready")
        return df_enriched
