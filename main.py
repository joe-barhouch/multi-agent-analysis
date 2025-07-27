"""Interactive CLI for the multi-agent supervisor system."""

import argparse
import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from src.agents.data_manager import DataManager
from src.agents.supervisor.agent import Supervisor
from src.core.base_agent import BaseAgent

load_dotenv()

# Initialize Rich console
console = Console()


def print_banner():
    """Print cool banner and system info."""
    print("\n" + "=" * 60)
    print("🤖 MULTI-AGENT SUPERVISOR SYSTEM 🤖")
    print("=" * 60)
    print("Interactive Financial Data Analysis CLI")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def print_config(api_key, model, data_manager, verbose=False):
    """Display current configuration."""
    print("\n📋 CONFIGURATION:")
    print("-" * 30)
    print(f"API Key: {'✅ Set' if api_key else '❌ Not Set'}")
    print(f"Model: {'gpt-4.1-mini' if model else '❌ Unavailable'}")
    print(f"Database: {data_manager.path}")
    print(f"Status: {'🟢 Ready' if api_key else '🟡 Limited Mode'}")
    if verbose:
        print("Verbose Mode: ✅ Enabled")
    print("-" * 30)


def extract_ai_response(result_data):
    """Extract clean AI response from LangChain message format."""
    try:
        if not result_data or "message" not in result_data:
            return None

        messages = result_data["message"].get("messages", [])

        # Find the last AIMessage
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                return message.content

        return None
    except Exception:
        return None


def get_token_usage(result_data):
    """Extract token usage information from result."""
    try:
        messages = result_data["message"].get("messages", [])
        for message in reversed(messages):
            if isinstance(message, AIMessage) and hasattr(message, "usage_metadata"):
                usage = message.usage_metadata
                return {
                    "total": usage.get("total_tokens", 0),
                    "input": usage.get("input_tokens", 0),
                    "output": usage.get("output_tokens", 0),
                }
        return None
    except Exception:
        return None


def extract_agent_flow(result_data):
    """Extract agent coordination flow from message history."""
    try:
        if not result_data or "message" not in result_data:
            return []

        messages = result_data["message"].get("messages", [])
        flow = []
        current_agent = None

        for message in messages:
            if isinstance(message, HumanMessage):
                flow.append(
                    {"type": "user_input", "content": message.content, "agent": "User"}
                )
            elif isinstance(message, AIMessage):
                agent_name = getattr(message, "name", "Unknown")
                if agent_name and agent_name != current_agent:
                    current_agent = agent_name
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


def extract_tool_calls(result_data):
    """Extract tool usage information."""
    try:
        if not result_data or "message" not in result_data:
            return []

        messages = result_data["message"].get("messages", [])
        tools_used = []

        for message in messages:
            if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
                for tool_call in message.tool_calls:
                    tools_used.append(
                        {
                            "name": tool_call.get("name", "Unknown"),
                            "args": tool_call.get("args", {}),
                            "id": tool_call.get("id", ""),
                        }
                    )

        return tools_used
    except Exception:
        return []


def format_agent_collaboration(result_data):
    """Format agent collaboration summary for normal mode."""
    flow = extract_agent_flow(result_data)
    tools = extract_tool_calls(result_data)

    if not flow:
        return ""

    # Extract unique agents in order
    agents = []
    for item in flow:
        if item["type"] == "agent_response" and item["agent"] not in agents:
            # Clean agent names
            agent_name = item["agent"].replace("_", " ").title()
            if "Supervisor" in agent_name:
                agent_name = "Supervisor"
            elif "data_prep" in agent_name.lower():
                agent_name = "Data Prep"
            elif "interpreter" in agent_name.lower():
                agent_name = "Interpreter"
            agents.append(agent_name)

    collaboration_text = "\n🔄 Agent Collaboration:\n"
    collaboration_text += f"  {' → '.join(agents)}\n"

    if tools:
        tool_names = [
            tool["name"].replace("transfer_to_", "").replace("_", " ").title()
            for tool in tools
            if not tool["name"].startswith("transfer_back")
        ]
        if tool_names:
            collaboration_text += f"  Tools Used: {', '.join(set(tool_names))}"

    return collaboration_text


def format_agent_flow_detailed(result_data):
    """Format detailed agent flow for verbose mode."""
    flow = extract_agent_flow(result_data)

    if not flow:
        return ""

    tree = Tree("🔄 Agent Flow")

    for i, item in enumerate(flow):
        if item["type"] == "user_input":
            tree.add(f"👤 User: {item['content'][:50]}...")
        elif item["type"] == "agent_response":
            agent_name = item["agent"].replace("_", " ").title()
            if "Supervisor" in agent_name:
                agent_name = "Supervisor"
            elif "data_prep" in agent_name.lower():
                agent_name = "Data Prep Agent"
            elif "interpreter" in agent_name.lower():
                agent_name = "Interpreter Agent"

            if item["tool_calls"]:
                tools_text = f" (called {len(item['tool_calls'])} tools)"
            else:
                tools_text = ""
            tree.add(f"🤖 {agent_name}{tools_text}")
        elif item["type"] == "tool_call":
            tool_name = item["tool_name"].replace("_", " ").title()
            # Show more detailed tool information
            if "transfer" in tool_name.lower():
                tree.add(f"🔄 {tool_name}")
            else:
                tree.add(f"🔧 {tool_name}: {item['content'][:50]}...")

    return tree


def format_tool_calls_table(result_data):
    """Create a detailed table of tool calls for verbose mode."""
    tools = extract_tool_calls(result_data)

    if not tools:
        return None

    table = Table(title="🔧 Tool Calls", show_header=True, header_style="bold cyan")
    table.add_column("Tool Name", style="yellow")
    table.add_column("Purpose", style="green")
    table.add_column("Arguments", style="dim")

    for tool in tools:
        tool_name = tool["name"].replace("_", " ").title()

        # Determine purpose based on tool name
        if "transfer_to_" in tool["name"]:
            target = tool["name"].replace("transfer_to_", "").replace("_", " ").title()
            purpose = f"Delegate to {target} Agent"
            args = "None"
        elif "transfer_back" in tool["name"]:
            purpose = "Return to Supervisor"
            args = "None"
        elif "sql" in tool["name"].lower():
            purpose = "Execute SQL Query"
            args = str(tool["args"]) if tool["args"] else "None"
        else:
            purpose = "Unknown"
            args = str(tool["args"]) if tool["args"] else "None"

        table.add_row(tool_name, purpose, args[:50] + "..." if len(args) > 50 else args)

    return table


def print_rich_results(result, verbose=False):
    """Print results using Rich formatting."""

    # Create main panel
    if result.success:
        title = "📊 [green]SUCCESS[/green]"
        border_style = "green"
    else:
        title = "📊 [red]FAILED[/red]"
        border_style = "red"

    # Extract AI response
    ai_response = extract_ai_response(result.data) if result.data else None

    # Build content
    content_parts = []

    if ai_response:
        content_parts.append(f"🤖 [bold cyan]AI Response:[/bold cyan]\n{ai_response}")
    elif result.data:
        content_parts.append(f"📝 [bold yellow]Response:[/bold yellow]\n{result.data}")

    if result.error:
        content_parts.append(f"❌ [bold red]Error:[/bold red]\n{result.error}")

    # Add agent collaboration for normal mode
    if result.data and not verbose:
        collaboration = format_agent_collaboration(result.data)
        if collaboration:
            content_parts.append(collaboration)

    # Show the main result panel
    content = "\n\n".join(content_parts)
    console.print(Panel(content, title=title, border_style=border_style))

    # Verbose mode extras
    if verbose and result.data:
        # Agent flow tree
        flow_tree = format_agent_flow_detailed(result.data)
        if flow_tree:
            console.print("\n")
            console.print(flow_tree)

        # Tool calls table
        tool_table = format_tool_calls_table(result.data)
        if tool_table:
            console.print("\n")
            console.print(tool_table)

        # Token usage table
        token_usage = get_token_usage(result.data)
        if token_usage:
            table = Table(
                title="📊 Token Usage", show_header=True, header_style="bold magenta"
            )
            table.add_column("Type", style="cyan")
            table.add_column("Count", justify="right", style="green")
            table.add_row("Input", str(token_usage["input"]))
            table.add_row("Output", str(token_usage["output"]))
            table.add_row("Total", str(token_usage["total"]), style="bold")
            console.print("\n")
            console.print(table)

        # Metadata
        if result.metadata:
            console.print(f"\n🔧 [bold]Metadata:[/bold] {result.metadata}")

        # Raw data (collapsible)
        if result.data:
            console.print(
                f"\n🔧 [bold]Raw Data:[/bold] [dim]{str(result.data)}...[/dim]"
            )


def print_clean_results(result, verbose=False):
    """Print results - wrapper for Rich formatting."""
    print_rich_results(result, verbose)


def trim_messages(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    """Trim messages to keep only the most recent ones."""
    if len(messages) <= max_messages:
        return messages

    # Keep the most recent messages
    return messages[-max_messages:]


def update_conversation_history(
    conversation_history: list[BaseMessage],
    user_message: str,
    ai_response: str,
    max_messages: int = 20,
) -> list[BaseMessage]:
    """Update conversation history with new messages and trim if needed."""
    # Add new messages
    conversation_history.append(HumanMessage(content=user_message))
    if ai_response:
        conversation_history.append(AIMessage(content=ai_response))

    # Trim if needed
    if len(conversation_history) > max_messages:
        conversation_history = trim_messages(conversation_history, max_messages)

    return conversation_history


async def process_query(
    supervisor: BaseAgent, query, session_id, conversation_history, verbose=False
):
    """Process a single user query with conversation context."""
    print(f"\n 🔄 ID #{session_id}")
    print(f"\n🔄 Processing: '{query}'")
    if len(conversation_history) > 0:
        print(f"💬 Context: {len(conversation_history)} previous messages")
    print("⏳ Working...")

    # Update config with new query
    supervisor.config["configurable"]["query"] = query

    try:
        result = await supervisor.execute()

        # Extract AI response for conversation history
        ai_response = extract_ai_response(result.data) if result.data else None

        # Update conversation history in place
        update_conversation_history(
            conversation_history,
            query,
            ai_response or "No response generated",
            max_messages=20,
        )

        print_clean_results(result, verbose=verbose)
        return result.success, ai_response

    except Exception as e:
        error_msg = f"Error during execution: {e}"
        print(f"\n❌ {error_msg}")

        # Still update conversation history with error
        update_conversation_history(
            conversation_history, query, error_msg, max_messages=20
        )

        if verbose:
            import traceback

            print(f"🔧 Full traceback:\n{traceback.format_exc()}")
        return False, None


async def main(verbose=False):
    """Main interactive CLI function."""
    print_banner()

    # Set up data manager
    print("🔧 Initializing data manager...")
    data_manager = DataManager(path="financial_data.db")

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    model = None

    if api_key:
        try:
            model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        except Exception as e:
            print(f"⚠️ Failed to initialize model: {e}")

    print_config(api_key, model, data_manager, verbose=verbose)

    # Create session ID
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Persistent conversation history for this session
    conversation_history: list[BaseMessage] = []

    # Create minimal global state template
    def create_global_state(query):
        return {
            "user_query": query,
            "session_id": session_id,
            "conversation_history": conversation_history,
            "max_messages": 20,  # Keep last 20 messages
            "enable_trimming": True,
            "interpreted_query": None,
            "todo_plan": [],
            "current_task": None,
            "dashboard_layout": {},
            "widget_specs": {},
            "widget_data_queries": {},
            "available_tables": [],
            "created_subtables": [],
            "data_descriptions": {},
            "errors": [],
            "warnings": [],
            "current_agent": None,
            "agent_history": [],
        }

    print("\n🚀 System ready! Type your queries below.")
    print("💡 Type 'exit', 'quit', or press Ctrl+C to stop.")
    print("🧠 Chat history: Enabled (max 20 messages, SQLite persistence)")
    print("=" * 60)

    query_count = 0

    while True:
        try:
            # Get user input
            user_query = input(
                f"\n[Query #{query_count + 1}] 💬 Enter your request: "
            ).strip()

            # Check for exit commands
            if user_query.lower() in ["q", "exit", "quit", "bye"]:
                print("\n👋 Goodbye! Thanks for using the Multi-Agent System!")
                break

            if not user_query:
                print("⚠️ Please enter a valid query.")
                continue

            # Create fresh global state for this query
            global_state = create_global_state(user_query)

            # Set up configuration
            config = RunnableConfig()
            config["configurable"] = {
                "model": model,
                "api_key": api_key,
                "query": user_query,
                "thread_id": "thread-1",
            }

            # Initialize supervisor for this query
            supervisor = Supervisor(
                name=f"supervisor_{query_count + 1}",
                global_state=global_state,
                data_manager=data_manager,
                config=config,
            )

            # Process the query
            success, ai_response = await process_query(
                supervisor,
                user_query,
                session_id,
                conversation_history,
                verbose=verbose,
            )
            query_count += 1

            if not success and not api_key:
                print(
                    "\n💡 Tip: Set OPENAI_API_KEY environment variable for full functionality."
                )

            print("\n" + "=" * 60)
            print(ai_response or "No response generated.")

        except KeyboardInterrupt:
            print("\n\n⛔ Interrupted by user. Shutting down...")
            break
        except EOFError:
            print("\n\n⛔ End of input detected. Shutting down...")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            print("🔄 Continuing... (type 'exit' to quit)")

    print("\n📊 Session Summary:")
    print(f"   • Queries processed: {query_count}")
    print(f"   • Session ID: {session_id}")
    print("   • Thank you for using the Multi-Agent System! 🎉")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Interactive CLI for the multi-agent supervisor system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Normal mode with clean output
  python main.py --verbose    # Debug mode with technical details
  python main.py -v           # Short version of verbose mode
        """,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose mode with debug information, token usage, and raw data",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = parse_args()
        asyncio.run(main(verbose=args.verbose))
    except KeyboardInterrupt:
        print("\n\n⛔ Program terminated by user.")
        sys.exit(0)
