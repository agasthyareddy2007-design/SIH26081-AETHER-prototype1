"""
Database configuration for Supabase PostgreSQL
Loads credentials from environment variables only
"""
import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Load .env file for local development
try:
    from dotenv import load_dotenv
    # Look for .env in project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, rely on system environment
    pass

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> Optional['DatabaseConfig']:
        """
        Load database configuration from environment variables.
        Returns None if any required variable is missing.
        Never logs or prints credentials.
        """
        try:
            host = os.environ.get('DB_HOST')
            port = os.environ.get('DB_PORT')
            database = os.environ.get('DB_NAME')
            user = os.environ.get('DB_USER')
            password = os.environ.get('DB_PASSWORD')

            if not all([host, port, database, user, password]):
                return None

            return cls(
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password
            )
        except (ValueError, KeyError):
            return None

    def get_connection_string(self) -> str:
        """Returns PostgreSQL connection string. Never log this."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
