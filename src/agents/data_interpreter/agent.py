"""Data Interpretation Agent that runs Python code on DataFrames."""

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_sandbox import PyodideSandboxTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from src.config import DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from src.core.base_agent import BaseAgent
from src.core.models import AgentResult
from src.core.state import GlobalState
from src.core.types import AgentType

from .prompts import ANALYSIS_PROMPT_TEMPLATE, DATA_INTERPRETATION_PROMPT


class DataInterpretationAgent(BaseAgent):
    """Agent that interprets data by running Python code on DataFrames."""

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        local_state: dict | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        super().__init__(
            agent_type=AgentType.DATA_INTERPRETATION,
            name=name,
            state=local_state,
            config=config,
            logger=logger,
        )
        self.local_state = local_state
        self.global_state = global_state
        self.name = name
        self.create_workflow()

    def gs_get(self, key: str, default=None):
        """Safely get a value from global state."""
        return self.global_state.get(key, default)

    def gs_set(self, key: str, value):
        """Safely set a value in global state."""
        self.global_state[key] = value
        self.log_activity(f"Stored {key} in global state")

    def create_workflow(self) -> None:
        """Create workflow for data interpretation."""
        self.validate_input()

        model = self.config.get("configurable", {}).get("model")
        if model is None:
            api_key = self.config.get("configurable", {}).get("api_key")
            if api_key:
                try:
                    model = ChatOpenAI(
                        model=DEFAULT_MODEL_NAME,
                        temperature=DEFAULT_TEMPERATURE,
                        api_key=api_key,
                    )
                except Exception as e:
                    self.log_activity(
                        f"Could not create OpenAI model: {e}", level="warning"
                    )
                    self.workflow = None
                    return
            else:
                self.log_activity(
                    "Could not create model - check API key configuration",
                    level="warning",
                )
                self.workflow = None
                return

        tools = []
        try:
            sandbox_tool = PyodideSandboxTool(allow_net=False, stateful=True)
            self.sandbox_tool = sandbox_tool
            tools.append(sandbox_tool)
        except Exception as e:
            self.log_activity(f"Could not create sandbox tool: {e}", level="error")
            self.workflow = None
            return

        @tool("load_and_analyze_dataframe")
        async def _load_and_analyze_dataframe() -> str:
            """Load DataFrame from global state and perform comprehensive analysis without sandbox."""
            df = self.gs_get("dataframe")
            if df is None:
                return "Error: No dataframe found in global state. Please ensure data_prep agent has executed successfully and stored a DataFrame."

            try:
                import pandas as pd

                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")

                for col in ["price", "close", "open", "high", "low"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                analysis_results = []

                analysis_results.append("=== DATA OVERVIEW ===")
                analysis_results.append(f"Shape: {df.shape}")
                analysis_results.append(f"Columns: {list(df.columns)}")
                analysis_results.append(f"Data types: {df.dtypes.to_dict()}")

                analysis_results.append("\n=== STATISTICAL SUMMARY ===")
                desc = df.describe(include="all")
                analysis_results.append(desc.to_string())

                analysis_results.append("\n=== MIN/MAX ANALYSIS ===")
                numeric_cols = df.select_dtypes(include=["number"]).columns

                for col in numeric_cols:
                    if df[col].notna().any():
                        min_val = df[col].min()
                        max_val = df[col].max()
                        min_idx = df[col].idxmin()
                        max_idx = df[col].idxmax()

                        analysis_results.append(f"\n{col.upper()}:")
                        analysis_results.append(f"  Maximum: {max_val} (Row {max_idx})")
                        analysis_results.append(f"  Minimum: {min_val} (Row {min_idx})")

                        if "date" in df.columns:
                            max_date = (
                                df.loc[max_idx, "date"]
                                if max_idx in df.index
                                else "N/A"
                            )
                            min_date = (
                                df.loc[min_idx, "date"]
                                if min_idx in df.index
                                else "N/A"
                            )
                            analysis_results.append(f"  Max occurred on: {max_date}")
                            analysis_results.append(f"  Min occurred on: {min_date}")

                analysis_results.append("\n=== ANOMALY DETECTION ===")
                for col in numeric_cols:
                    if df[col].notna().any():
                        Q1 = df[col].quantile(0.25)
                        Q3 = df[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR

                        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                        analysis_results.append(
                            f"{col}: {len(outliers)} potential outliers detected"
                        )

                        if len(outliers) > 0 and len(outliers) <= 5:
                            for idx, row in outliers.iterrows():
                                analysis_results.append(
                                    f"  Outlier: {row[col]:.2f} at index {idx}"
                                )
                                if "date" in df.columns:
                                    analysis_results.append(f"    Date: {row['date']}")

                if "date" in df.columns and len(numeric_cols) > 0:
                    analysis_results.append("\n=== TREND ANALYSIS ===")
                    df_sorted = df.sort_values("date").reset_index(drop=True)

                    for col in numeric_cols:
                        if df_sorted[col].notna().any():
                            values = df_sorted[col].dropna()
                            if len(values) > 1:
                                first_val = values.iloc[0]
                                last_val = values.iloc[-1]
                                change = last_val - first_val
                                pct_change = (
                                    (change / first_val * 100) if first_val != 0 else 0
                                )

                                analysis_results.append(f"{col}:")
                                analysis_results.append(
                                    f"  First value: {first_val:.2f}"
                                )
                                analysis_results.append(f"  Last value: {last_val:.2f}")
                                analysis_results.append(
                                    f"  Change: {change:.2f} ({pct_change:.1f}%)"
                                )

                                if pct_change > 5:
                                    analysis_results.append(
                                        "  Trend: Upward (significant increase)"
                                    )
                                elif pct_change < -5:
                                    analysis_results.append(
                                        "  Trend: Downward (significant decrease)"
                                    )
                                else:
                                    analysis_results.append(
                                        "  Trend: Relatively stable"
                                    )

                analysis_results.append("\n=== DATA QUALITY ===")
                null_counts = df.isnull().sum()
                analysis_results.append("Missing values per column:")
                for col, null_count in null_counts.items():
                    if null_count > 0:
                        analysis_results.append(
                            f"  {col}: {null_count} missing ({null_count / len(df) * 100:.1f}%)"
                        )

                if null_counts.sum() == 0:
                    analysis_results.append(
                        "  No missing values found - excellent data quality!"
                    )

                self.log_activity(
                    f"Successfully analyzed DataFrame with shape {df.shape}"
                )
                return "\n".join(analysis_results)

            except Exception as e:
                error_msg = f"Failed to analyze DataFrame: {str(e)}"
                self.log_activity(error_msg, level="error")
                return error_msg

        tools.append(_load_and_analyze_dataframe)

        enhanced_prompt = DATA_INTERPRETATION_PROMPT

        self.workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=enhanced_prompt,
            name=self.name,
            checkpointer=InMemorySaver(),
        )

    async def execute(self) -> AgentResult:
        """Execute data interpretation by running Python code."""
        self.log_activity("Executing data interpretation with Python analysis.")

        if self.workflow is None:
            self.log_activity("Workflow not initialized", level="error")
            return AgentResult(
                success=False,
                data=None,
                error="Workflow not initialized - check configuration.",
                metadata={"agent_name": self.name},
            )

        dataframe_data = self.gs_get("dataframe")
        user_query = self.gs_get("user_query", "")
        sql_query = self.gs_get("sql_query_executed", "")

        if dataframe_data is None:
            self.log_activity(
                "No DataFrame available for interpretation.", level="warning"
            )
            return AgentResult(
                success=False,
                data=None,
                error="No DataFrame available for interpretation. Ensure data_prep has executed successfully.",
                metadata={"agent_name": self.name},
            )

        analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            user_query=user_query,
            sql_query=sql_query,
            dataframe_rows=dataframe_data.shape[0],
            dataframe_cols=dataframe_data.shape[1],
        )

        response = await self.workflow.ainvoke(
            {"messages": [HumanMessage(content=analysis_prompt)]},
            config=self.config,
        )

        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name},
        )

    def validate_input(self) -> None:
        """Validate input configuration."""
        if not self.config:
            raise ValueError("Configuration is required for DataInterpretationAgent.")
        self.log_activity("Input validation completed successfully.")
