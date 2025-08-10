# widgets_schemas.py
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, conint, confloat
import re


# --- Enums ---


class WidgetTypeEnum(str, Enum):
    timeseries = "timeseries"
    table = "table"
    pie = "pie"
    tile = "tile"


class SortOrderEnum(str, Enum):
    asc = "asc"
    desc = "desc"


# --- Common helpers ---

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _is_hex_color(value: str) -> bool:
    return bool(HEX_COLOR_PATTERN.fullmatch(value))


# --- Core schema ---


class QueryAnalysisSchema(BaseModel):
    """Chosen widget type + SQL + reasoning."""

    model_config = ConfigDict(extra="forbid")

    widget_type: WidgetTypeEnum = Field(..., description="Type of widget to build")
    sql_query: str = Field(..., description="SQL query to fetch the data")
    reasoning: str = Field(..., description="Why this widget/query makes sense")


# --- Timeseries ---


class TimeseriesConfigSchema(BaseModel):
    """Config for a time series chart."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Clear, descriptive chart title")
    series_name: Optional[str] = Field(None, description="Name for the data series")
    x_axis_label: Optional[str] = Field(None, description="Label for time axis")
    y_axis_label: Optional[str] = Field(None, description="Label for value axis")
    time_field: str = Field(..., description="Column with time/date values")
    value_field: str = Field(..., description="Column with numeric values to plot")
    line_color: Optional[str] = Field(None, description="Hex color (e.g., #FF0000)")
    show_points: Optional[bool] = Field(
        None, description="Show data points on the line"
    )
    date_format: Optional[str] = Field(None, description="e.g., YYYY-MM-DD")
    value_prefix: Optional[str] = Field(None, description="Prefix (e.g., '$')")
    value_suffix: Optional[str] = Field(None, description="Suffix (e.g., '%')")

    @field_validator("line_color")
    @classmethod
    def validate_line_color(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not _is_hex_color(value):
            raise ValueError("line_color must be a hex color like #RRGGBB or #RGB")
        return value


# --- Pie ---


class PieConfigSchema(BaseModel):
    """Config for a pie/donut chart."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Clear, descriptive chart title")
    name_field: str = Field(..., description="Column with category names")
    value_field: str = Field(..., description="Column with values per slice")
    show_percentages: Optional[bool] = Field(None, description="Show % on slices")
    show_legend: Optional[bool] = Field(None, description="Show legend")
    colors: Optional[List[str]] = Field(None, description="Hex colors for slices")
    inner_radius: Optional[confloat(ge=0.0, le=1.0)] = Field(
        None, description="0-1; 0=full pie, >0=donut"
    )
    value_prefix: Optional[str] = Field(None, description="Prefix for values")
    value_suffix: Optional[str] = Field(None, description="Suffix for values")

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        for c in value:
            if not _is_hex_color(c):
                raise ValueError(f"Invalid hex color: {c}")
        return value


# --- Table ---


class TableConfigSchema(BaseModel):
    """Config for a data table widget."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Clear, descriptive table title")
    columns_to_show: Optional[List[str]] = Field(None, description="Columns to display")
    column_labels: Optional[Dict[str, str]] = Field(
        None, description="Map raw column -> display label"
    )
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_order: Optional[SortOrderEnum] = Field(None, description="asc or desc")
    max_rows: Optional[conint(ge=1)] = Field(
        None, description="Max number of rows to display"
    )
    value_prefix: Optional[str] = Field(None, description="Prefix for numeric values")
    value_suffix: Optional[str] = Field(None, description="Suffix for numeric values")


# --- Tile ---


class TileConfigSchema(BaseModel):
    """Config for a KPI/metric tile."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Descriptive tile title")
    metric_value: str = Field(..., description="Column containing the metric value")
    metric_label: str = Field(..., description="Human-readable metric label")
    subtitle: Optional[str] = Field(None, description="Additional context/subtitle")
    format_as_currency: Optional[bool] = Field(
        None, description="Format value as currency"
    )
    show_trend: Optional[bool] = Field(None, description="Show trend indicator")
    trend_field: Optional[str] = Field(None, description="Column for trend calculation")
    value_prefix: Optional[str] = Field(None, description="Prefix for value")
    value_suffix: Optional[str] = Field(None, description="Suffix for value")
