"""Data Preparation Agent Module."""

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
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

        checkpointer = self.config.get("configurable", {}).get("checkpointer")
        if checkpointer is None:
            checkpointer = InMemorySaver()

        self.workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=DATA_PREP_PROMPT.format(TOOLS=tool_info, DATA_SOURCES=data_sources),
            name=self.name,
            checkpointer=checkpointer,
        )
        self.log_activity("Creating workflow for data preparation tasks.")

        return self.workflow

    def setup_responses(self) -> None:
        """Setup Code Interpreter tool with persistent context."""
        model = self.config.get("configurable", {}).get("model")
        client = OpenAI()

        # file = client.files.create(
        #     file=open(
        #         "/Users/joe/joe/personal/multi-agent-analysis/data/finance_economics_dataset.csv",
        #         "rb",
        #     ),
        #     purpose="assistants",
        # )

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
        # Maintain conversation context
        messages = []

        questions = [
            "Read the CSV file and explain the data in the file. (the finance_economics_dataset.csv)"
            "save a monthly average of the close and return columns to a new csv"
        ]

        for q in questions:
            # Add user message
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

            # Get response with full context
            response = await code_model.ainvoke(messages, config=self.config)

            # Add assistant response to maintain context
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

    # Create workflow
    agent.create_workflow()

    # Execute the agent
    import asyncio

    # code_model = agent.setup_responses()

    asyncio.run(agent.run_code_interpreter())

    asyncio.run(agent.execute())
