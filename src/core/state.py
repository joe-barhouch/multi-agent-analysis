"""Global state schema for the multi-agent BI system."""

from typing import TYPE_CHECKING, Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

if TYPE_CHECKING:
    from src.agents.interpreter.models import QueryInterpretation

from .types import Task


class WidgetDataRequirements(BaseModel):
    """Data requirements for dashboard widgets."""

    widget_id: str
    widget_type: str  # "line_chart", "table", "kpi_card", "heatmap"
    data_format: str  # "time_series", "snapshot", "aggregated"
    main_columns: List[str]
    additional_columns: List[str] = []
    aggregation_level: str  # "daily", "company", "portfolio"


class WidgetSpec(BaseModel):
    """Complete widget specification."""

    widget_id: str
    widget_type: str
    config: Dict  # JSON spec for visualization library
    data_requirements: WidgetDataRequirements
    position: Dict  # {"x": 0, "y": 0, "w": 6, "h": 4}


class GlobalState(TypedDict):
    """Shared state across all agents in the system."""

    # Core conversation state
    user_query: str
    session_id: str
    conversation_history: List[BaseMessage]
    
    # Chat history configuration
    max_messages: Optional[int]
    enable_trimming: bool

    # Interpretation and planning
    interpreted_query: Optional["QueryInterpretation"]
    todo_plan: List[Task]
    current_task: Optional[str]

    # Dashboard state
    dashboard_layout: Dict
    widget_specs: Dict[str, WidgetSpec]
    widget_data_queries: Dict[str, Dict]  # {widget_id: {sql: str, pandas: str}}

    # Data state
    available_tables: List[Dict]  # Schema information
    created_subtables: List[str]
    data_descriptions: Dict[str, str]

    # Execution state
    errors: List[Dict]
    warnings: List[Dict]

    # Agent communication
    current_agent: Optional[str]
    agent_history: List[str]


class MessagesState(TypedDict):
    """LangGraph-compatible state for message handling."""
    
    messages: Annotated[List[BaseMessage], add_messages]
