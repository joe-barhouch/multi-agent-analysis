"""Data Manager for handling SQL databases."""

import sqlite3

from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool


def get_engine_for_db(path: str) -> Engine:
    """Pull sql file, populate in-memory database, and create engine."""

    connection = sqlite3.connect(path, check_same_thread=False)

    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


class DataManager:
    """Data Manager"""

    def __init__(self, path: str, directory: str = "data"):
        """Initialize DataManager."""
        self.path = path
        self.directory = directory

        self.db = self.get_sql_database()

    def get_sql_database(self) -> SQLDatabase:
        """Get SQLDatabase instance."""
        engine = get_engine_for_db(path=self.path)
        return SQLDatabase(engine=engine)
