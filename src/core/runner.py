"""Core agent runner for executing queries without CLI dependencies."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_sandbox import PyodideSandboxTool

from src.config import DEFAULT_MODEL_NAME, DEFAULT_TEMPERATURE
from src.core import BaseAgent, GlobalState
from src.core.models import AgentResult


@dataclass
class ExecutionResult:
    """Result of agent execution with structured data."""

    success: bool
    query: str
    ai_response: Optional[str] = None
    error: Optional[str] = None
    agent_flow: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Optional[Dict[str, int]] = None
    execution_time: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None
    final_global_state: Optional[GlobalState] = None


@dataclass
class SessionContext:
    """Context for a conversation session."""

    session_id: str
    conversation_history: List[BaseMessage] = field(default_factory=list)
    query_count: int = 0
    max_messages: int = 20


class AgentRunner:
    """Handles agent execution logic without CLI dependencies."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        data_manager: Optional[Any] = None,
    ):
        """Initialize the agent runner.

        Args:
            api_key: OpenAI API key (optional)
        """
        self.api_key = api_key
        self.model = self._initialize_model(api_key)
        self.data_manager = data_manager
        self._data_prep_assets: Optional[Dict[str, Any]] = None
        self._assets_manager_id: Optional[int] = None

    def _prepare_data_prep_assets(self, data_manager) -> dict:
        if self._data_prep_assets:
            return self._data_prep_assets
        if data_manager and not getattr(data_manager, "db", None):
            data_manager.get_sql_database()

        tools = []
        if self.model and data_manager and getattr(data_manager, "db", None):
            toolkit = SQLDatabaseToolkit(db=data_manager.db, llm=self.model)
            tools.extend(toolkit.get_tools())

        try:
            sandbox_tool = PyodideSandboxTool(allow_net=True, stateful=True)
            tools.append(sandbox_tool)
        except Exception:
            pass

        tool_info = "\n".join(
            f"<tool>{t.name}: {getattr(t, 'description', '')}</tool>" for t in tools
        )

        assets = {
            "data_tools": tools,
            "tool_info": tool_info,
            "data_sources": "Sources:\n - Snowflake (primary)\n - Auxiliary CSVs",
        }
        self._data_prep_assets = assets
        return assets

    def _initialize_model(self, api_key: Optional[str]) -> Optional[ChatOpenAI]:
        """Initialize the ChatOpenAI model using centralized config.

        Args:
            api_key: OpenAI API key

        Returns:
            ChatOpenAI instance or None if initialization fails
        """
        if not api_key:
            return None
        try:
            return ChatOpenAI(
                model=DEFAULT_MODEL_NAME,
                temperature=DEFAULT_TEMPERATURE,
                api_key=api_key,
            )
        except Exception:
            return None

    def create_session(self) -> SessionContext:
        """Create a new conversation session."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return SessionContext(session_id=session_id)

    def _create_global_state(
        self, query: str, session: SessionContext
    ) -> "GlobalState":
        """Create a fresh global state for a query."""
        from src.core.state import GlobalState

        return GlobalState(
            user_query=query,
            session_id=session.session_id,
            conversation_history=session.conversation_history,
            max_messages=session.max_messages,
            enable_trimming=True,
            interpreted_query=None,
            todo_plan=[],
            current_task=None,
            dashboard_layout={},
            widget_specs={},
            widget_data_queries={},
            available_tables=[],
            created_subtables=[],
            data_descriptions={},
            errors=[],
            warnings=[],
            current_agent=None,
            agent_history=[],
        )

    def _extract_ai_response(self, result_data: Dict[str, Any]) -> Optional[str]:
        """Extract clean AI response from result."""
        try:
            if not result_data or "message" not in result_data:
                return None

            messages = result_data["message"].get("messages", [])

            for message in reversed(messages):
                if isinstance(message, AIMessage):
                    return message.content

            return None
        except Exception:
            return None

    def _extract_token_usage(
        self, result_data: Dict[str, Any]
    ) -> Optional[Dict[str, int]]:
        """Extract token usage information."""
        try:
            messages = result_data["message"].get("messages", [])
            for message in reversed(messages):
                if isinstance(message, AIMessage) and hasattr(
                    message, "usage_metadata"
                ):
                    usage = message.usage_metadata
                    return {
                        "total": usage.get("total_tokens", 0),
                        "input": usage.get("input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                    }
            return None
        except Exception:
            return None

    def _extract_agent_flow(self, result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract agent coordination flow."""
        try:
            if not result_data or "message" not in result_data:
                return []

            messages = result_data["message"].get("messages", [])
            flow = []

            for message in messages:
                if isinstance(message, HumanMessage):
                    flow.append(
                        {
                            "type": "user_input",
                            "content": message.content,
                            "agent": "User",
                        }
                    )
                elif isinstance(message, AIMessage):
                    agent_name = getattr(message, "name", "Unknown")
                    flow.append(
                        {
                            "type": "agent_response",
                            "agent": agent_name,
                            "content": message.content,
                            "tool_calls": getattr(message, "tool_calls", []),
                        }
                    )
                elif isinstance(message, ToolMessage):
                    flow.append(
                        {
                            "type": "tool_call",
                            "tool_name": getattr(message, "name", "Unknown Tool"),
                            "content": message.content,
                        }
                    )

            return flow
        except Exception:
            return []

    # def _extract_tool_calls(self, result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    #     """Extract tool usage information."""
    #     try:
    #         if not result_data or "message" not in result_data:
    #             return []
    #
    #         messages = result_data["message"].get("messages", [])
    #         tools_used = []
    #
    #         for message in messages:
    #             if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
    #                 for tool_call in message.tool_calls:
    #                     tools_used.append(
    #                         {
    #                             "name": tool_call.get("name", "Unknown"),
    #                             "args": tool_call.get("args", {}),
    #                             "id": tool_call.get("id", ""),
    #                         }
    #                     )
    #
    #         return tools_used
    #     except Exception:
    #         return []

    def _extract_tool_calls(self, result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract comprehensive tool usage information, including agent and result."""
        try:
            if not result_data or "message" not in result_data:
                return []

            messages = result_data["message"].get("messages", [])
            if not messages:
                return []

            # Create a lookup for tool results by their ID by finding all ToolMessages
            tool_results = {
                msg.tool_call_id: msg.content
                for msg in messages
                if isinstance(msg, ToolMessage)
                and hasattr(msg, "tool_call_id")
                and msg.tool_call_id
            }

            tools_used = []
            current_agent = "Unknown"

            # Iterate through all messages to find tool calls and track agent context
            for message in messages:
                # Track current agent context
                if (
                    isinstance(message, AIMessage)
                    and hasattr(message, "name")
                    and message.name
                ):
                    current_agent = message.name

                # Extract tool calls from AIMessages
                if (
                    isinstance(message, AIMessage)
                    and hasattr(message, "tool_calls")
                    and message.tool_calls
                ):
                    agent_name = getattr(message, "name", current_agent)
                    for tool_call in message.tool_calls:
                        tool_id = tool_call.get("id")
                        tools_used.append(
                            {
                                "name": tool_call.get("name", "Unknown"),
                                "args": tool_call.get("args", {}),
                                "id": tool_id,
                                "agent": agent_name,
                                "result": tool_results.get(tool_id, ""),
                            }
                        )

                # Also look for ToolMessages that might indicate tool usage
                elif isinstance(message, ToolMessage):
                    tool_name = getattr(message, "name", "Unknown")
                    tool_id = getattr(message, "tool_call_id", "")

                    # Only add if we haven't already captured this tool call
                    if not any(tool["id"] == tool_id for tool in tools_used):
                        # Infer agent based on tool type or current context
                        inferred_agent = current_agent
                        if "sql_db" in tool_name.lower():
                            inferred_agent = "Data Prep"
                        elif (
                            "python" in tool_name.lower()
                            or "sandbox" in tool_name.lower()
                        ):
                            inferred_agent = "Data Prep"

                        tools_used.append(
                            {
                                "name": tool_name,
                                "args": {},  # ToolMessage doesn't have args
                                "id": tool_id,
                                "agent": inferred_agent,
                                "result": message.content,
                            }
                        )

            # EXPERIMENTAL: Try to extract nested tool calls from checkpointer metadata
            checkpointer_tools = self._extract_nested_tool_calls(result_data)
            if checkpointer_tools:
                print(
                    f"DEBUG: Found {len(checkpointer_tools)} additional tools from nested extraction"
                )
                tools_used.extend(checkpointer_tools)

            return tools_used
        except Exception as e:
            # Log the error for debugging
            print(f"Error extracting tool calls: {e}")
            return []

    def _extract_nested_tool_calls(
        self, result_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Attempt to extract tool calls from nested agent workflows."""
        nested_tools = []

        try:
            # Check if we have checkpointer metadata
            metadata = result_data.get("metadata", {})
            checkpointer = metadata.get("checkpointer")

            if checkpointer and hasattr(checkpointer, "storage"):
                print("DEBUG: Attempting nested tool extraction from checkpointer")

                # Iterate through checkpoint storage
                for key, checkpoint_data in checkpointer.storage.items():
                    if hasattr(checkpoint_data, "channel_values"):
                        channel_values = checkpoint_data.channel_values

                        # Look for messages in different channels
                        for channel_name, channel_content in channel_values.items():
                            if channel_name == "messages" and isinstance(
                                channel_content, list
                            ):
                                print(
                                    f"DEBUG: Found {len(channel_content)} messages in checkpoint channel '{channel_name}'"
                                )

                                # Extract tools from checkpoint messages
                                for msg in channel_content:
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            nested_tools.append(
                                                {
                                                    "name": tool_call.get(
                                                        "name", "Unknown"
                                                    ),
                                                    "args": tool_call.get("args", {}),
                                                    "id": tool_call.get("id", ""),
                                                    "agent": getattr(
                                                        msg, "name", "Unknown"
                                                    ),
                                                    "result": "",
                                                    "source": "checkpointer",
                                                }
                                            )
                                    elif isinstance(msg, ToolMessage):
                                        nested_tools.append(
                                            {
                                                "name": getattr(msg, "name", "Unknown"),
                                                "args": {},
                                                "id": getattr(msg, "tool_call_id", ""),
                                                "agent": "Data Prep",  # Infer from context
                                                "result": msg.content,
                                                "source": "checkpointer",
                                            }
                                        )

        except Exception as e:
            print(f"DEBUG: Error in nested tool extraction: {e}")

        return nested_tools

    def _extract_final_global_state(
        self, result_data: Dict[str, Any], supervisor
    ) -> Optional["GlobalState"]:
        """Extract the final global state from supervisor execution."""
        try:
            # Try to get the global state from the supervisor agent
            if hasattr(supervisor, "global_state"):
                return supervisor.global_state

            # Alternative: try to extract from result data
            if result_data and "global_state" in result_data:
                return result_data["global_state"]

            # If supervisor has a workflow with state
            if hasattr(supervisor, "workflow") and hasattr(
                supervisor.workflow, "get_state"
            ):
                try:
                    workflow_state = supervisor.workflow.get_state()
                    if workflow_state and hasattr(workflow_state, "values"):
                        # Look for global state in workflow values
                        values = workflow_state.values
                        if isinstance(values, dict) and "global_state" in values:
                            return values["global_state"]
                except Exception:
                    pass

            return None

        except Exception as e:
            print(f"DEBUG: Error extracting final global state: {e}")
            return None

    def _update_conversation_history(
        self, session: SessionContext, query: str, response: str
    ) -> None:
        """Update conversation history in the session."""
        session.conversation_history.append(HumanMessage(content=query))
        session.conversation_history.append(AIMessage(content=response))

        # Trim if needed
        if len(session.conversation_history) > session.max_messages:
            session.conversation_history = session.conversation_history[
                -session.max_messages :
            ]

    async def execute_query(
        self, query: str, session: SessionContext, supervisor_factory
    ) -> ExecutionResult:
        """Execute a query and return structured results.

        Args:
            query: User query to execute
            session: Session context with conversation history
            supervisor_factory: Factory function to create supervisor agent

        Returns:
            ExecutionResult with all extracted information
        """
        import time

        start_time = time.time()

        session.query_count += 1

        global_state = self._create_global_state(query, session)
        global_state["user_query"] = query

        assets = self._prepare_data_prep_assets(getattr(self, "data_manager", None))

        config = RunnableConfig()
        config["configurable"] = {
            "model": self.model,
            "api_key": self.api_key,
            "query": query,
            "thread_id": "thread-1",
            "data_tools": assets["data_tools"],
            "tool_info": assets["tool_info"],
            "data_sources": assets["data_sources"],
        }

        supervisor = supervisor_factory(
            name=f"supervisor_{session.query_count}",
            global_state=global_state,
            config=config,
        )
        supervisor = cast(BaseAgent, supervisor)

        try:
            result: AgentResult = await supervisor.execute()

            if not result.success:
                return ExecutionResult(
                    success=False,
                    query=query,
                    error=result.error or "Unknown error occurred",
                    execution_time=time.time() - start_time,
                )

            ai_response = self._extract_ai_response(result.data)
            agent_flow = self._extract_agent_flow(result.data)
            tool_calls = self._extract_tool_calls(result.data)
            token_usage = self._extract_token_usage(result.data)

            final_global_state = self._extract_final_global_state(
                result.data, supervisor
            )

            if result.data and "message" in result.data:
                messages = result.data["message"].get("messages", [])
                print("\n=== DEEP DEBUG: Message Analysis ===")
                print(f"Found {len(messages)} messages in supervisor workflow:")

                for i, msg in enumerate(messages):
                    msg_type = type(msg).__name__
                    msg_name = getattr(msg, "name", "N/A")
                    has_tool_calls = hasattr(msg, "tool_calls") and msg.tool_calls
                    is_tool_msg = msg_type == "ToolMessage"

                    print(
                        f"  [{i}] {msg_type} | name: {msg_name} | has_tool_calls: {has_tool_calls} | is_tool_msg: {is_tool_msg}"
                    )

                    if has_tool_calls:
                        for j, tc in enumerate(msg.tool_calls):
                            print(
                                f"       Tool Call [{j}]: {tc.get('name', 'Unknown')} | args: {tc.get('args', {})}"
                            )

                    if is_tool_msg:
                        tool_name = getattr(msg, "name", "Unknown")
                        tool_content = getattr(msg, "content", "")
                        content_preview = (
                            tool_content[:100] + "..."
                            if len(tool_content) > 100
                            else tool_content
                        )
                        print(f"       Tool: {tool_name} | content: {content_preview}")

                    if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                        print(f"       Additional kwargs: {msg.additional_kwargs}")

                print(
                    f"DEBUG: Extracted {len(tool_calls)} tool calls from supervisor workflow"
                )
                print("=== END DEEP DEBUG ===\n")

            if ai_response:
                self._update_conversation_history(session, query, ai_response)

            return ExecutionResult(
                success=True,
                query=query,
                ai_response=ai_response,
                agent_flow=agent_flow,
                tool_calls=tool_calls,
                token_usage=token_usage,
                execution_time=time.time() - start_time,
                raw_data=result.data,
                final_global_state=final_global_state,
            )

        except Exception as e:
            error_msg = f"Error during execution: {str(e)}"
            self._update_conversation_history(session, query, error_msg)

            return ExecutionResult(
                success=False,
                query=query,
                error=error_msg,
                execution_time=time.time() - start_time,
            )
