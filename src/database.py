"""
Database operations module for Financial Transaction Analytics Platform.
Handles PostgreSQL connections, table creation, and data insertion using SQLAlchemy.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, inspect, Table, Column, String, Float, DateTime, Boolean, Integer, MetaData
from sqlalchemy.exc import SQLAlchemyError
from config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database operations for the analytics platform.
    Uses SQLAlchemy for ORM and connection pooling.
    """

    def __init__(self):
        """Initialize database connection pool and engine."""
        try:
            self.engine = create_engine(
                settings.database_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True  # Test connections before using
            )
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.info("Database engine initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database engine: {e}", exc_info=True)
            raise

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.logger.info("Database connection test successful")
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False

    def create_tables(self) -> bool:
        """
        Create all required database tables from SQL schema file.

        Returns:
            bool: True if successful, False otherwise

        Executes sql/schema.sql which creates:
        - dim_customers
        - fact_transactions
        - anomaly_flags
        """
        try:
            self.logger.info("Creating database schema from sql/schema.sql")

            # Read and execute schema SQL
            with open('sql/schema.sql', 'r') as f:
                schema_sql = f.read()

            with self.engine.connect() as conn:
                # Execute schema (may contain multiple statements)
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for stmt in statements:
                    conn.execute(text(stmt))
                    self.logger.debug(f"Executed schema statement: {stmt[:50]}...")
                conn.commit()

            self.logger.info("Database schema created successfully")
            return True

        except FileNotFoundError as e:
            self.logger.error(f"Schema file not found: {e}")
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Database schema creation failed: {e}", exc_info=True)
            return False

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name (str): Name of the table

        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            exists = table_name in tables
            self.logger.debug(f"Table {table_name} exists: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
            return False

    def insert_dataframe(
        self,
        table_name: str,
        df: pd.DataFrame,
        if_exists: str = 'append',
        index: bool = False
    ) -> Tuple[bool, int]:
        """
        Insert DataFrame into database table efficiently using bulk insert.

        Args:
            table_name (str): Target table name
            df (pd.DataFrame): DataFrame to insert
            if_exists (str): {'fail', 'replace', 'append'}
            index (bool): Whether to write index

        Returns:
            Tuple[bool, int]: (success, num_rows_inserted)

        Uses SQLAlchemy's method='multi' for optimal performance.
        Handles type conversion and error recovery.
        """
        try:
            if len(df) == 0:
                self.logger.warning("Empty DataFrame provided for insert")
                return True, 0

            self.logger.info(f"Inserting {len(df)} rows into {table_name}")

            # Insert using SQLAlchemy with 'multi' method (batch insert)
            with self.engine.begin() as conn:
                df.to_sql(
                    table_name,
                    conn,
                    if_exists=if_exists,
                    index=index,
                    method='multi',
                    chunksize=settings.batch_size
                )

            self.logger.info(f"Successfully inserted {len(df)} rows into {table_name}")
            return True, len(df)

        except SQLAlchemyError as e:
            self.logger.error(f"Database insert failed for {table_name}: {e}", exc_info=True)
            return False, 0
        except Exception as e:
            self.logger.error(f"Unexpected error during insert: {e}", exc_info=True)
            return False, 0

    def execute_query(self, query: str) -> Optional[pd.DataFrame]:
        """
        Execute a SQL query and return results as DataFrame.

        Args:
            query (str): SQL query to execute

        Returns:
            Optional[pd.DataFrame]: Query results or None if error
        """
        try:
            self.logger.debug(f"Executing query: {query[:100]}...")
            df = pd.read_sql_query(query, self.engine)
            self.logger.info(f"Query returned {len(df)} rows")
            return df
        except SQLAlchemyError as e:
            self.logger.error(f"Query execution failed: {e}")
            return None

    def execute_insert(self, query: str) -> Tuple[bool, Optional[int]]:
        """
        Execute an INSERT/UPDATE/DELETE statement.

        Args:
            query (str): SQL statement to execute

        Returns:
            Tuple[bool, Optional[int]]: (success, num_rows_affected)
        """
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(query))
                rows_affected = result.rowcount
            self.logger.info(f"Query executed successfully, {rows_affected} rows affected")
            return True, rows_affected
        except SQLAlchemyError as e:
            self.logger.error(f"Insert execution failed: {e}", exc_info=True)
            return False, None

    def get_table_count(self, table_name: str) -> Optional[int]:
        """
        Get row count for a table.

        Args:
            table_name (str): Table name

        Returns:
            Optional[int]: Row count or None if error
        """
        try:
            query = f"SELECT COUNT(*) as count FROM {table_name}"
            df = pd.read_sql_query(query, self.engine)
            count = df['count'].iloc[0]
            self.logger.info(f"Table {table_name} has {count} rows")
            return count
        except Exception as e:
            self.logger.error(f"Failed to get table count: {e}")
            return None

    def drop_table_if_exists(self, table_name: str) -> bool:
        """
        Drop a table if it exists (useful for reset).

        Args:
            table_name (str): Table name

        Returns:
            bool: True if successful
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            self.logger.info(f"Table {table_name} dropped")
            return True
        except Exception as e:
            self.logger.error(f"Failed to drop table: {e}")
            return False

    def close(self):
        """Close database connection pool."""
        try:
            self.engine.dispose()
            self.logger.info("Database connection pool closed")
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")


# Type hint for return values
from typing import Tuple
