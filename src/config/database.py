"""Database configuration examples for multi-agent system."""

from typing import Optional

from src.agents.data_manager import DatabaseConfig, DataManager

# Example configurations for different database types

# SQLite (existing default)
sqlite_config = DatabaseConfig(
    db_type="sqlite",
    database="financial_data.db"
)

# Snowflake configuration
snowflake_config = DatabaseConfig(
    db_type="snowflake",
    account="your_account_id",  # e.g., "abc12345.us-east-1"
    username="your_username",
    password="your_password",
    database="YOUR_DATABASE",
    warehouse="YOUR_WAREHOUSE",  # e.g., "COMPUTE_WH"
    schema="PUBLIC",  # Optional, defaults to PUBLIC
    role="YOUR_ROLE",  # Optional, e.g., "ACCOUNTADMIN"
    extra_params={
        "application": "multi_agent_analysis",
        "client_session_keep_alive": True
    }
)


# Example usage functions
def create_sqlite_manager(db_path: str = "financial_data.db") -> DataManager:
    """Create DataManager for SQLite database."""
    return DataManager(path=db_path)


def create_snowflake_manager(
    account: str,
    username: str,
    password: str,
    database: str,
    warehouse: str,
    schema: str,
    role: Optional[str] = None
) -> DataManager:
    """Create DataManager for Snowflake database."""
    config = DatabaseConfig(
        db_type="snowflake",
        account=account,
        username=username,
        password=password,
        database=database,
        warehouse=warehouse,
        schema=schema,
        role=role
    )
    return DataManager(config=config)
