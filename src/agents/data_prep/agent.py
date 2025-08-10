"""Data Prep Agent."""

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_sandbox import PyodideSandboxTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.agents.database_manager import SnowflakeManager as DataManager
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
        state: GlobalState,
        data_manager: DataManager,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Data Prep Agent."""
        super().__init__(
            agent_type=AgentType.DATA_PREP,
            name=name,
            state=state,
            config=config,
            logger=logger,
        )
        self.data_manager = data_manager
        self.name = name

        self.create_workflow()

    def create_workflow(self) -> None:
        """Create the workflow for the data preparation agent."""
        # Input validation
        self.validate_input()

        model = self.config.get("configurable", {}).get("model")

        toolkit = SQLDatabaseToolkit(db=self.data_manager.db, llm=model)
        sqlite_tools = toolkit.get_tools()

        # Try to create sandbox tool, but make it optional for testing
        # sandbox_tool = PyodideSandboxTool(
        #     # Allow Pyodide to install python packages that
        #     # might be required.
        #     allow_net=True,
        #     stateful=True,
        # )

        # Tool descriptions
        tool_info = "\n".join(
            f"<tool>{tool.name}: {tool.description}</tool>" for tool in sqlite_tools
        )
        # if sandbox_tool:
        #     tool_info += f"<tool>{sandbox_tool.name}: {sandbox_tool.description}</tool>"

        print(f"\nTool info: {tool_info}")

        # Create tools list
        tools = list(sqlite_tools)
        # if sandbox_tool:
        #     tools.append(sandbox_tool)

        self.workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=DATA_PREP_PROMPT.format(
                TOOLS=tool_info,
                DATA_SOURCES="""Sources: 
                    - DB: financial_data.db SQLite database
                    - data/finance_economics_dataset.csv CSV file
                   """,
            ),
            name=self.name,
            checkpointer=MemorySaver(),  # Use in-memory saver for simplicity
        )
        self.log_activity("Creating workflow for data preparation tasks.")

        return self.workflow

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

        query = self.state.get("user_query", None)

        if not query:
            self.log_activity("No query provided for data preparation.", level="error")
            return AgentResult(
                success=False,
                data=None,
                error="No query provided for data preparation.",
                metadata={"agent_name": self.name},
            )

        # Call the workflow with proper message format

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
        # Model can be None for testing without API key
        self.log_activity("Input validation completed successfully.")


if __name__ == "__main__":
    # Example usage
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
        state=global_state,
        data_manager=data_manager,
        config=RunnableConfig(
            configurable={
                "model": ChatOpenAI(
                    model="gpt-4.1-mini",
                    temperature=0,
                ),
                "thread_id": "thread-1",
            }
        ),
    )

    # Create workflow
    agent.create_workflow()

    # Execute the agent
    import asyncio

    # code_model = agent.setup_responses()

    asyncio.run(agent.run_code_interpreter())

    asyncio.run(agent.execute())
