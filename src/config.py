"""
Configuration management module for Financial Transaction Analytics Platform.
Uses Pydantic BaseSettings for environment-based configuration.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database Configuration
    database_url: str = "postgresql://postgres:postgres@localhost:5432/financial_db"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Data Paths
    raw_data_path: str = "./data/raw/sample_transactions.csv"
    processed_data_path: str = "./data/processed/"

    # Application Settings
    log_level: str = "INFO"
    batch_size: int = 5000
    anomaly_score_threshold: float = 0.5
    environment: str = "development"
    debug: bool = False

    # Anomaly Detection Parameters
    zscore_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    high_value_threshold: float = 10000.0
    velocity_threshold: int = 5
    velocity_window_minutes: int = 60

    # Alert Configuration
    alert_high_anomaly_threshold: float = 0.85
    send_alerts: bool = False
    alert_email: Optional[str] = None

    class Config:
        """Pydantic config for environment variable loading."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def get_processed_path(self, filename: str) -> Path:
        """Get full path for processed data file."""
        return Path(self.processed_data_path) / filename


# Global settings instance
settings = Settings()
