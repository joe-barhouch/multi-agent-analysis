"""Data Preparation Agent Module with DataFrame Storage."""

import pandas as pd
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_sandbox import PyodideSandboxTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from openai import OpenAI

from src.agents.database_manager import SnowflakeManager as DataManager
from src.config import DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from src.core.base_agent import BaseAgent
from src.core.models import AgentResult
from src.core.state import GlobalState
from src.core.types import AgentType

from .prompts import DATA_PREP_PROMPT


class DataPrepAgent(BaseAgent):
    """Agent responsible for data preparation tasks."""

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        data_manager: DataManager,
        local_state: StateGraph | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Data Prep Agent."""
        super().__init__(
            agent_type=AgentType.DATA_PREP,
            name=name,
            state=local_state,
            config=config,
            logger=logger,
        )
        self.local_state = local_state
        self.global_state = global_state
        self.data_manager = data_manager
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
        self.validate_input()

        model = self.config.get("configurable", {}).get("model")
        if model is None:
            self.log_activity("No model provided in config", level="error")
            self.workflow = None
            return

        tools = self.config.get("configurable", {}).get("data_tools")
        tool_info = self.config.get("configurable", {}).get("tool_info")
        data_sources = (
            self.config.get("configurable", {}).get("data_sources")
            or "Sources: (unspecified)"
        )

        if not tools:
            toolkit = SQLDatabaseToolkit(db=self.data_manager.db, llm=model)
            tools = toolkit.get_tools()
            try:
                sandbox_tool = PyodideSandboxTool(allow_net=True, stateful=True)
                tools.append(sandbox_tool)
            except Exception:
                pass
            tool_info = "\n".join(
                f"<tool>{t.name}: {getattr(t, 'description', '')}</tool>" for t in tools
            )

        @tool("execute_sql_and_store_dataframe")
        async def execute_sql_and_store_dataframe(sql_query: str) -> str:
            """Execute SQL query and store the resulting DataFrame in global state.

            Args:
                sql_query: The SQL query to execute

            Returns:
                String description of the execution result and DataFrame info
            """
            try:
                self.log_activity(f"Executing SQL query: {sql_query}")

                if hasattr(self.data_manager.db, "_engine"):
                    df = pd.read_sql(sql_query, self.data_manager.db._engine)
                else:
                    result = self.data_manager.db.run(sql_query)
                    if isinstance(result, str):
                        lines = result.strip().split("\n")
                        if len(lines) > 1:
                            headers = (
                                lines[0].split("\t")
                                if "\t" in lines[0]
                                else lines[0].split()
                            )
                            data_rows = []
                            for line in lines[1:]:
                                row = line.split("\t") if "\t" in line else line.split()
                                data_rows.append(row)
                            df = pd.DataFrame(data_rows, columns=headers)
                        else:
                            return f"Query executed but returned: {result}"
                    else:
                        df = pd.DataFrame(result)

                self.gs_set("dataframe", df)
                self.gs_set("sql_query_executed", sql_query)

                info = "Successfully executed SQL query and stored DataFrame:\n"
                info += f"- Shape: {df.shape}\n"
                info += f"- Columns: {list(df.columns)}\n"
                info += f"- First few rows:\n{df.head().to_string()}"

                self.log_activity(f"DataFrame stored with shape {df.shape}")

                return info

            except Exception as e:
                error_msg = f"Error executing SQL query: {str(e)}"
                self.log_activity(error_msg, level="error")
                return error_msg

        tools.append(execute_sql_and_store_dataframe)

        tool_info += "\n<tool>execute_sql_and_store_dataframe: Execute SQL query and store the resulting DataFrame in global state for further analysis</tool>"

        checkpointer = self.config.get("configurable", {}).get("checkpointer")
        if checkpointer is None:
            checkpointer = InMemorySaver()

        updated_prompt = DATA_PREP_PROMPT.format(
            TOOLS=tool_info, DATA_SOURCES=data_sources
        )

        self.workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=updated_prompt,
            name=self.name,
            checkpointer=checkpointer,
        )
        self.log_activity("Creating workflow for data preparation tasks.")

        return self.workflow

    def setup_responses(self) -> None:
        """Setup Code Interpreter tool with persistent context."""
        model = self.config.get("configurable", {}).get("model")
        client = OpenAI()

        container = client.containers.create(name="code_interpreter_container")

        chat_model = ChatOpenAI(
            model=model.model_name,
            output_version="responses/v1",
            use_responses_api=True,
            use_previous_response_id=True,
        )
        code_model = chat_model.bind_tools(
            [
                {
                    "type": "code_interpreter",
                    "container": container.id,
                    "files": ["file-AhTVPQ698NboD96RqD6MpX"],
                },
            ]
        )

        self.code_model = code_model

        return code_model

    async def run_code_interpreter(self) -> None:
        code_model = self.setup_responses()
        messages = []

        questions = [
            "Read the CSV file and explain the data in the file. (the finance_economics_dataset.csv)"
            "save a monthly average of the close and return columns to a new csv"
        ]

        for q in questions:
            messages.append(
                HumanMessage(
                    content=q,
                    additional_kwargs={
                        "attachments": [
                            {
                                "files": "file-AhTVPQ698NboD96RqD6MpX",
                            }
                        ]
                    },
                )
            )

            response = await code_model.ainvoke(messages, config=self.config)

            messages.append({"role": "assistant", "content": response.content})

            self.log_activity(f"Code Interpreter response: {response.content}")
            print(f"Code Interpreter response: {response.content}")

    async def execute(self) -> AgentResult:
        """Execute data preparation tasks."""
        self.log_activity("Executing data preparation tasks.")

        if self.workflow is None:
            self.log_activity(
                "Workflow not initialized - likely missing API key", level="error"
            )
            return AgentResult(
                success=False,
                data=None,
                error="Workflow not initialized - check API key configuration.",
                metadata={"agent_name": self.name},
            )

        query = self.global_state.get("user_query", None)

        if not query:
            self.log_activity("No query provided for data preparation.", level="error")
            return AgentResult(
                success=False,
                data=None,
                error="No query provided for data preparation.",
                metadata={"agent_name": self.name},
            )

        response = await self.workflow.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config=self.config,
        )

        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name},
        )

    def validate_input(self) -> None:
        """Validate the input configuration for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for DataPrepAgent.")
        self.log_activity("Input validation completed successfully.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    from src.core.state import GlobalState

    load_dotenv()

    global_state = GlobalState(
        user_query="Compute the average of 3215 - cos(45)",
    )

    data_manager = DataManager("financial_data.db")
    data_manager.get_sql_database()

    agent = DataPrepAgent(
        name="DataPrepAgent",
        global_state=global_state,
        data_manager=data_manager,
        config=RunnableConfig(
            configurable={
                "model": ChatOpenAI(
                    model=DEFAULT_MODEL_NAME, temperature=DEFAULT_TEMPERATURE
                ),
                "thread_id": "thread-1",
            }
        ),
    )

    agent.create_workflow()

    import asyncio

    asyncio.run(agent.execute())
