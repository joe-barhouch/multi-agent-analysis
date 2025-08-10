"""Widget descriptions."""

WIDGET_TYPE_DESCRIPTIONS = {
    WidgetTypeEnum.CONTINUOUS_CARTESIAN: """
**Continuous Cartesian Chart Widget**

**How it works:** Creates 2D coordinate system plots with continuous X and Y axes for visualizing relationships between two continuous variables.

**Base data required:**
- Two continuous numeric columns for X and Y positioning
- Optional: Additional numeric column for bubble sizes or point labels

**Supported series types:**
- Line charts, scatter plots, column/bar charts, area charts, bubble charts
- Error bars and range visualizations

**Features:**
- Multiple series on same chart with dual Y-axes support
- Interactive tooltips and legends
- Time-based playback for animated visualizations
- Reference lines and configurable axis scales
""",
    WidgetTypeEnum.CATEGORICAL_CARTESIAN: """
**Categorical Cartesian Chart Widget**

**How it works:** Creates charts with discrete categories on one axis and continuous values on the other, ideal for comparing data across different categories.

**Base data required:**
- One categorical column for grouping/categories
- One or more numeric columns for values
- Optional: Additional categorical column for stacking groups

**Supported series types:**
- Column/bar charts with stacking support
- Line charts, area charts, scatter plots, bubble charts

**Features:**
- Horizontal or vertical orientation
- Stacking capability for multiple series
- Multiple value axes and category-based tooltips
- Time-based playback for animated categorical data
""",
    WidgetTypeEnum.MAP_GEO: """
**Geographic Map Widget**

**How it works:** Displays data on a world map using country boundaries, with support for choropleth coloring and animated playback over time.

**Base data required:**
- Country codes (ISO format) for geographic positioning
- Numeric values for data visualization per country
- Optional: Time/date column for animated playback

**Features:**
- Choropleth maps with color-coded countries
- Interactive country tooltips
- Time-based animations for temporal geographic data
- Support for multiple data series on same map

**Notes:**
- Does not support city-level, region-level, or latitude/longitude data, only country-level data
""",
    WidgetTypeEnum.PIE: """
**Pie Chart Widget**

**How it works:** Creates circular charts where data is represented as slices, with each slice's size proportional to its value in the dataset.

**Base data required:**
- One categorical column for slice categories
- One numeric column for slice values/proportions
- Optional: Country codes for country-specific pie charts

**Features:**
- Proportional slice sizing based on values
- Interactive tooltips for each slice
- Support for country flags in country-based charts
- Custom color specifications and legend positioning
""",
    WidgetTypeEnum.TABLE_GRID: """
**Table Grid Widget**

**How it works:** Displays data in a structured table format with advanced features like sorting, filtering, pagination, and embedded visualizations.

**Base data required:**
- Tabular data with multiple columns of various types
- Column headers and row data
- Optional: Summary/aggregate data for totals rows

**Supported column types:**
- Text, numeric, date/time, country, and category columns
- Action columns with hyperlinks
- Embedded chart columns (line, area, column, pie, stacked bar)

**Features:**
- Search, filtering, and sorting capabilities
- Row selection and pagination
- Embedded visualizations within table cells
- Column styling and formatting options
""",
    WidgetTypeEnum.TILE: """
**Tile Widget**

**How it works:** Displays key metrics and KPIs in a compact card format with optional header, main content, and embedded charts.

**Base data required:**
- One or more metric values (numeric, text, or date columns)
- Optional: Time series data for embedded trend charts

**Supported content types:**
- Numbers with various formatting (currency, percentages, scales)
- Text with styling options
- Date/time displays
- Embedded charts: line, area, column, stacked bar

**Features:**
- Compact metric display with rich styling
- Embedded spark charts for trend visualization
- Interactive tooltips and action links
- Configurable layouts and separators
""",
    WidgetTypeEnum.TILE_MATRIX: """
**Tile Matrix Widget**

**How it works:** Displays multiple tiles in a grid layout, each showing different metrics or KPIs, ideal for dashboard overviews.

**Base data required:**
- Multiple rows of data, each representing one tile
- Consistent column structure across all tiles
- Metric values for each tile (numeric, text, or date columns)

**Features:**
- Grid layout of multiple tiles
- Consistent styling and formatting across tiles
- Each tile supports same features as single Tile widget
- Responsive grid sizing and arrangement
""",
    WidgetTypeEnum.TIMESERIES: """
**Time Series Widget**

**How it works:** Specialized visualization for temporal data with time-based X-axis and support for multiple time series with navigation and zoom controls.

**Base data required:**
- Time/date column for temporal positioning
- One or more numeric columns for measurements over time
- Optional: Additional columns for multiple series comparison

**Supported visualizations:**
- Line charts showing trends over time
- Area charts for cumulative data
- Multiple series comparison on same timeline

**Features:**
- Time-based X-axis with intelligent date/time formatting
- Zoom and pan functionality for time navigation
- Multiple Y-axes for different value scales
- Interactive tooltips with time-based data
""",
}


WIDGET_SPECIFIC_RULES = {
    WidgetTypeEnum.TIMESERIES: """
        "- Always include the main periods of time in the periodSelector",
        "- Set periodSelector.isDatePickerVisible to true for maximum date selection flexibility",
        "- Use appropriate chart types (line, area, column, scatter, bubble) based on data characteristics",
        "- Enable crosshair on both X and Y axes for better data point identification",
        "- Set legend position to 'BOTTOM' for better space utilization",
        "- For multiple series, use distinct colors and ensure showInLegend is true",
        "- Apply appropriate number formatting with proper scale (BASE, PERCENTAGE, etc.)",
        "- Include tooltip items for all relevant data points",
        "- Use area stacking when showing cumulative or part-to-whole relationships",
        "- Set appropriate axis scales (dynamic, positive, negative, symmetrical) based on data range",
    """,
    WidgetTypeEnum.CATEGORICAL_CARTESIAN: """
        "- Set chart direction to 'VERTICAL' for better readability unless data suggests otherwise",
        "- Use stacking for area and column series when showing part-to-whole relationships",
        "- Enable crosshair on category axis for better data point identification",
        "- Set legend position to 'BOTTOM' for better space utilization",
        "- Use appropriate series types (column, line, area, scatter, bubble) based on data characteristics",
        "- Apply proper number formatting with scale appropriate to data magnitude",
        "- Include playback configuration if data has temporal or sequential dimensions",
        "- Set enableAreaStacking to true when showing cumulative data",
        "- Use appropriate axis scales and tick amounts for optimal readability",
    """,
    WidgetTypeEnum.CONTINUOUS_CARTESIAN: """
        - Use scatter series for correlation analysis and bubble series for three-dimensional data",
        - Set appropriate axis scales (dynamic, positive, negative, symmetrical) based on data distribution",
        - Enable crosshair on both axes for precise data point identification",
        - Use trend lines and reference lines when showing relationships or benchmarks",
        - Apply logarithmic scales when data spans multiple orders of magnitude",
        - Include country entities when data represents geographical information",
        - Set bubble sizes appropriately with maxSizePercentage and minSizePercentage",
        - Use color specifications to encode additional data dimensions",
    """,
    WidgetTypeEnum.MAP_GEO: """
        - Only use when data contains valid country codes (ISO 2 or 3 letter codes)
        - Include playback configuration for temporal geographical data
        - Set appropriate color scales for choropleth mapping
        - Use discrete color maps for categorical geographical data
        - Enable country tooltips with proper formatting
        - Set zoom and center appropriately for the geographical scope of data
        - Use gradient color specifications for continuous geographical variables
    """,
    WidgetTypeEnum.PIE: """
        - Limit to 7 or fewer categories for optimal readability
        - Sort slices by value (largest to smallest) for better visual impact
        - Use 'donut' style for better label placement when space is limited
        - Include percentage values in labels for part-to-whole understanding
        - Set appropriate colors using discrete color maps
        - Enable data labels and legend for complete information
        - Use exploded slices sparingly to highlight specific categories
    """,
    WidgetTypeEnum.TABLE_GRID: """
        - Enable hasSearchBox for tables with more than 20 rows
        - Set hasHeaderFilter to true for columns with distinct categorical values
        - Use appropriate column types (text, number, dateTime, category, country) based on data types
        - Apply proper number formatting with appropriate decimal places and scales
        - Set sortable to true for quantitative and ordinal columns
        - Use rowSelection > 0 when user interaction is needed",
        - Enable groupColumns for hierarchical data organization",
        - Set appropriate column alignment (LEFT for text, RIGHT for numbers, CENTER for categories)",
        - Use styling options (color bars, arrows, dots) to enhance data comprehension",
        - Include summary rows for aggregate information when appropriate",
        - Set defaultState.rowsPerPage based on data volume (10-50 rows per page)",
    """,
    WidgetTypeEnum.TILE: """
        - Focus on a single key metric or KPI",
        - Use large, prominent number formatting for primary value",
        - Include comparison values (previous period, target, benchmark) when available",
        - Apply appropriate color coding for status indication (green/red for good/bad)",
        - Use percentage or change indicators for context",
        - Keep supporting text minimal and focused",
        - Include trend indicators (arrows, mini charts) when showing change over time",
    """,
    WidgetTypeEnum.TILE_MATRIX: """
        - Organize tiles in logical groupings (by category, importance, or functional area)",
        - Use consistent formatting and scales across related tiles",
        - Apply color coding systematically across the matrix",
        - Include drill-down capabilities for detailed analysis",
        - Set appropriate tile sizes based on information hierarchy",
        - Use comparative layouts to show relationships between metrics",
        - Include sparklines or mini charts for trend information",
    """,
}
