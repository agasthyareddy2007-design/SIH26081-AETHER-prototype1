"""
Database connection manager for Supabase PostgreSQL
Handles connection pooling and graceful failure
"""
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

from .config import DatabaseConfig

logger = logging.getLogger("aether.database")

class DatabaseConnection:
    """
    Manages PostgreSQL connection pool.
    Graceful degradation: if DB is unavailable, logs the error but allows forecasting to continue.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig.from_env()
        self.pool: Optional[pool.SimpleConnectionPool] = None
        self._available = False

        if self.config:
            try:
                self.pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    connect_timeout=5
                )
                self._available = True
                logger.info("PostgreSQL connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {type(e).__name__}")
                self._available = False
        else:
            logger.warning("Database credentials not found in environment. Persistence disabled.")

    def is_available(self) -> bool:
        """Check if database connection is available"""
        return self._available and self.pool is not None

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Yields None if database is unavailable.
        """
        if not self.is_available():
            yield None
            return

        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {type(e).__name__}")
            yield None
        finally:
            if conn:
                self.pool.putconn(conn)

    def close(self):
        """Close all connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")

# Global connection instance
_db_connection: Optional[DatabaseConnection] = None

def get_db_connection() -> DatabaseConnection:
    """Get or create the global database connection"""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection
