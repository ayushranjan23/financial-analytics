"""
Anomaly detection module for Financial Transaction Analytics Platform.
Implements statistical, IQR-based, and rule-based anomaly detection methods.
"""

import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalies in transaction data using multiple methods:
    - Statistical outliers (Z-score)
    - Interquartile Range (IQR)
    - Business rule-based detection
    """

    def __init__(self, zscore_threshold: float = 3.0, iqr_multiplier: float = 1.5):
        """
        Initialize anomaly detector with thresholds.

        Args:
            zscore_threshold (float): Z-score threshold for outlier detection
            iqr_multiplier (float): IQR multiplier for outlier bounds
        """
        self.zscore_threshold = zscore_threshold
        self.iqr_multiplier = iqr_multiplier
        self.logger = logging.getLogger(self.__class__.__name__)

    def statistical_outliers(
        self,
        df: pd.DataFrame,
        column: str = 'amount',
        z_threshold: Optional[float] = None
    ) -> np.ndarray:
        """
        Detect statistical outliers using Z-score method.

        Formula: Z = (X - μ) / σ

        Args:
            df (pd.DataFrame): Transaction data
            column (str): Column to analyze
            z_threshold (float): Z-score threshold (default: self.zscore_threshold)

        Returns:
            np.ndarray: Boolean mask where True = outlier

        Uses standard normal distribution: values with Z > 3 are ~99.7th percentile
        """
        try:
            z_threshold = z_threshold or self.zscore_threshold

            if column not in df.columns:
                self.logger.error(f"Column {column} not found in DataFrame")
                return np.zeros(len(df), dtype=bool)

            # Calculate mean and std
            mean = df[column].mean()
            std = df[column].std()

            if std == 0:
                self.logger.warning(f"Standard deviation is 0 for {column}, skipping Z-score detection")
                return np.zeros(len(df), dtype=bool)

            # Calculate Z-scores
            z_scores = np.abs((df[column] - mean) / std)
            outliers = z_scores > z_threshold

            outlier_count = outliers.sum()
            self.logger.info(f"Z-score detection found {outlier_count} outliers in {column}")

            return outliers

        except Exception as e:
            self.logger.error(f"Error in statistical outlier detection: {e}", exc_info=True)
            return np.zeros(len(df), dtype=bool)

    def iqr_outliers(
        self,
        df: pd.DataFrame,
        column: str = 'amount',
        multiplier: Optional[float] = None
    ) -> np.ndarray:
        """
        Detect outliers using Interquartile Range (IQR) method.

        Formula:
        - Q1 = 25th percentile
        - Q3 = 75th percentile
        - IQR = Q3 - Q1
        - Lower bound = Q1 - multiplier × IQR
        - Upper bound = Q3 + multiplier × IQR

        Args:
            df (pd.DataFrame): Transaction data
            column (str): Column to analyze
            multiplier (float): IQR multiplier (default: self.iqr_multiplier)

        Returns:
            np.ndarray: Boolean mask where True = outlier
        """
        try:
            multiplier = multiplier or self.iqr_multiplier

            if column not in df.columns:
                self.logger.error(f"Column {column} not found in DataFrame")
                return np.zeros(len(df), dtype=bool)

            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR

            outliers = (df[column] < lower_bound) | (df[column] > upper_bound)

            outlier_count = outliers.sum()
            self.logger.info(
                f"IQR detection found {outlier_count} outliers in {column} "
                f"(bounds: {lower_bound:.2f} - {upper_bound:.2f})"
            )

            return outliers

        except Exception as e:
            self.logger.error(f"Error in IQR outlier detection: {e}", exc_info=True)
            return np.zeros(len(df), dtype=bool)

    def rule_based_anomalies(
        self,
        df: pd.DataFrame,
        high_value_threshold: float = 10000.0,
        velocity_threshold: int = 5,
        velocity_window_minutes: int = 60
    ) -> Dict[str, np.ndarray]:
        """
        Detect anomalies based on business rules.

        Rules:
        1. High-value transactions: amount > threshold
        2. Velocity anomaly: >N transactions from same customer in M minutes
        3. Geographic anomaly: Cross-border high-value transaction
        4. Time-based anomaly: Weekend/off-hours for corporate accounts

        Args:
            df (pd.DataFrame): Transaction data
            high_value_threshold (float): Threshold for high-value flag
            velocity_threshold (int): Max transactions in window
            velocity_window_minutes (int): Time window for velocity check

        Returns:
            Dict[str, np.ndarray]: Boolean masks for each rule
        """
        rules_triggered = {}

        try:
            # Rule 1: High-value transactions
            if 'amount_in_usd' in df.columns:
                high_value = df['amount_in_usd'] > high_value_threshold
                rules_triggered['high_value'] = high_value
                self.logger.info(f"High-value rule flagged {high_value.sum()} transactions")
            else:
                self.logger.warning("amount_in_usd column not found, skipping high-value rule")
                rules_triggered['high_value'] = np.zeros(len(df), dtype=bool)

            # Rule 2: Velocity anomaly (high transaction frequency)
            if 'customer_id' in df.columns and 'timestamp' in df.columns:
                velocity_flags = np.zeros(len(df), dtype=bool)

                # Group by customer and time window
                df_sorted = df.sort_values('timestamp').copy()
                for customer_id in df_sorted['customer_id'].unique():
                    customer_txns = df_sorted[df_sorted['customer_id'] == customer_id]

                    # Check for >5 transactions in 1-hour window
                    for idx, row in customer_txns.iterrows():
                        window_start = row['timestamp'] - timedelta(minutes=velocity_window_minutes)
                        window_end = row['timestamp']

                        txns_in_window = customer_txns[
                            (customer_txns['timestamp'] >= window_start) &
                            (customer_txns['timestamp'] <= window_end)
                        ]

                        if len(txns_in_window) > velocity_threshold:
                            velocity_flags[idx] = True

                rules_triggered['velocity'] = velocity_flags
                self.logger.info(f"Velocity rule flagged {velocity_flags.sum()} transactions")
            else:
                self.logger.warning("Required columns for velocity check not found")
                rules_triggered['velocity'] = np.zeros(len(df), dtype=bool)

            # Rule 3: Geographic anomaly (cross-border high-value)
            if 'is_cross_border' in df.columns and 'amount_in_usd' in df.columns:
                cross_border_high = (
                    (df['is_cross_border'] == True) &
                    (df['amount_in_usd'] > high_value_threshold * 0.5)  # Lower threshold for cross-border
                )
                rules_triggered['cross_border_high'] = cross_border_high
                self.logger.info(f"Geographic rule flagged {cross_border_high.sum()} transactions")
            else:
                self.logger.warning("Required columns for geographic check not found")
                rules_triggered['cross_border_high'] = np.zeros(len(df), dtype=bool)

            # Rule 4: Weekend high-value (anomalous timing)
            if 'is_weekend' in df.columns and 'amount_in_usd' in df.columns:
                weekend_high = (
                    (df['is_weekend'] == True) &
                    (df['amount_in_usd'] > high_value_threshold)
                )
                rules_triggered['weekend_high'] = weekend_high
                self.logger.info(f"Weekend anomaly rule flagged {weekend_high.sum()} transactions")
            else:
                self.logger.warning("Required columns for weekend check not found")
                rules_triggered['weekend_high'] = np.zeros(len(df), dtype=bool)

            return rules_triggered

        except Exception as e:
            self.logger.error(f"Error in rule-based anomaly detection: {e}", exc_info=True)
            # Return empty flags
            return {
                'high_value': np.zeros(len(df), dtype=bool),
                'velocity': np.zeros(len(df), dtype=bool),
                'cross_border_high': np.zeros(len(df), dtype=bool),
                'weekend_high': np.zeros(len(df), dtype=bool),
            }

    def mark_anomalies(
        self,
        df: pd.DataFrame,
        zscore_weight: float = 0.4,
        rule_weight: float = 0.6
    ) -> pd.DataFrame:
        """
        Calculate composite anomaly score and mark flagged transactions.

        Scoring methodology:
        - Statistical score: 1.0 if Z-score OR IQR outlier, else 0.0
        - Rule score: Number of rules triggered / total rules
        - Anomaly score: (stat_score × 0.4) + (rule_score × 0.6)

        Args:
            df (pd.DataFrame): Transaction data with processed features
            zscore_weight (float): Weight for statistical methods
            rule_weight (float): Weight for rule-based methods

        Returns:
            pd.DataFrame: DataFrame with anomaly_score and is_flagged columns
        """
        try:
            self.logger.info(f"Calculating anomaly scores for {len(df)} transactions")

            df = df.copy()

            # 1. Statistical anomaly score
            zscore_outliers = self.statistical_outliers(df, 'amount_in_usd')
            iqr_outliers = self.iqr_outliers(df, 'amount_in_usd')
            statistical_score = (zscore_outliers | iqr_outliers).astype(float)

            self.logger.info(f"Statistical outliers: {statistical_score.sum()}")

            # 2. Rule-based anomaly score
            rules = self.rule_based_anomalies(df)
            rules_triggered_count = sum(rules.values())  # Sum all boolean arrays
            rule_score = (rules_triggered_count / len(rules)).astype(float)

            self.logger.info(f"Rule-based anomalies: {rule_score.sum():.0f} rule triggers")

            # 3. Composite anomaly score (0 to 1)
            df['anomaly_score'] = (
                (statistical_score * zscore_weight) +
                (rule_score * rule_weight)
            )

            # 4. Flag high-risk transactions
            threshold = 0.5  # Configurable threshold
            df['is_flagged'] = df['anomaly_score'] > threshold

            # 5. Add rule trigger info for audit trail
            df['rules_triggered'] = sum(list(rules.values()))

            flagged_count = df['is_flagged'].sum()
            high_risk = (df['anomaly_score'] > 0.7).sum()

            self.logger.info(
                f"Anomaly marking complete: {flagged_count} flagged, "
                f"{high_risk} high-risk (score > 0.7)"
            )

            return df

        except Exception as e:
            self.logger.error(f"Error in anomaly marking: {e}", exc_info=True)
            # Return data with zero anomaly scores
            df['anomaly_score'] = 0.0
            df['is_flagged'] = False
            df['rules_triggered'] = 0
            return df


# Type hint for Optional
from typing import Optional
