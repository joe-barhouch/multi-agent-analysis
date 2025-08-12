"""Config file for the application."""

import os
from typing import Final, Optional

from dotenv import load_dotenv

load_dotenv()

DEBUG: Final[bool] = os.getenv("DEBUG", "false").lower() == "true"

# API Keys
OPENAI_API_KEY: Final[Optional[str]] = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: Final[Optional[str]] = os.getenv("ANTHROPIC_API_KEY", "")

# Model Configuration
DEFAULT_MODEL_NAME: Final[str] = os.getenv(
    "DEFAULT_MODEL_NAME", "gpt-5-mini-2025-08-07"
)
DEFAULT_TEMPERATURE: Final[float] = float(
    os.getenv("DEFAULT_TEMPERATURE", "1.0")
)

# Snowflake Configuration
SNOWFLAKE_CONN_STRING: Final[Optional[str]] = os.getenv(
    "SNOWFLAKE_CONN_STRING", ""
)
SNOWFLAKE_RSA_PRIVATE_KEY: Final[Optional[str]] = os.getenv(
    "SNOWFLAKE_RSA_PRIVATE_KEY", ""
)
