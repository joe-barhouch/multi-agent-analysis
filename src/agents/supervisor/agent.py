"""Fixed Supervisor Agent Class with Proper Handoff Implementation"""

from typing import Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.agents.data_prep.agent import DataPrepAgent
from src.agents.database_manager import SnowflakeManager as DataManager
from src.agents.interpreter.agent import InterpreterAgent
from src.config import DEBUG
from src.core import AgentConfig, AgentResult, AgentType, BaseAgent, GlobalState
from src.core.types import Plan

from .prompts import PLAN_PROMPT, SUPERVISOR_PROMPT

load_dotenv()


class FinalResponse(BaseModel):
    """Final response model for the supervisor agent."""

    thought_process: str = Field(
        ..., description="Thought process of the supervisor agent"
    )
    result: str = Field(..., description="Final result or answer to the user query")


class Supervisor(BaseAgent):
    """Supervisor Agent responsible for coordinating all tasks."""

    def __init__(
        self,
        name: str,
        state: GlobalState,
        data_manager: DataManager,
        streaming: bool = False,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Supervisor Agent."""
        super().__init__(
            agent_type=AgentType.SUPERVISOR,
            name=name,
            state=state,
            config=config,
            logger=logger,
            streaming=streaming,
        )
        self.data_manager = data_manager
        self.name = name

        # Initialize worker agents
        self.interpreter_agent = InterpreterAgent(
            name="interpreter",
            state=self.state,
            config=self.config,
            logger=self.logger,
        )

        self.data_prep_agent = DataPrepAgent(
            name="data_prep",
            state=self.state,
            data_manager=self.data_manager,
            config=self.config,
            logger=self.logger,
        )

        self.supervisor_agent = None
        self.create_workflow()

    def create_handoff_tool(self, *, agent_name: str, description: str | None = None):
        """Create a handoff tool for transferring control to a specific agent."""
        tool_name = f"transfer_to_{agent_name}"
        description = description or f"Transfer task to {agent_name} for processing."

        @tool(tool_name, description=description)
        def handoff_tool(
            state: Annotated[dict[str, Any], InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            """Hand off control to the specified agent with task description."""

            # Extract messages from the internal agent state
            messages = state.get("messages", [])

            # Create tool message to acknowledge the transfer
            tool_message = {
                "role": "tool",
                "content": f"Successfully transferred to {agent_name}",
                "name": tool_name,
                "tool_call_id": tool_call_id,
            }

            # Extract the user query from the messages
            user_query = None
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    # Get the last human message as the query
                    if getattr(msg, "type", None) == "human" or isinstance(
                        msg, HumanMessage
                    ):
                        user_query = msg.content

            # If no explicit human message, use the last message content
            if not user_query and messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    user_query = last_msg.content

            # Build the complete GlobalState to pass to the child agent
            # Use self.state as the base and update with current information
            updated_global_state = {
                **self.state,  # Start with current global state
                "user_query": user_query or self.state.get("user_query", ""),
                "messages": messages + [tool_message],
                "conversation_history": self.state.get("conversation_history", []),
            }

            return Command(
                goto=agent_name,  # Navigate to the agent node
                update=updated_global_state,  # Pass the complete global state
                graph=Command.PARENT,  # Indicate we're navigating in parent graph
            )

        return handoff_tool

    def create_workflow(self) -> None:
        """Create the custom supervisor workflow."""
        # Input validation
        self.validate_input()

        # Get model from config
        model = self.config.get("configurable", {}).get("model")

        # Create handoff tools for each agent
        handoff_to_interpreter = self.create_handoff_tool(
            agent_name="interpreter_agent",
            description="Transfer task to the interpreter agent for query interpretation",
        )

        handoff_to_data_prep = self.create_handoff_tool(
            agent_name="data_prep_agent",
            description="Transfer task to the data preparation agent for data exploration, cleaning, transformation and execution",
        )

        self.supervisor_agent = create_react_agent(
            model=model,
            tools=[handoff_to_interpreter, handoff_to_data_prep, self.update_todo],
            prompt=SUPERVISOR_PROMPT,
            state_schema=GlobalState,
            name="Supervisor",
            response_format=FinalResponse,
            debug=DEBUG,
        )

        # Build the multi-agent graph
        graph_builder = StateGraph(GlobalState, AgentConfig)

        # Add supervisor node
        graph_builder.add_node(
            "supervisor",
            self.supervisor_agent,
        )

        # Add worker agent nodes
        graph_builder.add_node("interpreter_agent", self.interpreter_agent.workflow)
        graph_builder.add_node("data_prep_agent", self.data_prep_agent.workflow)

        # Add edges
        graph_builder.add_edge(START, "supervisor")

        # Worker agents always return to supervisor
        graph_builder.add_edge("interpreter_agent", "supervisor")
        graph_builder.add_edge("data_prep_agent", "supervisor")

        # Add checkpointer
        checkpointer = MemorySaver()

        # Compile the graph
        self.workflow = graph_builder.compile(checkpointer=checkpointer)

        self.log_activity("Custom supervisor workflow created successfully.")

    async def execute(self) -> AgentResult:
        """Execute the supervisor workflow."""
        self.log_activity("Executing supervisor workflow.")

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
            self.log_activity("No query provided for processing.", level="error")
            return AgentResult(
                success=False,
                data=None,
                error="No query provided for processing.",
                metadata={"agent_name": self.name},
            )

        # Get conversation history from global state
        conversation_history = self.state.get("messages", [])

        # Prepare messages for workflow (include history + current query)
        messages = conversation_history.copy()
        messages.append(HumanMessage(content=query))

        try:
            if not self.streaming:
                # Prepare complete state with all GlobalState fields
                complete_state = {
                    **self.state,  # Include all existing state
                    "messages": messages,
                    "user_query": query,  # Ensure user_query is set
                }

                # Run the workflow with complete state
                response = await self.workflow.ainvoke(
                    complete_state, config=self.config
                )

                # Extract the final message from supervisor
                final_messages = response.get("messages", [])

                supervisor_response = None
                for msg in reversed(final_messages):
                    if (
                        hasattr(msg, "name")
                        and msg.name.lower() in ["supervisor"]
                        and not (hasattr(msg, "tool_calls") and msg.tool_calls)
                    ):
                        supervisor_response = msg.content
                        break

                if not supervisor_response:
                    # Fallback to last AI message
                    for msg in reversed(final_messages):
                        if hasattr(msg, "content") and msg.content:
                            supervisor_response = msg.content
                            break

                    if not supervisor_response:
                        supervisor_response = "No response generated"

            else:
                # Streaming implementation
                supervisor_response = ""
                complete_state = {
                    **self.state,
                    "messages": messages,
                    "user_query": query,
                }

                async for chunk in self.workflow.astream(
                    complete_state, config=self.config, stream_mode="values"
                ):
                    # Process streaming chunks
                    if "messages" in chunk:
                        last_msg = chunk["messages"][-1]
                        if hasattr(last_msg, "content"):
                            print(last_msg.content)
                            supervisor_response = last_msg.content

            # Update self.state with the final workflow state
            if not self.streaming:
                self.state.update(response)

            # Debugging output
            if DEBUG:
                self.debug_workflow()

            return AgentResult(
                success=True,
                data={
                    "response": supervisor_response,
                    "messages": final_messages if not self.streaming else None,
                    "message": (
                        {"messages": final_messages} if not self.streaming else None
                    ),
                    "state": self.state if not self.streaming else None,
                },
                error=None,
                metadata={
                    "agent_name": self.name,
                    "checkpointer": getattr(self.workflow, "checkpointer", None),
                },
            )

        except Exception as e:
            self.log_activity(f"Error during workflow execution: {e}", level="error")
            return AgentResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"agent_name": self.name},
            )

    async def update_todo(self, query: str):
        """
        Write Todo plan for the multi-agent workflow, to be tracked and updated.

        Args:
            query (str): The user query to be processed by the supervisor agent.
        """
        # Get the model from config
        model = self.config.get("configurable", {}).get("model")

        # Get conversation history from global state
        chat_history = self.state.get("messages", [])

        # Create structured model for Plan output
        structured_model = model.with_structured_output(schema=Plan)

        # Create the prompt template
        human_prompt = """Based on the query and context provided, please create a detailed task plan.

        User Query:
        {QUERY}

        Remember to break this down into specific, actionable tasks that our agents can execute."""

        template = ChatPromptTemplate.from_messages(
            [SystemMessage(content=PLAN_PROMPT), HumanMessage(content=human_prompt)]
        )

        # Create the chain
        chain = template | structured_model

        try:
            # Invoke the chain to get the plan
            plan = await chain.ainvoke(
                {
                    "QUERY": query,
                    "CHAT_HISTORY": (
                        str(chat_history)
                        if chat_history
                        else "No previous conversation"
                    ),
                }
            )

            # Store the plan in global state for tracking
            self.state["plan"] = plan

            self.log_activity(f"Created plan with {len(plan.tasks)} tasks")
            self.log_activity(f"Plan details: \n{plan}")

            return {"plan": plan}

        except Exception as e:
            self.log_activity(f"Error creating plan: {e}", level="error")
            # Return a fallback plan
            return Plan(tasks=[])

    def validate_input(self) -> None:
        """Validate the input configuration for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for Supervisor Agent.")
        self.log_activity("Input validation completed successfully.")

    def draw_graph(self, output_file_path: str | None = None) -> None:
        """Draw the workflow graph."""
        if self.workflow is None:
            self.log_activity(
                "Workflow not initialized - cannot draw graph.", level="error"
            )
            return

        try:
            if output_file_path is None:
                output_file_path = f"{self.name}_workflow_graph.png"
            self.workflow.get_graph(xray=True).draw_mermaid_png(
                output_file_path=output_file_path
            )
            self.log_activity(f"Graph saved to {output_file_path}")
        except Exception as e:
            self.log_activity(f"Error drawing workflow graph: {e}", level="error")

    def debug_workflow(self) -> None:
        """Debug the workflow by printing its structure."""
        print("\n=== CUSTOM SUPERVISOR WORKFLOW DEBUG ===")
        print(f"Workflow type: {type(self.workflow)}")

        # Print graph structure
        if hasattr(self.workflow, "nodes"):
            print(f"Graph nodes: {self.workflow.nodes}")

        # Try to access checkpointer state
        if hasattr(self.workflow, "checkpointer") and self.workflow.checkpointer:
            checkpointer = self.workflow.checkpointer
            print(f"Checkpointer type: {type(checkpointer)}")

            # For MemorySaver, we can access the storage
            if hasattr(checkpointer, "storage"):
                print(f"Checkpointer has storage: {bool(checkpointer.storage)}")
                if checkpointer.storage:
                    print(f"Storage keys: {list(checkpointer.storage.keys())}")
        else:
            print("No checkpointer available")

        print("=== END SUPERVISOR DEBUG ===\n")
