"""
Streamlit-specific formatters for displaying execution results in the web interface.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.core.runner import ExecutionResult


class StreamlitFormatter:
    """Formats execution results for Streamlit display."""

    @staticmethod
    def format_agent_name(agent_name: str) -> str:
        """Clean and format agent names."""
        if not agent_name:
            return "Unknown Agent"
        agent_name = agent_name.replace("_", " ").title()
        if "Supervisor" in agent_name:
            return "🎯 Supervisor"
        elif "data_prep" in agent_name.lower():
            return "📊 Data Prep"
        elif "interpreter" in agent_name.lower():
            return "🧠 Interpreter"
        return f"🤖 {agent_name}"

    def display_agent_collaboration(self, result: ExecutionResult):
        """Display agent collaboration flow."""
        agents = []
        for item in result.agent_flow:
            if not item.get("agent"):
                continue
            if item["type"] == "agent_response":
                agent_name = self.format_agent_name(item["agent"])
                if agent_name not in agents:
                    agents.append(agent_name)

        if agents:
            st.markdown("**Agent Collaboration Flow:**")
            collaboration = " ➜ ".join(agents)
            st.info(collaboration)
        else:
            st.info("Single agent response")

    def display_tool_details(self, result: ExecutionResult):
        """Display detailed agent responses in a structured format."""
        details_found = False

        for item in result.agent_flow:
            if item["type"] == "agent_response" and item.get("content", "").strip():
                agent_name = self.format_agent_name(item["agent"])
                content = item["content"]

                st.markdown(f"**{agent_name} Response:**")

                # Format structured responses
                if "<thought_process>" in content and "<result>" in content:
                    # Extract and format thought process and result separately
                    thought_start = content.find("<thought_process>") + 17
                    thought_end = content.find("</thought_process>")
                    result_start = content.find("<result>") + 8
                    result_end = content.find("</result>")

                    if thought_start > 17 and thought_end > thought_start:
                        thought = content[thought_start:thought_end].strip()
                        with st.expander(
                            f"💭 {agent_name} Thinking Process", expanded=False
                        ):
                            st.write(thought)

                    if result_start > 8 and result_end > result_start:
                        result_content = content[result_start:result_end].strip()
                        st.success(f"**Result:** {result_content}")
                else:
                    # Show full content for non-structured responses
                    st.write(content)

                details_found = True
                st.markdown("---")

        if not details_found:
            st.info("No detailed agent responses available.")

    def display_tool_calls_table(self, tool_calls: List[Dict[str, Any]]):
        """Display tool calls in a formatted table."""
        if not tool_calls:
            st.info("No tool calls recorded.")
            return

        # Prepare data for DataFrame
        table_data = []

        for tool in tool_calls:
            tool_name = tool["name"]
            agent_name = self.format_agent_name(tool.get("agent", "Unknown"))

            # Determine purpose and format based on tool type
            if "transfer_to_" in tool_name:
                target = tool_name.replace("transfer_to_", "").replace("_", " ").title()
                purpose = f"Delegate to {target}"
                args_display = "-"
                result_display = tool.get(
                    "result", f"Successfully transferred to {target.lower()}"
                )
            elif "transfer_back" in tool_name:
                purpose = "Return Control"
                args_display = "-"
                result_display = tool.get(
                    "result", "Successfully transferred back to Supervisor"
                )
            elif "sql_db_list_tables" in tool_name:
                purpose = "List Database Tables"
                args_display = "-"
                result_display = self._format_result(tool.get("result", ""))
            elif "sql_db_query" in tool_name:
                purpose = "Execute SQL Query"
                args_display = self._format_sql_query(tool.get("args", {}))
                result_display = self._format_result(tool.get("result", ""))
            elif "sql_db_schema" in tool_name:
                purpose = "Get Table Schema"
                table_name = tool.get("args", {}).get(
                    "table_names_to_use", ""
                ) or tool.get("args", {}).get("table", "")
                args_display = (
                    f"Table: {table_name}"
                    if table_name
                    else self._format_args(tool.get("args", {}))
                )
                result_display = self._format_result(tool.get("result", ""))
            elif "python" in tool_name.lower() or "sandbox" in tool_name.lower():
                purpose = "Execute Python Code"
                args_display = self._format_python_code(tool.get("args", {}))
                result_display = self._format_result(tool.get("result", ""))
            else:
                purpose = "Custom Tool"
                args_display = self._format_args(tool.get("args", {}))
                result_display = self._format_result(tool.get("result", ""))

            # Clean up tool name for display
            if "sql_db_" in tool_name:
                display_name = (
                    tool_name.replace("sql_db_", "SQL: ").replace("_", " ").title()
                )
            elif "pyodide_" in tool_name:
                display_name = "Python Sandbox"
            else:
                display_name = tool_name.replace("_", " ").title()

            table_data.append(
                {
                    "Agent": agent_name,
                    "Tool Name": display_name,
                    "Purpose": purpose,
                    "Arguments": args_display,
                    "Result Preview": result_display,
                }
            )

        # Create and display DataFrame
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

        # Additional details for complex results
        if any("sql" in tool["name"].lower() for tool in tool_calls):
            st.info("💡 SQL tool calls contain database queries and results.")

    def display_execution_stats(self, result: ExecutionResult):
        """Display execution statistics in metrics format."""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Execution Time",
                f"{result.execution_time:.2f}s",
                help="Total time taken to process the query",
            )

        with col2:
            agents_count = len(
                set(
                    item["agent"]
                    for item in result.agent_flow
                    if item["type"] == "agent_response" and item.get("agent")
                )
            )
            st.metric(
                "Agents Involved",
                agents_count,
                help="Number of different agents that participated",
            )

        with col3:
            st.metric(
                "Tool Calls",
                len(result.tool_calls),
                help="Total number of tool calls made",
            )

        with col4:
            transfer_count = sum(
                1 for tool in result.tool_calls if "transfer" in tool["name"].lower()
            )
            st.metric(
                "Agent Transfers",
                transfer_count,
                help="Number of times control was transferred between agents",
            )

        # Token usage if available
        if result.token_usage:
            st.markdown("**Token Usage:**")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Input Tokens", f"{result.token_usage['input']:,}")
            with col2:
                st.metric("Output Tokens", f"{result.token_usage['output']:,}")
            with col3:
                st.metric("Total Tokens", f"{result.token_usage['total']:,}")

        # Success indicator
        if result.success:
            st.success("✅ Query executed successfully")
        else:
            st.error(f"❌ Query failed: {result.error}")

    def _format_sql_query(self, args: dict) -> str:
        """Format SQL query from arguments."""
        if not args:
            return "-"

        query = args.get("query", "")
        if isinstance(query, str) and query.strip():
            query = query.strip()
            query = " ".join(query.split())
            if len(query) > 100:
                return query[:100] + "..."
            return query

        if "table_names_to_use" in args:
            return f"Table: {args['table_names_to_use']}"
        elif "schema" in args:
            return f"Schema: {args['schema']}"

        args_str = str(args)
        if len(args_str) > 100:
            return args_str[:100] + "..."
        return args_str

    def _format_python_code(self, args: dict) -> str:
        """Format Python code from arguments."""
        code = args.get("code", "") or args.get("script", "")
        if isinstance(code, str):
            lines = [line.strip() for line in code.split("\n") if line.strip()]
            if lines:
                first_line = lines[0]
                if len(first_line) > 80:
                    return first_line[:80] + "..."
                return first_line
        return str(args)[:80]

    def _format_args(self, args: Any, max_length: int = 100) -> str:
        """Format tool arguments for display."""
        if not args:
            return "-"

        if isinstance(args, dict):
            if not args:
                return "-"

            if "query" in args:
                return self._format_sql_query(args)
            elif "code" in args or "script" in args:
                return self._format_python_code(args)
            elif "table" in args or "table_names_to_use" in args:
                table_name = args.get("table") or args.get("table_names_to_use", "")
                return f"Table: {table_name}" if table_name else str(args)

            items = []
            for key, value in args.items():
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                items.append(f"{key}: {value}")

            args_str = ", ".join(items)
            if len(args_str) > max_length:
                return args_str[:max_length] + "..."
            return args_str

        args_str = str(args)
        if len(args_str) > max_length:
            return args_str[:max_length] + "..."
        return args_str

    def _format_result(self, result: Any, max_length: int = 80) -> str:
        """Format tool result for display."""
        if not result:
            return "-"

        result_str = str(result).strip()

        # Handle tabular data
        if "\n" in result_str and "|" in result_str:
            lines = result_str.split("\n")
            for line in lines:
                if line.strip() and not all(c in "-|+" for c in line.strip()):
                    if len(line) > max_length:
                        return line[: max_length - 3] + "..."
                    return line

        # Handle lists
        if result_str.startswith("[") and result_str.endswith("]"):
            try:
                items = eval(result_str)
                if isinstance(items, list) and items:
                    preview = f"{items[0]}" + (
                        f" (+{len(items)-1} more)" if len(items) > 1 else ""
                    )
                    if len(preview) > max_length:
                        return preview[: max_length - 3] + "..."
                    return preview
            except:
                pass

        # Default truncation
        if len(result_str) > max_length:
            return result_str[: max_length - 3] + "..."
        return result_str

    def display_global_state(self, global_state):
        """Display the global state in a structured format."""
        if not global_state:
            st.info("No global state available.")
            return

        # Session Information
        st.markdown("### 🔍 Session Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Session ID", global_state.get("session_id", "N/A"))
        with col2:
            st.metric("Current Agent", global_state.get("current_agent", "None"))
        with col3:
            st.metric("Query Count", len(global_state.get("conversation_history", [])) // 2)

        # Conversation State
        with st.expander("💬 Conversation State", expanded=False):
            conversation_history = global_state.get("conversation_history", [])
            max_messages = global_state.get("max_messages", 20)
            enable_trimming = global_state.get("enable_trimming", False)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Messages", len(conversation_history))
            with col2:
                st.metric("Max Messages", max_messages)
            with col3:
                st.info("Trimming: " + ("✅" if enable_trimming else "❌"))

        # Planning State
        with st.expander("📋 Planning & Tasks", expanded=False):
            current_task = global_state.get("current_task")
            todo_plan = global_state.get("todo_plan", [])
            
            if current_task:
                st.info(f"**Current Task:** {current_task}")
            else:
                st.info("**Current Task:** None")
                
            if todo_plan:
                st.markdown(f"**Todo Plan ({len(todo_plan)} items):**")
                for i, task in enumerate(todo_plan, 1):
                    if isinstance(task, dict):
                        task_name = task.get("name", task.get("description", str(task)))
                        task_status = task.get("status", "unknown")
                        status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(task_status, "❓")
                        st.markdown(f"{i}. {status_emoji} {task_name}")
                    else:
                        st.markdown(f"{i}. {task}")
            else:
                st.info("No planned tasks")

        # Data State
        with st.expander("📊 Data State", expanded=False):
            available_tables = global_state.get("available_tables", [])
            created_subtables = global_state.get("created_subtables", [])
            data_descriptions = global_state.get("data_descriptions", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Available Tables", len(available_tables))
                if available_tables:
                    st.markdown("**Tables:**")
                    for table in available_tables[:5]:  # Show first 5
                        table_name = table.get("name", str(table)) if isinstance(table, dict) else str(table)
                        st.markdown(f"• {table_name}")
                    if len(available_tables) > 5:
                        st.markdown(f"... and {len(available_tables) - 5} more")
                        
            with col2:
                st.metric("Created Subtables", len(created_subtables))
                if created_subtables:
                    st.markdown("**Subtables:**")
                    for subtable in created_subtables[:5]:
                        st.markdown(f"• {subtable}")
                    if len(created_subtables) > 5:
                        st.markdown(f"... and {len(created_subtables) - 5} more")
            
            if data_descriptions:
                st.markdown("**Data Descriptions:**")
                for name, desc in list(data_descriptions.items())[:3]:
                    st.markdown(f"• **{name}:** {desc[:100]}{'...' if len(desc) > 100 else ''}")
                if len(data_descriptions) > 3:
                    st.markdown(f"... and {len(data_descriptions) - 3} more")

        # Dashboard State
        dashboard_layout = global_state.get("dashboard_layout", {})
        widget_specs = global_state.get("widget_specs", {})
        widget_data_queries = global_state.get("widget_data_queries", {})
        
        if dashboard_layout or widget_specs or widget_data_queries:
            with st.expander("📈 Dashboard State", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Layout Items", len(dashboard_layout))
                with col2:
                    st.metric("Widget Specs", len(widget_specs))
                with col3:
                    st.metric("Data Queries", len(widget_data_queries))

        # Agent Communication
        with st.expander("🤖 Agent Communication", expanded=False):
            agent_history = global_state.get("agent_history", [])
            current_agent = global_state.get("current_agent")
            
            if current_agent:
                st.info(f"**Active Agent:** {self.format_agent_name(current_agent)}")
            
            if agent_history:
                st.markdown(f"**Agent History ({len(agent_history)} agents):**")
                agent_flow = " ➜ ".join([self.format_agent_name(agent) for agent in agent_history[-5:]])  # Last 5
                st.markdown(agent_flow)
                if len(agent_history) > 5:
                    st.markdown(f"... and {len(agent_history) - 5} earlier agents")
            else:
                st.info("No agent history")

        # Execution State
        errors = global_state.get("errors", [])
        warnings = global_state.get("warnings", [])
        
        if errors or warnings:
            with st.expander("⚠️ Execution State", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    if errors:
                        st.error(f"**Errors ({len(errors)}):**")
                        for error in errors[:3]:
                            error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                            st.markdown(f"• {error_msg}")
                        if len(errors) > 3:
                            st.markdown(f"... and {len(errors) - 3} more errors")
                    else:
                        st.success("**Errors:** None")
                        
                with col2:
                    if warnings:
                        st.warning(f"**Warnings ({len(warnings)}):**")
                        for warning in warnings[:3]:
                            warning_msg = warning.get("message", str(warning)) if isinstance(warning, dict) else str(warning)
                            st.markdown(f"• {warning_msg}")
                        if len(warnings) > 3:
                            st.markdown(f"... and {len(warnings) - 3} more warnings")
                    else:
                        st.success("**Warnings:** None")

