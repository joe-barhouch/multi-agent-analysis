"""Base agent class for all multi-agent system components."""

import logging
from abc import ABC, abstractmethod

from langchain_core.runnables import RunnableConfig

from .models import AgentResult
from .state import GlobalState
from .types import AgentType


class BaseAgent(ABC):
    """Abstract base class for all agents in the multi-agent system."""

    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        streaming: bool = False,
        state: GlobalState | None = None,
        config: RunnableConfig | None = None,
        logger: logging.Logger | None = logging.getLogger(f"{__name__}"),
    ):
        """Initialize the base agent.

        Args:
            agent_type: Type of the agent (e.g., planner, executor)
            name: Unique name for the agent
            state: Current global state of the system

        """
        self.agent_type = agent_type
        self.name = name
        self.state = state
        self.config = config or RunnableConfig()
        self.logger = logger
        self.streaming = streaming

    @abstractmethod
    def create_workflow(self) -> None:
        """
        Create the workflow for the agent.

        This method defines how the agent
        will operate within the multi-agent system.
        """
        pass

    @abstractmethod
    async def execute(self) -> AgentResult:
        """
        Main execution method for the agent.

        Returns:
            AgentResult with success status and data
        """
        pass

    @abstractmethod
    def validate_input(self) -> None:
        """
        Validate that the agent can process the current state.

        """
        if not self.state:
            self.log_activity("Invalid state: Global state is None.", level="error")
            raise ValueError("Global state cannot be None.")

    def log_activity(self, message: str, level: str = "info") -> None:
        """
        Log agent activity with appropriate level.

        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
        """
        if self.logger:
            getattr(self.logger, level)(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] {level.upper()}: {message}")
