"""Supervisor Agent Class"""

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph
from langgraph_supervisor import create_supervisor
from pydantic import BaseModel, Field

from src.agents import DataManager, DataPrepAgent, InterpreterAgent
from src.config import DEBUG, DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from src.core import AgentResult, AgentType, BaseAgent, GlobalState

from .prompts import SUPERVISOR_PROMPT

load_dotenv()

# TODO:
# Initiate flow to read data better
# Update global state with tool calls
# Update explored queries and sql ran and tables selected
# Use sandbox for python manipulation
# How to debug the internals of the data agent from a supervisor call
# Streaming output


class FinalResponse(BaseModel):
    """Final response model for the supervisor agent."""

    thought_process: str = Field(
        ..., description="Thought process of the supervisor agent"
    )
    result: str = Field(
        ...,
        description="Final result or answer to the user query",
    )


class Supervisor(BaseAgent):
    """Supervisor Agent responsible for coordinating all tasks."""

    # Class-level defaults; can be overridden via config
    MAX_HISTORY_MESSAGES_DEFAULT = 10
    MAX_MESSAGE_LENGTH_DEFAULT = 5000
    MAX_GLOBAL_HISTORY_DEFAULT = 20

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        data_manager: DataManager,
        streaming: bool = False,
        local_state: StateGraph | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Supervisor Agent."""
        super().__init__(
            agent_type=AgentType.SUPERVISOR,
            name=name,
            state=local_state,
            config=config,
            logger=logger,
            streaming=streaming,
        )
        self.local_state = local_state
        self.global_state = global_state
        self.data_manager = data_manager

        # Resolve limits from config (if provided), fallback to defaults
        cfg = {}
        try:
            cfg = (self.config or {}).get("configurable", {})  # type: ignore[union-attr]
        except Exception:
            cfg = {}
        self.MAX_HISTORY_MESSAGES = int(
            cfg.get("max_history_messages", self.MAX_HISTORY_MESSAGES_DEFAULT)
        )
        self.MAX_MESSAGE_LENGTH = int(
            cfg.get("max_message_length", self.MAX_MESSAGE_LENGTH_DEFAULT)
        )
        self.MAX_GLOBAL_HISTORY = int(
            cfg.get("max_global_history", self.MAX_GLOBAL_HISTORY_DEFAULT)
        )

        self.name = name

        self.create_workflow()

    def create_workflow(self) -> None:
        """Create the workflow for the supervisor agent."""
        # Input validation
        self.validate_input()

        interpreter_agent = InterpreterAgent(
            name="interpreter",
            global_state=self.global_state,
            local_state=self.local_state,
            config=self.config,
            logger=self.logger,
        )
        data_prep_agent = DataPrepAgent(
            name="data_prep",
            global_state=self.global_state,
            local_state=self.local_state,
            data_manager=self.data_manager,
            config=self.config,
            logger=self.logger,
        )

        agent_workflows = [
            interpreter_agent.workflow,
            data_prep_agent.workflow,
        ]
        agents_label = ["interpreter", "data_prep"]

        model = self.config.get("configurable", {}).get("model")
        query = self.global_state.get("user_query", None)

        if model is None:
            # Try to create model using API key from config/centralized config
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

        supervisor = create_supervisor(
            agents=agent_workflows,
            model=model,
            prompt=SUPERVISOR_PROMPT.format(
                AGENTS=f"Available agents: {', '.join(agents_label)}",
                QUERY=query,
            ),
            supervisor_name="Supervisor",
            add_handoff_messages=True,
            add_handoff_back_messages=True,
            parallel_tool_calls=True,
            response_format=FinalResponse,
            output_mode="full_history",
        )

        # Compile with in-memory saver; switch to persistent saver
        # in deployment
        self.workflow = supervisor.compile(
            checkpointer=InMemorySaver(),
        )

    async def execute(self) -> AgentResult:
        """Execute supervisor flow for the current user query."""
        self.log_activity("Executing supervisor workflow.")

        if self.workflow is None:
            self.log_activity(
                "Workflow not initialized - likely missing API key",
                level="error",
            )
            return AgentResult(
                success=False,
                data=None,
                error=("Workflow not initialized - check API key configuration."),
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

        # Get conversation history from global state
        conversation_history = self.global_state.get("conversation_history", [])

        # Clean up global state conversation history to prevent memory bloat
        self._cleanup_conversation_history()

        # Prepare messages for workflow - limit history to prevent tokens
        # Keep only the last few messages to stay within token limits
        filtered_history = []
        for msg in conversation_history[-self.MAX_HISTORY_MESSAGES :]:
            content = str(getattr(msg, "content", ""))
            has_content = bool(content)
            content_too_long = len(content) > self.MAX_MESSAGE_LENGTH
            if has_content and content_too_long:
                # Truncate long messages
                truncated_content = (
                    content[: self.MAX_MESSAGE_LENGTH] + "... [truncated]"
                )
                # Create new message with truncated content
                if hasattr(msg, "type"):
                    if msg.type == "human":
                        truncated_msg = HumanMessage(content=truncated_content)
                    else:
                        truncated_msg = AIMessage(content=truncated_content)
                    filtered_history.append(truncated_msg)
                else:
                    filtered_history.append(msg)
            else:
                filtered_history.append(msg)

        # Prepare messages for workflow
        messages = filtered_history.copy()

        # Truncate current query if too long
        current_query = query
        if len(query) > self.MAX_MESSAGE_LENGTH:
            current_query = query[: self.MAX_MESSAGE_LENGTH] + "... [truncated]"

        messages.append(HumanMessage(content=current_query))

        if not self.streaming:
            response = await self.workflow.ainvoke(
                {"messages": messages}, config=self.config
            )

        else:
            # TODO: fix streaming
            async for chunk in self.workflow.astream(
                {"messages": messages}, stream_mode="values"
            ):
                print(chunk)

            print("Streaming not fully implemented yet.")
            response = None

        # Debugging output
        if DEBUG:
            self.debug_workflow()

        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={
                "agent_name": self.name,
                "checkpointer": getattr(self.workflow, "checkpointer", None),
            },
        )

    def validate_input(self) -> None:
        """Validate the input configuration for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for Supervisor Agent.")
        # Model can be None for testing without API key
        self.log_activity("Input validation completed successfully.")

    def _cleanup_conversation_history(self) -> None:
        """Clean up conversation history to prevent memory bloat."""
        conversation_history = self.global_state.get("conversation_history", [])

        if len(conversation_history) > self.MAX_GLOBAL_HISTORY:
            # Keep only the most recent messages
            trimmed_history = conversation_history[-self.MAX_GLOBAL_HISTORY :]
            self.global_state["conversation_history"] = trimmed_history
            self.log_activity(
                (
                    "Trimmed conversation history from "
                    f"{len(conversation_history)} to "
                    f"{len(trimmed_history)} messages"
                )
            )

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
        except Exception as e:
            self.log_activity(f"Error drawing workflow graph: {e}", level="error")

    def debug_workflow(self) -> None:
        """Debug the workflow by printing its structure."""
        # Enhanced debugging: Access checkpointer state if available
        print("\n=== SUPERVISOR WORKFLOW DEBUG ===")
        print(f"Workflow type: {type(self.workflow)}")

        # Try to access checkpointer state
        checkpointer = getattr(self.workflow, "checkpointer", None)
        if checkpointer is not None:
            print(f"Checkpointer type: {type(checkpointer)}")
            print(f"Checkpointer available: {checkpointer is not None}")

            # Try to get checkpoint data
            try:
                # For InMemorySaver, we might need to access internal storage
                if hasattr(checkpointer, "storage"):
                    keys = (
                        list(checkpointer.storage.keys())
                        if checkpointer.storage
                        else None
                    )
                    print(f"Checkpointer storage keys: {keys}")

                    # Print checkpoint data for debugging
                    for key, checkpoint_data in checkpointer.storage.items():
                        print(f"Checkpoint {key}: {type(checkpoint_data)}")
                        if hasattr(checkpoint_data, "channel_values"):
                            ch_vals = checkpoint_data.channel_values
                            print(f"  Channel values: {ch_vals.keys()}")
                            # Look for messages in the checkpoint
                            if "messages" in ch_vals:
                                checkpoint_messages = ch_vals["messages"]
                                print(
                                    "  Checkpoint has "
                                    f"{len(checkpoint_messages)} messages"
                                )

            except Exception as e:  # pragma: no cover - debug only
                print(f"Error accessing checkpointer: {e}")
        else:
            print("No checkpointer available")

        print("=== END SUPERVISOR DEBUG ===\n")
