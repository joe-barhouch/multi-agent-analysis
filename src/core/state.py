"""Global state schema for the multi-agent BI system."""

from typing import Dict, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.agents.interpreter.models import Plan, QueryInterpretation


class WidgetDataRequirements(BaseModel):
    """Data requirements for dashboard widgets."""

    widget_id: str
    widget_type: str  # "line_chart", "table", "kpi_card", "heatmap"
    data_format: str  # "time_series", "snapshot", "aggregated"
    main_columns: list[str]
    additional_columns: list[str] = []
    aggregation_level: str  # "daily", "company", "portfolio"


class WidgetSpec(BaseModel):
    """Complete widget specification."""

    widget_id: str
    widget_type: str
    config: Dict  # JSON spec for visualization library
    data_requirements: WidgetDataRequirements
    position: Dict  # {"x": 0, "y": 0, "w": 6, "h": 4}


class AgentConfig(TypedDict):
    """Configuration for agents in the system."""

    model: ChatOpenAI


class GlobalState(TypedDict):
    """Shared state across all agents in the system."""

    # Core conversation state
    user_query: str
    session_id: str
    conversation_history: list[BaseMessage]

    # Chat history configuration
    max_messages: Optional[int]
    enable_trimming: bool

    # Interpretation and planning
    interpreted_query: Optional[QueryInterpretation]
    plan: Plan
    current_task: Optional[str]

    # Dashboard state
    dashboard_layout: dict
    widget_specs: dict[str, WidgetSpec]
    widget_data_queries: dict[str, dict]  # {widget_id: {sql: str, pandas: str}}

    # Data state
    available_tables: list[Dict]  # Schema information
    created_subtables: list[str]
    data_descriptions: dict[str, str]

    # Execution state
    errors: list[Dict]
    warnings: list[Dict]

    # Agent communication
    current_agent: Optional[str]
    agent_history: list[str]
