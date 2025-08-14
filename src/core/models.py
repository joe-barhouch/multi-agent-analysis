"""Data models for the core system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


@dataclass
class AgentResult:
    """Standard result format for agent operations."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskStatus(str, Enum):
    """Task execution statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Task model for workflow management."""

    id: int = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Description of the task")
    status: TaskStatus = Field(
        TaskStatus.PENDING, description="Current status of the task"
    )


class TimeFilter(BaseModel):
    """Flexible time window for metric queries."""

    start_date: Optional[str] = Field(
        default=None, description="Start date (YYYY-MM-DD), if applicable."
    )
    period: Optional[str] = Field(
        default=None,
        description="Relative period such as '1Y', '6M', etc.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date (YYYY-MM-DD) – may be omitted.",
    )

    # Accept whatever the LLM hands back (extra keys or missing keys)
    model_config = {"extra": "allow"}


class QueryInterpretation(BaseModel):
    """Structured interpretation of user queries."""

    intent: str = Field(
        description="The main action the user wants to perform."
    )
    dashboard_name: str = Field(
        description="Name of the dashboard to be created or modified."
    )
    metrics: list[str] = Field(
        description="List of metrics to be included in the dashboard."
    )
    entities: list[str] = Field(
        description="List of entities to be analyzed."
    )
    time_filters: Optional[TimeFilter] = Field(
        default=None,
        description="Time filters to apply",
    )
    metric_operations: Optional[dict[str, str]] = Field(
        default=None,
        description="Operations to apply on metrics.",
    )


class Plan(BaseModel):
    """Structured Plan to follow."""

    tasks: list[Task] = Field(
        ..., description="List of tasks to be executed in the plan."
    )
