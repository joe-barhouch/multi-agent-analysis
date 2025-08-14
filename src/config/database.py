"""Snowflake database setup for the multi-agent system.

This module provides a simple re-export of the Snowflake helpers used across
the application. All database interactions are centralized in
`src.agents.database_manager`.
"""

from src.agents.database_manager import (
    SnowflakeManager,
    create_snowflake_manager,
)

__all__ = ["SnowflakeManager", "create_snowflake_manager"]
