"""Data models for the core system."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Standard result format for agent operations."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
