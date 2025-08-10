"""Common type definitions for the multi-agent system."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Available agent types in the system."""

    SUPERVISOR = "supervisor"
    QUERY_INTERPRETER = "query_interpreter"
    DATA_PREP = "data_prep"
    DATA_AGENT = "data_agent"
    VISUALISATION = "visualisation"
    DATA_ANALYST = "data_analyst"


# Supervisor
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


class Plan(BaseModel):
    """Structured Plan to follow."""

    tasks: list[Task] = Field(
        ..., description="List of tasks to be executed in the plan."
    )


# Query Interpreter
class TimeFilter(BaseModel):
    """Flexible time window for metric queries."""

    start_date: Optional[str] = Field(
        default=None, description="Start date (YYYY-MM-DD), if applicable."
    )
    period: Optional[str] = Field(
        default=None,
        description="Relative period such as '1Y', '6M', etc. if applicable. Covers phrases like 'last year', 'last 6 months', etc.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End date (YYYY-MM-DD) – may be omitted. If omitted, the current date is used.",
    )

    # Accept whatever the LLM hands back (extra keys or missing keys)
    model_config = {"extra": "allow"}


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
    time_filters: Optional[TimeFilter] = Field(
        default=None,
        description="Time filters to apply",
    )
    metric_operations: Optional[dict[str, str]] = Field(
        default=None,
        description="Operations to apply on metrics, e.g., {'price': 'avg', 'returns': 'sum'}.",
    )


# Visualisation
class WidgetTypeEnum(Enum):
    CONTINUOUS_CARTESIAN = "continuousCartesian"
    CATEGORICAL_CARTESIAN = "categoricalCartesian"
    MAP_GEO = "mapGeo"
    PIE = "pie"
    TABLE_GRID = "tableGrid"
    TILE = "tile"
    TILE_MATRIX = "tileMatrix"
    TIMESERIES = "timeseries"


class WidgetDescription(BaseModel):
    """Description of a widget to be created."""

    id: float = Field(
        ...,
        description="Id of the widget starting at 1.0. Each new widget is a new integer, if there are parent-child widgets, then the id is Parent Id.1, incrementing the decimals ",
    )
    name: str = Field(..., description="Super short name for the widget")
    widget_type: WidgetTypeEnum = Field(..., description="Type of the widget")
    description: str = Field(
        ...,
        description="Detailed description on how the widget should have. Concise but explaining all elements required like the columns, type, axis...",
    )
    main_columns: list[str] = Field(
        ..., description="Main columns to be displayed in the widget"
    )
    additional_columns: list[str] = Field(
        default_factory=list, description="Additional columns for the widget"
    )
    aggregation_level: str = Field(
        ..., description="Level of aggregation for the data (e.g., 'daily', 'company')"
    )
    need_children: bool = Field(
        default=False,
        description="True if the widget can be clicked on to create links to children widgets",
    )


class WidgetQueries(BaseModel):
    """List of Descriptions of queries to be executed for each widget."""

    queries: list[WidgetDescription] = Field(
        ..., description="List of widget queries to be executed"
    )


class DashboardLayout(BaseModel):
    """Layout of the overall dashboard."""

    layout: list[dict] = Field(
        ..., description="List of layout specifications for the dashboard"
    )


# Data Preparation
class TableInfo(BaseModel):
    """Information about a table in the database."""

    name: str
    columns: list[str]  # List of column names
    description: str  # Description of the table
    table_schema: str  # Schema of the table


class DataInfo(BaseModel):
    """Information about the data in the system."""

    tables: list[TableInfo]  # List of available tables
