"""Global state schema for the multi-agent BI system."""

from typing import Optional, TypedDict

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt.chat_agent_executor import AgentState

from src.core.types import (
    DashboardLayout,
    DataInfo,
    Plan,
    QueryInterpretation,
    WidgetQueries,
)


class AgentConfig(TypedDict):
    """Configuration for agents in the system."""

    model: ChatOpenAI
    tool_model: ChatOpenAI


# class GlobalState(TypedDict):
class GlobalState(AgentState):
    """Shared state across all agents in the system."""

    # Core conversation state
    user_query: str
    conversation_history: list[BaseMessage]
    # messages: list[BaseMessage]  # All messages in the conversation

    # Interpretation and planning
    query_interpretation: Optional[QueryInterpretation]
    plan: Plan

    # Dashboard state
    dashboard_layout: DashboardLayout
    widget_specs: WidgetQueries
    widget_data_queries: dict[str, dict]  # {widget_id: {sql: str, pandas: str}}

    # Data state
    available_tables: DataInfo
    data_descriptions: dict[str, str]

    # Execution state
    errors: list[str]
    warnings: list[str]

    # Agent communication
    agent_history: list[str]
