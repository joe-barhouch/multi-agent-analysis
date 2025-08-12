"""Interpreter Agent."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.interpreter.models import Plan, QueryInterpretation
from src.agents.interpreter.prompts import INTERPRETER_PROMPT, PLAN_PROMPT
from src.config import DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from src.core.base_agent import BaseAgent
from src.core.models import AgentResult
from src.core.state import GlobalState
from src.core.types import AgentType


class InterpreterAgent(BaseAgent):
    """Agent responsible for Query Interpretation."""

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        local_state: dict | None = None,
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

        self.name = name
        self.create_workflow()

    def _old_create_workflow(self) -> None:
        """Create the workflow for the data preparation agent."""
        # Input validation
        self.validate_input()

        # workflow = StateGraph(GraphState, AgentConfig)

        model = self.config.get("configurable", {}).get("model")
        if model is None:
            # Try to create model using API key from config/centralized config
            api_key = self.config.get("configurable", {}).get("api_key")
            if api_key:
                try:
                    model = ChatOpenAI(
                        model=DEFAULT_MODEL_NAME,
                        temperature=DEFAULT_TEMPERATURE,
                        api_key=api_key
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

    def create_workflow(self) -> None:
        """Create Interpreter workflow."""
        model = self.config.get("configurable", {}).get("model")

        tools = [
            Tool(
                name="create_plan",
                func=self.create_plan,
                coroutine=self.create_plan,
                description="Create a structured plan based on the user's query and chat history.",
            ),
            Tool(
                name="interpret_question",
                func=self.interpret_question,
                coroutine=self.interpret_question,
                description="Interpret the user's question to extract intent, entities, and metrics.",
            ),
        ]

        human_prompt = """Here is the user's query:
        <user_query>
        {QUERY}
        </user_query>
        And here is the chat history:
        <chat_history>
        {CHAT_HISTORY}
        </chat_history>
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(INTERPRETER_PROMPT),
                HumanMessage(
                    human_prompt.format(
                        QUERY=self.global_state.get("user_query", ""),
                        CHAT_HISTORY=self.global_state.get("conversation_history", []),
                    )
                ),
            ]
        )

        workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=prompt,
            name=self.name,
            checkpointer=InMemorySaver(),
        )

        self.workflow = workflow

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

        # async for chunk in self.workflow.astream(
        #     {"messages": [HumanMessage(content=query)]},
        #     config=self.config,
        # ):
        #     response = chunk
        #     print(response)

        breakpoint()
        # Placeholder for actual implementation
        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name},
        )

    async def create_plan(self, state, config=None):
        """Create a plan based on the current state."""
        self.log_activity("Creating plan based on current state.")

        # Use the workflow to create a plan
        if config:
            model = config.get("configurable", {}).get("model")
        else:
            model = self.config.get("configurable", {}).get("model")

        # query = state.get("user_query", "")
        query = state

        # chat_history = state.get("conversation_history", [])
        chat_history = []

        structured_model = model.with_structured_output(schema=Plan)
        human_prompt = """Here is the user's query:
        <user_query>
        {QUERY}
        </user_query>

        <query_interpretation>
        Here is the structured interpretation of the query:
        {QUERY_INTERPRETATION}
        </query_interpretation>

        And here is the chat history:
        <chat_history>
        {CHAT_HISTORY}
        </chat_history>
        """

        template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    PLAN_PROMPT.format(
                        QUERY=query,
                        CHAT_HISTORY=chat_history,
                        QUERY_INTERPRETATION=state.get(
                            "interpreted_query", state.get("user_query")
                        ),
                    )
                ),
                HumanMessage(human_prompt),
            ]
        )

        chain = template | structured_model

        plan = await chain.ainvoke(
            {
                "QUERY": query,
                "CHAT_HISTORY": chat_history,
            }
        )

        self.log_activity(f"Plan created: {plan}")

        return {
            "plan": plan,
        }

    async def interpret_question(self, state, config=None):
        """Interpret Question"""
        self.log_activity("Interpreting user question.")
        if config:
            model = config.get("configurable", {}).get("model")
        else:
            model = self.config.get("configurable", {}).get("model")

        # query = state.get("user_query", "")
        query = state

        # chat_history = state.get("conversation_history", [])
        chat_history = []

        structured_model = model.with_structured_output(schema=QueryInterpretation)
        human_prompt = """Here is the user's query:
        <user_query>
        {QUERY}
        </user_query>

        And here is the chat history:
        <chat_history>
        {CHAT_HISTORY}
        </chat_history>
        """

        template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    INTERPRETER_PROMPT.format(QUERY=query, CHAT_HISTORY=chat_history)
                ),
                HumanMessage(human_prompt),
            ]
        )

        chain = template | structured_model

        interpretation = await chain.ainvoke(
            {
                "QUERY": query,
                "CHAT_HISTORY": chat_history,
            }
        )

        self.log_activity(f"Interpretation created: {interpretation}")

        return {
            "interpretation": interpretation,
        }

    def validate_input(self) -> None:
        """Validate the input for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for the Interpreter Agent.")
        if "query" not in self.config.get("configurable", {}):
            raise ValueError("Query must be provided in the configuration.")
        self.log_activity("Input validation passed for Interpreter Agent.")


async def main():
    """Main function to run the Interpreter Agent."""
    agent = InterpreterAgent(
        name="Interpreter",
        global_state=GlobalState(
            user_query="Show me the top 3 companies by revenue in 2005, then display bottom 5 by GDP growth"
        ),
        local_state=None,
        config={
            "configurable": {
                "model": ChatOpenAI(
                    model=DEFAULT_MODEL_NAME,
                    temperature=DEFAULT_TEMPERATURE
                ),
                "thread_id": "thread-1",
            },
            "recursion_limit": 5,
        },
    )
    result = await agent.execute()
    print(result)


if __name__ == "__main__":
    # Example usage
    import asyncio

    asyncio.run(main())
