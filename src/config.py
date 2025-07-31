"""Config file for the application."""

import os
from typing import Final
from dotenv import load_dotenv

load_dotenv()

DEBUG: Final[bool] = os.getenv("DEBUG", "false").lower() == "true"
