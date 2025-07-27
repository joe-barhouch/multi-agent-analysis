"""Core module for multi-agent BI system."""

from .base_agent import BaseAgent
from .models import AgentResult
from .state import GlobalState, WidgetDataRequirements, WidgetSpec
from .types import AgentType

__all__ = [
    "BaseAgent",
    "GlobalState",
    "WidgetSpec",
    "WidgetDataRequirements",
    "AgentResult",
    "AgentType",
]
