"""Common type definitions for the multi-agent system."""

from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Available agent types in the system."""

    SUPERVISOR = "supervisor"
    QUERY_INTERPRETER = "query_interpreter"
    DATA_PREP = "data_prep"
    DATA_AGENT = "data_agent"
    VISUALIZATION = "visualization"
    DATA_ANALYST = "data_analyst"


class TaskStatus(str, Enum):
    """Task execution statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Task model for workflow management."""

    id: int = Field(..., description="Unique identifier for the task starting at 1")
    description: str = Field(..., description="Description of the task to be performed")
    status: TaskStatus = Field(
        TaskStatus.PENDING, description="Current status of the task"
    )
