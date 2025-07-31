"""Interpreter models for the agent."""

from typing import Optional

from pydantic import BaseModel, Field

from src.core.types import Task


class QueryInterpretation(BaseModel):
    """Structured interpretation of user queries."""

    intent: str = Field(
        description="The main action the user wants to perform, e.g., 'create_dashboard'."
    )
    dashboard_name: str = Field(
        description="Name of the dashboard to be created or modified."
    )
    metrics: list[str] = Field(
        description="List of metrics to be included in the dashboard, e.g., ['price', 'returns']."
    )
    entities: list[str] = Field(
        description="List of entities to be analyzed, e.g., ['AAPL', 'Google', 'Education Sector']."
    )
    time_filters: Optional[dict[str, str]] = Field(
        default=None,
        description="Time filters to apply, e.g., {'start': '2024-01-01', 'period': '1Y'}.",
    )
    metric_operations: Optional[dict[str, str]] = Field(
        default=None,
        description="Operations to apply on metrics, e.g., {'price': 'avg', 'returns': 'sum'}.",
    )


class Plan(BaseModel):
    """Structured Plan to follow."""

    tasks: list[Task] = Field(
        ..., description="List of tasks to be executed in the plan."
    )
