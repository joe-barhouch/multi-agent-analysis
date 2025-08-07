"""Simple database manager for Snowflake connections."""

from typing import List
from urllib.parse import parse_qs, urlparse

import pandas as pd
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine, text

from src.config import SNOWFLAKE_CONN_STRING, SNOWFLAKE_RSA_PRIVATE_KEY


class SnowflakeManager:
    """Simple Snowflake database manager."""
    
    def __init__(self, conn_string: str, private_key: str):
        """Initialize with connection string and private key.
        
        Args:
            conn_string: Snowflake connection string
            private_key: RSA private key for authentication
        """
        self.conn_string = conn_string
        self.private_key = private_key
        self._engine = None
        self._sql_database = None
        self.config = self._parse_connection_string(conn_string)
    
    def _parse_connection_string(self, conn_string: str) -> dict:
        """Parse connection string into components."""
        parsed = urlparse(conn_string)
        params = parse_qs(parsed.query)
        
        return {
            'username': parsed.username,
            'account': parsed.hostname,
            'database': parsed.path.lstrip('/').split('/')[0],
            'warehouse': params.get('warehouse', [None])[0],
            'schema': params.get('schema', [None])[0],
            'role': params.get('role', [None])[0]
        }
    
    @property
    def engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            connect_args = {'private_key': self.private_key}
            if self.config['warehouse']:
                connect_args['warehouse'] = self.config['warehouse']
            if self.config['role']:
                connect_args['role'] = self.config['role']
                
            self._engine = create_engine(
                self.conn_string,
                connect_args=connect_args
            )
        return self._engine
    
    @property
    def sql_database(self):
        """Get or create LangChain SQL database."""
        if self._sql_database is None:
            self._sql_database = SQLDatabase(engine=self.engine)
        return self._sql_database
    
    @property
    def db(self):
        """Alias for sql_database (for backward compatibility)."""
        return self.sql_database
    
    def get_sql_database(self):
        """Get LangChain SQL database (for backward compatibility)."""
        return self.sql_database
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()
            return True
        except Exception:
            return False
    
    def list_tables(self) -> List[str]:
        """Get list of all tables."""
        return self.sql_database.get_usable_table_names()
    
    def get_table_info(self, table_name: str) -> str:
        """Get table schema information."""
        return self.sql_database.get_table_info_no_throw([table_name])
    
    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql(sql, conn)
    
    def run_sql(self, query: str) -> str:
        """Run SQL query and return results as string (for LangChain)."""
        return self.sql_database.run(query)


def create_snowflake_manager() -> SnowflakeManager:
    """Create Snowflake manager from environment config.
    
    Returns:
        Configured SnowflakeManager instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    if not SNOWFLAKE_CONN_STRING:
        raise ValueError(
            "SNOWFLAKE_CONN_STRING environment variable is required"
        )
    
    if not SNOWFLAKE_RSA_PRIVATE_KEY:
        raise ValueError(
            "SNOWFLAKE_RSA_PRIVATE_KEY environment variable is required"
        )
    
    return SnowflakeManager(SNOWFLAKE_CONN_STRING, SNOWFLAKE_RSA_PRIVATE_KEY)


# For backward compatibility, create an alias
DataManager = SnowflakeManager
