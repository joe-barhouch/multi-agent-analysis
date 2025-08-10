"""Interpreter Agent."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from src.agents.interpreter.prompts import INTERPRETER_MAIN_PROMPT, INTERPRETER_PROMPT
from src.core import GlobalState, QueryInterpretation
from src.core.base_agent import BaseAgent
from src.core.models import AgentResult
from src.core.types import AgentType


class InterpreterAgent(BaseAgent):
    """Agent responsible for Query Interpretation."""

    def __init__(
        self,
        name: str,
        state: GlobalState,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Interpreter Agent."""
        super().__init__(
            agent_type=AgentType.QUERY_INTERPRETER,
            name=name,
            state=state,
            config=config,
            logger=logger,
        )
        self.name = name
        self.create_workflow()

    def _old_create_workflow(self) -> None:
        """Create the workflow for the data preparation agent."""
        # Input validation
        self.validate_input()

        # workflow = StateGraph(GraphState, AgentConfig)

        model = self.config.get("configurable", {}).get("model")
        if model is None:
            # Try to create model using API key from config
            api_key = self.config.get("configurable", {}).get("api_key")
            if api_key:
                try:
                    model = ChatOpenAI(
                        model="gpt-4.1-mini", temperature=0.0, api_key=api_key
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

    def create_workflow(self) -> None:
        """Create Interpreter workflow."""
        model = self.config.get("configurable", {}).get("model")

        tools = [
            Tool(
                name="interpret_question",
                func=self.interpret_question,
                coroutine=self.interpret_question,
                description="Interpret the user's question to extract intent, entities, and metrics.",
            )
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
                SystemMessage(INTERPRETER_MAIN_PROMPT),
                HumanMessage(
                    human_prompt.format(
                        QUERY=self.state.get("user_query", ""),
                        CHAT_HISTORY=self.state.get("conversation_history", []),
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

        query = self.state.get("user_query", None)

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

        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name},
        )

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

        breakpoint()
        self.state["query_interpretation"] = interpretation
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
        state=GlobalState(
            user_query="Show me the top 3 companies by revenue in 2005, then display bottom 5 by GDP growth"
        ),
        config={
            "configurable": {
                "model": ChatOpenAI(model="gpt-4.1-mini", temperature=0.0),
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
