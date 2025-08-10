"""Visualisation Agent."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.core import BaseAgent
from src.core.models import AgentResult
from src.core.state import GlobalState
from src.core.types import AgentType, DashboardLayout, WidgetQueries

from .prompts import LAYOUT_PROMPT, VISUALISATION_PROMPT, WIDGET_SUBQUERIES_PROMPT


# -----------------------------
# Simple agent binder for tools
# -----------------------------
_CURRENT_AGENT = None  # set by VisualisationAgent when workflow is created


def _require_agent():
    """Return the bound agent or raise a clear error."""
    if _CURRENT_AGENT is None:
        raise RuntimeError("VisualisationAgent not bound to tools yet.")
    return _CURRENT_AGENT


# -----------------------------
# Tools (module-level, zero-arg)
# -----------------------------


@tool
async def create_layout() -> dict[str, Any]:
    """Create a dashboard layout for the current query. Returns {'layout': DashboardLayout}."""
    agent = _require_agent()
    model = (agent.config or {}).get("configurable", {}).get("model")
    user_query: str = agent.state.get("user_query", "")

    if not model:
        return {"error": "No model configured for structured output."}

    struct_model = model.with_structured_output(DashboardLayout)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", LAYOUT_PROMPT),
            (
                "human",
                "Here is the user's query:\n<user_query>\n{QUERY}\n</user_query>",
            ),
        ]
    )

    chain = prompt | struct_model
    layout: DashboardLayout = chain.invoke({"QUERY": user_query})

    # Save for the next tool
    agent.state["dashboard_layout"] = layout
    return {"layout": layout}


@tool
async def create_widget_desc() -> dict[str, Any]:
    """Create widget specs for the saved layout. Returns {'widget_specs': WidgetQueries}."""
    agent = _require_agent()
    model = (agent.config or {}).get("configurable", {}).get("model")
    user_query: str = agent.state.get("user_query", "")
    layout: Optional[DashboardLayout] = agent.state.get("dashboard_layout")

    if not layout:
        return {
            "error": "No layout found. Call create_layout before create_widget_desc."
        }
    if not model:
        return {"error": "No model configured for structured output."}

    struct_model = model.with_structured_output(WidgetQueries)

    system_block = WIDGET_SUBQUERIES_PROMPT.format(LAYOUT=layout)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_block),
            (
                "human",
                "Here is the user's query:\n<user_query>\n{QUERY}\n</user_query>",
            ),
        ]
    )

    chain = prompt | struct_model
    widget_specs: WidgetQueries = chain.invoke({"QUERY": user_query})

    agent.state["widget_specs"] = widget_specs
    return {"widget_specs": widget_specs}


# -----------------------------
# Agent class
# -----------------------------


class VisualisationAgent(BaseAgent):
    """Agent that plans dashboard visualisation."""

    def __init__(
        self,
        name: str,
        state: GlobalState,
        config: Optional[RunnableConfig] = None,
        logger=None,
        streaming: bool = False,
    ):
        super().__init__(
            agent_type=AgentType.VISUALISATION,
            name=name,
            state=state,
            config=config,
            logger=logger,
            streaming=streaming,
        )
        self.checkpointer = MemorySaver()  # short-term memory
        self.workflow = None
        self.create_workflow()

    # -----------------------------
    # Graph lifecycle
    # -----------------------------
    def create_workflow(self) -> None:
        """Create ReAct workflow with tools."""
        self.validate_input()

        # bind this instance for the zero-arg tools
        global _CURRENT_AGENT
        _CURRENT_AGENT = self

        model = (self.config or {}).get("configurable", {}).get("model", None)
        human_prompt = """Here is the user's query:
        <user_query>
        {QUERY}
        </user_query>
        And here is the chat history:
        <chat_history>
        {CHAT_HISTORY}
        </chat_history>
        """

        query = self.state.get("user_query", "")
        chat_history = self.state.get("chat_history", "")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", VISUALISATION_PROMPT),
                ("human", human_prompt.format(QUERY=query, CHAT_HISTORY=chat_history)),
            ]
        )

        tools = [create_layout, create_widget_desc]

        self.workflow = create_react_agent(
            model=model,
            tools=tools,
            prompt=prompt,
            name=self.name,
            checkpointer=self.checkpointer,
            debug=True,
        )
        self.log_activity("Visualisation workflow created.")

    def validate_input(self) -> None:
        """Light validation on config."""
        if self.config is None:
            self.log_activity("Config is None; running without model.", level="warning")
        self.log_activity("Input validation completed.")

    async def execute(self) -> AgentResult:
        """Run the agent once for the current 'user_query'."""
        self.log_activity("Executing visualisation agent.")
        if self.workflow is None:
            return AgentResult(
                success=False,
                data=None,
                error="Workflow not initialized - check API key configuration.",
                metadata={"agent_name": self.name},
            )

        user_query: Optional[str] = self.state.get("user_query")
        chat_history = self.state.get("chat_history", [])
        if not user_query:
            return AgentResult(
                success=False,
                data=None,
                error="No query provided for visualisation.",
                metadata={"agent_name": self.name},
            )

        # Stable thread for checkpointing across turns
        thread_id = (self.config or {}).get("configurable", {}).get("thread_id")
        if not thread_id:
            thread_id = f"vis-{uuid.uuid4()}"
        runtime_config: RunnableConfig = {
            **(self.config or {}),
            "configurable": {
                **((self.config or {}).get("configurable", {})),
                "thread_id": thread_id,
            },
        }

        payload = {
            "messages": [HumanMessage(content=user_query)],
            "QUERY": user_query,
            "CHAT_HISTORY": chat_history or "",
        }

        response = await self.workflow.ainvoke(payload, config=runtime_config)

        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name, "thread_id": thread_id},
        )


# -----------------------------
# Example CLI usage
# -----------------------------


async def main():
    from langchain_openai import ChatOpenAI

    agent = VisualisationAgent(
        name="VisualisationAgent",
        state=GlobalState(),
        config=RunnableConfig(
            configurable={
                "model": ChatOpenAI(model="gpt-5-mini"),
                "thread_id": "thread-1",
            }
        ),
    )

    while True:
        user_query = input("Enter your query: ")
        agent.state["user_query"] = user_query
        result = await agent.execute()
        print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
