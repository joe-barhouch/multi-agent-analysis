"""Interpreter Agent."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.agents.interpreter.models import QueryInterpretation
from src.agents.interpreter.prompts import INTERPRETER_PROMPT
from src.core.models import AgentResult
from src.core.types import AgentType
from src.core.base_agent import BaseAgent
from src.core.state import GlobalState


class InterpreterAgent(BaseAgent):
    """Agent responsible for Query Interpretation."""

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        local_state: GlobalState | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Data Prep Agent."""
        super().__init__(
            agent_type=AgentType.QUERY_INTERPRETER,
            name=name,
            state=local_state,
            config=config,
            logger=logger,
        )
        self.local_state = local_state
        self.global_state = global_state

        self.create_workflow()

    def create_workflow(self) -> None:
        """Create the workflow for the data preparation agent."""
        # Input validation
        self.validate_input()

        model = self.config.get("configurable", {}).get("model")
        if model is None:
            # Try to create model using API key from config
            api_key = self.config.get("configurable", {}).get("api_key")
            if api_key:
                try:
                    model = ChatOpenAI(
                        model="gpt-4o-mini", temperature=0.0, api_key=api_key
                    )
                except Exception as e:
                    self.log_activity(
                        f"Could not create OpenAI model: {e}", level="warning"
                    )
                    self.workflow = None
                    return
            else:
                self.log_activity(
                    "No API key provided - workflow will not be created",
                    level="warning",
                )
                self.workflow = None
                return

        # struct_model = model.with_structured_output(schema=QueryInterpretation)
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(INTERPRETER_PROMPT),
                HumanMessage(
                    f"Query: {self.config.get('configurable', {}).get('query')}"
                ),
            ]
        )

        self.workflow = create_react_agent(
            model=model,
            tools=[],
            prompt=prompt,
            response_format=QueryInterpretation,
            name=self.name,
        )

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

        query = self.config.get("configurable", {}).get("query")

        if not query:
            self.log_activity("No query provided for data preparation.", level="error")
            return AgentResult(
                success=False,
                data=None,
                error="No query provided for data preparation.",
                metadata={"agent_name": self.name},
            )

        # Call the workflow with proper message format
        from langchain_core.messages import HumanMessage

        response = await self.workflow.ainvoke(
            {"messages": [HumanMessage(content=query)]}
        )

        # Placeholder for actual implementation
        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name},
        )

    def validate_input(self) -> None:
        """Validate the input for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for the Interpreter Agent.")
        if "query" not in self.config.get("configurable", {}):
            raise ValueError("Query must be provided in the configuration.")
        self.log_activity("Input validation passed for Interpreter Agent.")
