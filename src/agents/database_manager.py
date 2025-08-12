"""Simple database manager for Snowflake connections."""

from typing import List
from urllib.parse import parse_qs, urlparse

import pandas as pd
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine, text
from sqlglot import exp as sql_exp
from sqlglot import parse

from src.config import SNOWFLAKE_CONN_STRING, SNOWFLAKE_RSA_PRIVATE_KEY


class SQLSecurityError(Exception):
    """Exception raised for dangerous SQL operations."""

    pass


def validate_sql_query(query: str) -> str:
    """Validate SQL query for security threats using sqlglot.

    - Enforces a single statement (no multi-statement queries).
    - Allows only SELECT queries (WITH/CTE and UNION/UNION ALL).
    - Detects dangerous operations via AST nodes (not regex).

    Args:
        query: SQL query string to validate

    Returns:
        Cleaned query string

    Raises:
        SQLSecurityError: If query contains dangerous operations
            or invalid structure
    """
    sql = query.strip()
    if not sql:
        raise SQLSecurityError("Empty SQL query is not allowed.")

    # Parse the SQL into an AST using the Snowflake dialect.
    # Use parse() (not parse_one) to detect multiple statements.
    try:
        statements = parse(sql, read="snowflake")
    except Exception as e:
        raise SQLSecurityError(f"Invalid SQL syntax: {e}") from e

    # Disallow multiple statements separated by semicolons
    if len(statements) != 1:
        raise SQLSecurityError("Only a single SQL statement is allowed.")

    stmt = statements[0]

    # Build a list of disallowed expression types safely via getattr
    disallowed_names = [
        "Delete",
        "Drop",
        "Truncate",
        "Alter",
        "Create",
        "Insert",
        "Update",
        "Replace",
        "Merge",
        "Grant",
        "Revoke",
        "Call",
        "Execute",
        "Use",
        "Set",
        "Declare",
        # Also block generic command statements if present
        # in the dialect
        "Command",
    ]
    disallowed_types = tuple(
        t
        for t in (getattr(sql_exp, name, None) for name in disallowed_names)
        if t is not None
    )

    # If the top-level statement itself is a disallowed operation,
    # raise a precise error before generic gating.
    for t in disallowed_types:
        if isinstance(stmt, t):
            op_name = getattr(t, "__name__", str(t)).upper()
            raise SQLSecurityError(
                (
                    f"Dangerous SQL operation '{op_name}' detected. "
                    "Only SELECT queries are permitted."
                )
            )

    # Allow only SELECT/CTE/UNION as the top-level statement
    allowed_roots = (sql_exp.Select, sql_exp.With, sql_exp.Union)
    if not isinstance(stmt, allowed_roots):
        raise SQLSecurityError(
            "Only SELECT queries (including WITH/UNION) are allowed."
        )

    # If WITH (CTE), unwrap to the underlying statement
    # (should be SELECT or UNION)
    root = stmt
    if isinstance(stmt, sql_exp.With):
        root = stmt.this
        if not isinstance(root, (sql_exp.Select, sql_exp.Union)):
            raise SQLSecurityError("WITH must wrap a SELECT or UNION query.")

    # Search the AST for any disallowed operations. This avoids
    # false positives from strings/comments.
    for t in disallowed_types:
        if root.find(t):
            # Report the keyword name in upper case for clarity
            op_name = getattr(t, "__name__", str(t)).upper()
            raise SQLSecurityError(
                (
                    "Dangerous SQL operation '"
                    f"{op_name}"
                    "' detected. Only SELECT queries are permitted."
                )
            )

    # If the root is a UNION, ensure each side is a SELECT
    # (sqlglot guarantees this for typical parses)
    if isinstance(root, sql_exp.Union):
        left_ok = isinstance(
            root.left, (sql_exp.Select, sql_exp.With, sql_exp.Subquery)
        )
        right_ok = isinstance(
            root.right, (sql_exp.Select, sql_exp.With, sql_exp.Subquery)
        )
        if not (left_ok and right_ok):
            raise SQLSecurityError("UNION must combine SELECT queries only.")

    return sql


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
            "username": parsed.username,
            "account": parsed.hostname,
            "database": parsed.path.lstrip("/").split("/")[0],
            "warehouse": params.get("warehouse", [None])[0],
            "schema": params.get("schema", [None])[0],
            "role": params.get("role", [None])[0],
        }

    @property
    def engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            connect_args = {"private_key": self.private_key}
            if self.config["warehouse"]:
                connect_args["warehouse"] = self.config["warehouse"]
            if self.config["role"]:
                connect_args["role"] = self.config["role"]

            self._engine = create_engine(self.conn_string, connect_args=connect_args)
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
        """Execute SQL query and return results as DataFrame.

        Args:
            sql: SQL query to execute

        Returns:
            DataFrame with query results

        Raises:
            SQLSecurityError: If query contains dangerous operations
        """
        # Validate query for security
        validated_sql = validate_sql_query(sql)

        with self.engine.connect() as conn:
            return pd.read_sql(validated_sql, conn)

    def run_sql(self, query: str) -> str:
        """Run SQL query and return results as string (for LangChain).

        Args:
            query: SQL query to execute

        Returns:
            Query results as string

        Raises:
            SQLSecurityError: If query contains dangerous operations
        """
        # Validate query for security
        validated_query = validate_sql_query(query)

        return self.sql_database.run(validated_query)


def create_snowflake_manager() -> SnowflakeManager:
    """Create Snowflake manager from environment config.

    Returns:
        Configured SnowflakeManager instance

    Raises:
        ValueError: If required environment variables are missing
    """
    if not SNOWFLAKE_CONN_STRING:
        raise ValueError("SNOWFLAKE_CONN_STRING environment variable is required")

    if not SNOWFLAKE_RSA_PRIVATE_KEY:
        raise ValueError("SNOWFLAKE_RSA_PRIVATE_KEY environment variable is required")

    return SnowflakeManager(SNOWFLAKE_CONN_STRING, SNOWFLAKE_RSA_PRIVATE_KEY)


# For backward compatibility, create an alias
DataManager = SnowflakeManager
