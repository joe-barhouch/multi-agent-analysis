"""Formatters for CLI output presentation."""

from typing import Any, Dict, List

from rich.table import Table
from rich.tree import Tree

from src.core.runner import ExecutionResult


class ResultFormatter:
    """Formats execution results for display."""

    @staticmethod
    def format_agent_name(agent_name: str) -> str:
        """Clean and format agent names."""
        if not agent_name:
            return "Unknown Agent"
        agent_name = agent_name.replace("_", " ").title()
        if "Supervisor" in agent_name:
            return "Supervisor"
        elif "data_extractor" in agent_name.lower():
            return "🗂️"
        elif "interpreter" in agent_name.lower():
            return "Interpreter"
        return agent_name

    @staticmethod
    def format_agent_collaboration_summary(result: ExecutionResult) -> str:
        """Format a concise agent collaboration summary."""
        agents = []
        for item in result.agent_flow:
            if not item.get("agent"):
                continue
            if item["type"] == "agent_response":
                agent_name = ResultFormatter.format_agent_name(item["agent"])
                if agent_name not in agents:
                    agents.append(agent_name)

        # Create clean agent flow
        collaboration_text = "\n🔄 Agent Collaboration:\n"
        if agents:
            collaboration_text += f"  {' → '.join(agents)}"
        else:
            collaboration_text += "  Single agent response"

        return collaboration_text

    @staticmethod
    def format_agent_flow_tree(result: ExecutionResult) -> Tree:
        """Create a SIMPLIFIED agent flow tree showing only handoffs."""
        tree = Tree("🔄 Agent Flow")

        for item in result.agent_flow:
            if item["type"] == "user_input":
                content_preview = (
                    item["content"][:50] + "..."
                    if len(item["content"]) > 50
                    else item["content"]
                )
                tree.add(f"👤 User: {content_preview}")

            elif item["type"] == "agent_response":
                agent_name = ResultFormatter.format_agent_name(item["agent"])

                # Only show agent handoffs, not detailed responses
                tree.add(f"🤖 {agent_name}: [Processing...]")

            elif item["type"] == "tool_call":
                tool_name = item["tool_name"]

                # Only show transfer operations, not detailed tool calls
                if "transfer" in tool_name.lower():
                    tree.add(f"↔️  {tool_name.replace('_', ' ').title()}")

        return tree

    @staticmethod
    def create_tool_details_panel(result: ExecutionResult) -> str:
        """Create a separate Tool Details panel with detailed agent responses."""
        details = []

        for item in result.agent_flow:
            if item["type"] == "agent_response" and item.get("content", "").strip():
                agent_name = ResultFormatter.format_agent_name(item["agent"])
                content = item["content"]

                # Format the detailed response
                if "<thought_process>" in content and "<result>" in content:
                    # Extract and format thought process and result separately
                    thought_start = content.find("<thought_process>") + 17
                    thought_end = content.find("</thought_process>")
                    result_start = content.find("<result>") + 8
                    result_end = content.find("</result>")

                    if thought_start > 17 and thought_end > thought_start:
                        thought = content[thought_start:thought_end].strip()
                        details.append(f"💭 {agent_name} Thinking:\n{thought}")

                    if result_start > 8 and result_end > result_start:
                        result = content[result_start:result_end].strip()
                        details.append(f"✅ {agent_name} Result:\n{result}")
                else:
                    # Show full content for non-structured responses
                    details.append(f"🤖 {agent_name}:\n{content}")

        return "\n\n".join(details) if details else "No detailed responses available."

    # @staticmethod
    # def format_agent_flow_tree(result: ExecutionResult) -> Tree:
    #     """Create a simplified, high-level agent flow tree."""
    #     tree = Tree("🔄 Agent Flow")
    #
    #     for item in result.agent_flow:
    #         if item["type"] == "user_input":
    #             content_preview = (
    #                 item["content"][:50] + "..."
    #                 if len(item["content"]) > 50
    #                 else item["content"]
    #             )
    #             tree.add(f"👤 User: {content_preview}")
    #
    #         elif item["type"] == "agent_response":
    #             agent_name = ResultFormatter.format_agent_name(item["agent"])
    #             tool_count = len(item.get("tool_calls", []))
    #             node_text = f"🤖 {agent_name}"
    #
    #             # Add a preview of the agent's thought process or response
    #             if item.get("content", "").strip():
    #                 content = item["content"]
    #                 if "<thought_process>" in content:
    #                     start = content.find("<thought_process>") + 17
    #                     end = content.find("</thought_process>")
    #                     if start > 17 and end > start:
    #                         thought = content[start:end].strip()[:60] + "..."
    #                         node_text += f": 💭 {thought}"
    #                 else:
    #                     preview = content[:60] + "..." if len(content) > 60 else content
    #                     node_text += f": {preview}"
    #
    #             # Indicate that tools were called without showing details
    #             if tool_count > 0:
    #                 node_text += (
    #                     f" [dim](initiating {tool_count} tool"
    #                     f"{'s' if tool_count > 1 else ''})[/dim]"
    #                 )
    #
    #             tree.add(node_text)
    #
    #     return tree

    @staticmethod
    def format_tool_calls_table(tool_calls: List[Dict[str, Any]]) -> Table:
        """Create a formatted table of tool calls with hierarchical organization."""
        table = Table(
            title="🔧 Tool Calls",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Agent", style="yellow", no_wrap=True)
        table.add_column("Tool Name", style="green", no_wrap=True)
        table.add_column("Purpose", style="blue")
        table.add_column("Arguments/Query", style="dim", max_width=40)
        table.add_column("Result Preview", style="italic", max_width=40)

        # Group tool calls by agent for better organization
        agent_groups = {}
        for tool in tool_calls:
            agent = tool.get("agent", "Unknown")
            if agent not in agent_groups:
                agent_groups[agent] = []
            agent_groups[agent].append(tool)

        # Add tools in logical order: Supervisor first, then other agents
        agent_order = ["Supervisor", "Data Prep", "Interpreter", "Unknown"]
        processed_agents = set()

        for preferred_agent in agent_order:
            if preferred_agent in agent_groups:
                for tool in agent_groups[preferred_agent]:
                    ResultFormatter._add_tool_row_to_table(table, tool)
                processed_agents.add(preferred_agent)

        # Add any remaining agents not in the preferred order
        for agent, tools in agent_groups.items():
            if agent not in processed_agents:
                for tool in tools:
                    ResultFormatter._add_tool_row_to_table(table, tool)

        return table

    @staticmethod
    def _add_tool_row_to_table(table: Table, tool: Dict[str, Any]) -> None:
        """Add a single tool call row to the table."""
        tool_name = tool["name"]
        agent_name = ResultFormatter.format_agent_name(tool.get("agent", "Unknown"))

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
            result_display = ResultFormatter._format_result(tool.get("result", ""))
        elif "sql_db_query" in tool_name:
            purpose = "Execute SQL Query"
            args_display = ResultFormatter._format_sql_query(tool.get("args", {}))
            result_display = ResultFormatter._format_result(tool.get("result", ""))
        elif "sql_db_schema" in tool_name:
            purpose = "Get Table Schema"
            table_name = tool.get("args", {}).get("table_names_to_use", "") or tool.get(
                "args", {}
            ).get("table", "")
            args_display = (
                f"Table: {table_name}"
                if table_name
                else ResultFormatter._format_args(tool.get("args", {}))
            )
            result_display = ResultFormatter._format_result(tool.get("result", ""))
        elif "python" in tool_name.lower() or "sandbox" in tool_name.lower():
            purpose = "Execute Python Code"
            args_display = ResultFormatter._format_python_code(tool.get("args", {}))
            result_display = ResultFormatter._format_result(tool.get("result", ""))
        else:
            purpose = "Custom Tool"
            args_display = ResultFormatter._format_args(tool.get("args", {}))
            result_display = ResultFormatter._format_result(tool.get("result", ""))

        # Clean up tool name for display
        if "sql_db_" in tool_name:
            display_name = (
                tool_name.replace("sql_db_", "SQL: ").replace("_", " ").title()
            )
        elif "pyodide_" in tool_name:
            display_name = "Python Sandbox"
        else:
            display_name = tool_name.replace("_", " ").title()

        table.add_row(agent_name, display_name, purpose, args_display, result_display)

    @staticmethod
    def _format_sql_query(args: dict) -> str:
        """Format SQL query from arguments."""
        if not args:
            return "-"

        query = args.get("query", "")
        if isinstance(query, str) and query.strip():
            # Clean up and truncate long queries
            query = query.strip()
            # Replace newlines and extra spaces with single spaces
            query = " ".join(query.split())
            if len(query) > 50:
                return query[:50] + "..."
            return query

        # Check for other common argument patterns
        if "table_names_to_use" in args:
            return f"Table: {args['table_names_to_use']}"
        elif "schema" in args:
            return f"Schema: {args['schema']}"

        # Fall back to showing all args
        args_str = str(args)
        if len(args_str) > 50:
            return args_str[:50] + "..."
        return args_str

    @staticmethod
    def _format_python_code(args: dict) -> str:
        """Format Python code from arguments."""
        code = args.get("code", "") or args.get("script", "")
        if isinstance(code, str):
            # Get first meaningful line
            lines = [line.strip() for line in code.split("\n") if line.strip()]
            if lines:
                first_line = lines[0]
                if len(first_line) > 40:
                    return first_line[:50] + "..."
                return first_line
        return str(args)[:40]

    @staticmethod
    def _format_result(result: Any, max_length: int = 40) -> str:
        """Format tool result for display."""
        if not result:
            return "-"

        result_str = str(result).strip()

        # Handle tabular data
        if "\n" in result_str and "|" in result_str:
            # Extract first row of data
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
                        f" (+{len(items) - 1} more)" if len(items) > 1 else ""
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

    @staticmethod
    def format_token_usage_table(token_usage: Dict[str, int]) -> Table:
        """Create a formatted token usage table."""
        table = Table(
            title="📊 Token Usage", show_header=True, header_style="bold magenta"
        )
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Input", f"{token_usage['input']:,}")
        table.add_row("Output", f"{token_usage['output']:,}")
        table.add_row("Total", f"{token_usage['total']:,}", style="bold")

        # Add cost estimation TODO
        # cost_per_1k = 0.0001  # Example rate
        # total_cost = (token_usage['total'] / 1000) * cost_per_1k
        # table.add_row("Est. Cost", f"${total_cost:.4f}", style="dim")

        return table

    @staticmethod
    def _format_args(args: Any, max_length: int = 50) -> str:
        """Format tool arguments for display."""
        if not args:
            return "-"

        # Handle dict arguments
        if isinstance(args, dict):
            if not args:
                return "-"

            # Check for common patterns
            if "query" in args:
                return ResultFormatter._format_sql_query(args)
            elif "code" in args or "script" in args:
                return ResultFormatter._format_python_code(args)
            elif "table" in args or "table_names_to_use" in args:
                table_name = args.get("table") or args.get("table_names_to_use", "")
                return f"Table: {table_name}" if table_name else str(args)

            # Show key-value pairs in a readable format
            items = []
            for key, value in args.items():
                if isinstance(value, str) and len(value) > 30:
                    value = value[:30] + "..."
                items.append(f"{key}: {value}")

            args_str = ", ".join(items)
            if len(args_str) > max_length:
                return args_str[:max_length] + "..."
            return args_str

        # Handle other types
        args_str = str(args)
        if len(args_str) > max_length:
            return args_str[:max_length] + "..."
        return args_str

    @staticmethod
    def format_execution_stats(result: ExecutionResult) -> Table:
        """Create an execution statistics table."""
        table = Table(
            title="📈 Execution Statistics", show_header=True, header_style="bold blue"
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        # Count different types of tools
        sql_count = sum(
            1 for tool in result.tool_calls if "sql" in tool["name"].lower()
        )
        python_count = sum(
            1
            for tool in result.tool_calls
            if "python" in tool["name"].lower() or "sandbox" in tool["name"].lower()
        )
        transfer_count = sum(
            1 for tool in result.tool_calls if "transfer" in tool["name"].lower()
        )

        table.add_row("Execution Time", f"{result.execution_time:.2f}s")
        table.add_row(
            "Agents Involved",
            str(
                len(
                    set(
                        item["agent"]
                        for item in result.agent_flow
                        if item["type"] == "agent_response"
                    )
                )
            ),
        )
        table.add_row("Total Tool Calls", str(len(result.tool_calls)))

        if sql_count > 0:
            table.add_row("SQL Queries", str(sql_count))
        if python_count > 0:
            table.add_row("Python Scripts", str(python_count))
        if transfer_count > 0:
            table.add_row("Agent Transfers", str(transfer_count))

        table.add_row("Success", "✅" if result.success else "❌")

        return table
