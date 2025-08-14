"""Data Extractor Agent Module."""

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from src.agents.database_manager import SnowflakeManager as DataManager
from src.config import DEFAULT_MODEL_NAME
from src.core.base_agent import BaseAgent
from src.core.models import AgentResult
from src.core.state import GlobalState
from src.core.types import AgentType

from .prompts import DATA_EXTRACTOR_PROMPT


class DataExtractorAgent(BaseAgent):
    """Agent responsible for SQL generation and data extraction tasks."""

    def __init__(
        self,
        name: str,
        global_state: GlobalState,
        data_manager: DataManager,
        local_state: StateGraph | None = None,
        config: RunnableConfig | None = None,
        logger=None,
    ):
        """Initialize the Data Extractor Agent."""
        super().__init__(
            agent_type=AgentType.DATA_EXTRACTOR,
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

    def _build_safe_sql_db_query(self):
        """
        Return a Tool that runs a validated SQL query and stores
        results in state.
        """

        @tool("sql_db_query")
        def safe_sql_db_query(query: str) -> str:
            """Execute SQL query safely and return results."""
            # Execute query using data manager
            query_preview = query[:200] + "..." if len(query) > 200 else query
            self.log_activity(
                f"[DATA EXTRACTOR] Executing SQL: {query_preview}"
            )
            try:
                df = self.data_manager.query(query)
                self.log_activity(
                    f"[DATA EXTRACTOR] Query executed successfully. "
                    f"Got {len(df)} rows, {len(df.columns)} columns"
                )
                
                # Store results in global state for other agents
                if hasattr(self.global_state, 'update') and callable(self.global_state.update):
                    self.global_state.update({
                        'last_dataframe': df,
                        'viz_dataframe': df,
                        'query_executed': query,
                        'data_source': 'database'
                    })
                else:
                    # If global_state is a dict
                    self.global_state['last_dataframe'] = df
                    self.global_state['viz_dataframe'] = df
                    self.global_state['query_executed'] = query
                    self.global_state['data_source'] = 'database'
                
                self.log_activity(
                    "[DATA EXTRACTOR] Data stored in global state for other agents"
                )
                
                # Return summary for the agent with actual data preview
                preview = df.head(3).to_string() if len(df) > 0 else "No data returned"
                result_summary = (
                    f"Query executed successfully. Retrieved {len(df)} rows "
                    f"with {len(df.columns)} columns from database. "
                    f"Data stored in global state.\n\nData preview:\n{preview}\n\n"
                    f"TASK COMPLETED. Transfer back to supervisor immediately."
                )
                return result_summary
            except Exception as e:
                error_msg = f"[DATA EXTRACTOR] SQL execution failed: {e}"
                self.log_activity(error_msg, level="error")
                return f"SQL execution failed: {e}. Transfer back to supervisor."

        return safe_sql_db_query

    def _get_database_schema_ddl(self) -> str:
        """
        Fetch complete database schema DDL for context.
        Returns formatted schema information for SQL generation.
        """
        try:
            if not self.data_manager:
                return "No database connection available"
            
            self.log_activity("[DATA EXTRACTOR] Fetching database schema DDL")
            
            # Get list of tables
            tables = self.data_manager.list_tables()
            if not tables:
                return "No tables found in database"
            
            schema_ddl = []
            schema_ddl.append("=== DATABASE SCHEMA DDL ===")
            
            # Get database and schema info from config
            database_name = getattr(self.data_manager, 'config', {}).get('database', 'Unknown')
            schema_name = getattr(self.data_manager, 'config', {}).get('schema', 'Unknown')
            
            schema_ddl.append(f"Database: {database_name}")
            schema_ddl.append(f"Schema: {schema_name}")
            schema_ddl.append("")
            
            for table in tables:
                try:
                    # Get table schema using SQL toolkit approach
                    table_info = self.data_manager.get_table_info(table)
                    schema_ddl.append(f"TABLE: {table}")
                    schema_ddl.append("-" * (len(table) + 7))
                    schema_ddl.append(table_info)
                    schema_ddl.append("")
                    
                    self.log_activity(f"[DATA EXTRACTOR] Retrieved schema for table: {table}")
                    
                except Exception as e:
                    self.log_activity(f"[DATA EXTRACTOR] Error getting schema for {table}: {e}", level="warning")
                    schema_ddl.append(f"TABLE: {table} (schema unavailable)")
                    schema_ddl.append("")
            
            full_schema = "\n".join(schema_ddl)
            self.log_activity(f"[DATA EXTRACTOR] Schema DDL retrieved successfully ({len(full_schema)} chars)")
            return full_schema
            
        except Exception as e:
            error_msg = f"[DATA EXTRACTOR] Error fetching schema DDL: {e}"
            self.log_activity(error_msg, level="error")
            return f"Schema unavailable: {e}"

    def create_workflow(self):
        """Create the data extraction workflow using SQL database toolkit."""
        try:
            # Get SQL tools from config or create default toolkit
            config_sql_tools = self.config.get("tools", []) if self.config else []
            
            # If no tools in config, create default SQL toolkit
            if not config_sql_tools and self.data_manager:
                model = ChatOpenAI(model=DEFAULT_MODEL_NAME)
                toolkit = SQLDatabaseToolkit(
                    db=self.data_manager.db, llm=model
                )
                config_sql_tools = toolkit.get_tools()
                self.log_activity(
                    "[DATA EXTRACTOR] Created default SQL toolkit"
                )
            
            # Build custom safe SQL query tool
            safe_sql_tool = self._build_safe_sql_db_query()
            
            # Replace the sql_db_query tool with our safe version
            tools = []
            for sql_tool in config_sql_tools:
                if (hasattr(sql_tool, 'name') and 
                    sql_tool.name == 'sql_db_query'):
                    tools.append(safe_sql_tool)
                    self.log_activity(
                        "[DATA EXTRACTOR] Replaced sql_db_query"
                    )
                else:
                    tools.append(sql_tool)
            
            # Add safe tool if no replacement occurred
            if safe_sql_tool not in tools:
                tools.append(safe_sql_tool)
                self.log_activity(
                    "[DATA EXTRACTOR] Added safe_sql_db_query tool"
                )

            schema_ddl = self._get_database_schema_ddl()
            tool_info = "\n".join(
                f"<tool>{t.name}: {getattr(t, 'description', '')}</tool>"
                for t in tools
            )

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(DATA_EXTRACTOR_PROMPT.format(
                    TOOLS=tool_info,
                    SCHEMA_DDL=schema_ddl
                ))
            ])

            self.workflow = create_react_agent(
                model=ChatOpenAI(model="gpt-4o"),
                tools=tools,
                prompt=prompt,
                name="data_extractor"
            )
            
            self.log_activity(
                "[DATA EXTRACTOR] Workflow initialized successfully"
            )
        except Exception as e:
            self.log_activity(
                f"[DATA EXTRACTOR] Error creating workflow: {e}", 
                level="error"
            )
            self.workflow = None

        return self.workflow

    async def execute(self) -> AgentResult:
        """
        Execute data extraction based on global state query.

        Returns:
            AgentResult with success status and data
        """
        try:
            if self.workflow is None:
                self.log_activity(
                    "Workflow not initialized", level="error"
                )
                return AgentResult(
                    success=False,
                    data=None,
                    error="Workflow not initialized",
                    metadata={"agent_name": self.name},
                )
        except AttributeError:
            pass

        # Get query from global state
        query = self.global_state.get("user_query", "")
        if not query:
            self.log_activity(
                "No query provided for data extraction.", level="error"
            )
            return AgentResult(
                success=False,
                data=None,
                error="No query provided",
                metadata={"agent_name": self.name},
            )

        try:
            # Log the input
            self.log_activity(
                f"[DATA EXTRACTOR] Processing query: {query[:200]}"
            )
            
            # Log workflow invocation start
            self.log_activity(
                "[DATA EXTRACTOR] Starting workflow execution"
            )

            # Use the standard workflow for SQL generation and execution
            response = await self.workflow.ainvoke(
                {"messages": [HumanMessage(content=query)]}, config=self.config
            )

            self.log_activity(
                "[DATA EXTRACTOR] Workflow execution completed"
            )
            
            self.log_activity(
                f"[DATA EXTRACTOR] Response generated: {str(response)[:500]}"
            )
            
            return AgentResult(
                success=True,
                data={"response": response},
                error=None,
                metadata={"agent_name": self.name},
            )

        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            self.log_activity(error_msg, level="error")
            return AgentResult(
                success=False,
                data=None,
                error=error_msg,
                metadata={"agent_name": self.name},
            )

    def validate_input(self) -> None:
        """Validate the input configuration for the agent."""
        if not self.config:
            raise ValueError("Configuration is required for DataExtractorAgent.")
        # Model can be None for testing without API key
        self.log_activity("Input validation completed successfully.")


