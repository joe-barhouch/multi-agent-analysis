"""Supervisor Agent Class"""

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph_supervisor import create_supervisor
from pydantic import BaseModel, Field

from src.agents import DataManager, DataPrepAgent, InterpreterAgent
from src.core import AgentResult, AgentType, BaseAgent, GlobalState

from .prompts import SUPERVISOR_PROMPT

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
        global_state: GlobalState,
        data_manager: DataManager,
        local_state: GlobalState | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Data Prep Agent."""
        super().__init__(
            agent_type=AgentType.SUPERVISOR,
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

        model = self.config.get("configurable", {}).get("model")
        query = self.global_state.get("user_query", None)

        if model is None:
            # Try to create model using API key from config
            api_key = self.config.get("configurable", {}).get("api_key")
            if api_key:
                try:
                    model = ChatOpenAI(
                        model="gpt-4.1-mini", temperature=0, api_key=api_key
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

        supervisor = create_supervisor(
            agents=[
                interpreter_agent.workflow,
                data_prep_agent.workflow,
            ],
            model=model,
            prompt=SUPERVISOR_PROMPT.format(
                AGENTS="\n".join(
                    f"<agent>{agent.name}"
                    for agent in [interpreter_agent, data_prep_agent]
                ),
                QUERY=query,
            ),
            supervisor_name="Supervisor",
            add_handoff_messages=True,
            add_handoff_back_messages=True,
            response_format=FinalResponse,
        )

        # TODO: check why checkpointer is not working
        # Create persistent checkpointer
        sql_checkpointer = SqliteSaver.from_conn_string("chat_history.db")

        self.workflow = supervisor.compile(
            checkpointer=InMemorySaver(),  # Use in-memory saver for simplicity
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

        # Prepare messages for workflow (include history + current query)
        messages = conversation_history.copy()
        messages.append(HumanMessage(content=query))

        response = await self.workflow.ainvoke(
            {"messages": messages}, config=self.config
        )

        # Enhanced debugging: Access checkpointer state if available
        print(f"\n=== SUPERVISOR WORKFLOW DEBUG ===")
        print(f"Workflow type: {type(self.workflow)}")
        
        # Try to access checkpointer state
        if hasattr(self.workflow, 'checkpointer') and self.workflow.checkpointer:
            checkpointer = self.workflow.checkpointer
            print(f"Checkpointer type: {type(checkpointer)}")
            print(f"Checkpointer available: {checkpointer is not None}")
            
            # Try to get checkpoint data
            try:
                # For InMemorySaver, we might need to access internal storage
                if hasattr(checkpointer, 'storage'):
                    print(f"Checkpointer storage keys: {list(checkpointer.storage.keys()) if checkpointer.storage else 'None'}")
                    
                    # Print checkpoint data for debugging
                    for key, checkpoint_data in checkpointer.storage.items():
                        print(f"Checkpoint {key}: {type(checkpoint_data)}")
                        if hasattr(checkpoint_data, 'channel_values'):
                            print(f"  Channel values: {checkpoint_data.channel_values.keys()}")
                            # Look for messages in the checkpoint
                            if 'messages' in checkpoint_data.channel_values:
                                checkpoint_messages = checkpoint_data.channel_values['messages']
                                print(f"  Checkpoint has {len(checkpoint_messages)} messages")
                                
            except Exception as e:
                print(f"Error accessing checkpointer: {e}")
        else:
            print("No checkpointer available")
        
        print("=== END SUPERVISOR DEBUG ===\n")

        # Placeholder for actual implementation
        return AgentResult(
            success=True,
            data={"message": response},
            error=None,
            metadata={"agent_name": self.name, "checkpointer": getattr(self.workflow, 'checkpointer', None)},
        )

    def validate_input(self) -> None:
        """Validate the input configuration for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for Supervisor Agent.")
        # Model can be None for testing without API key
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
        except Exception as e:
            self.log_activity(f"Error drawing workflow graph: {e}", level="error")
