"""CLI Manager for handling all presentation and user interaction."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from src.cli.formatters import ResultFormatter
from src.core.runner import ExecutionResult, SessionContext


class CLIManager:
    """Manages CLI presentation and user interaction."""

    def __init__(self, verbose: bool = False):
        """Initialize the CLI manager.

        Args:
            verbose: Enable verbose output mode
        """
        self.verbose = verbose
        self.console = Console()
        self.formatter = ResultFormatter()

    def print_banner(self) -> None:
        """Print the application banner."""
        print("\n" + "=" * 60)
        print("🤖 MULTI-AGENT SUPERVISOR SYSTEM 🤖")
        print("=" * 60)
        print("Interactive Financial Data Analysis CLI")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def print_configuration(
        self, has_api_key: bool, has_model: bool, db_path: str
    ) -> None:
        """Display current configuration."""
        print("\n📋 CONFIGURATION:")
        print("-" * 30)
        print(f"API Key: {'✅ Set' if has_api_key else '❌ Not Set'}")
        print(f"Model: {'gpt-5-mini' if has_model else '❌ Unavailable'}")
        print(f"Database: {db_path}")
        print(f"Status: {'🟢 Ready' if has_api_key else '🟡 Limited Mode'}")
        if self.verbose:
            print("Verbose Mode: ✅ Enabled")
        print("-" * 30)

    def print_ready_message(self) -> None:
        """Print the ready message."""
        print("\n🚀 System ready! Type your queries below.")
        print("💡 Type 'exit', 'quit', or press Ctrl+C to stop.")
        print("🧠 Chat history: Enabled (max 20 messages)")
        print("=" * 60)

    def get_user_input(self, query_count: int) -> Optional[str]:
        """Get user input with proper prompt.

        Returns:
            User input or None if exit requested
        """
        user_input = input(
            f"\n[Query #{query_count + 1}] 💬 Enter your request: "
        ).strip()

        if user_input.lower() in ["q", "exit", "quit", "bye"]:
            return None

        if not user_input:
            print("⚠️ Please enter a valid query.")
            return ""

        return user_input

    def print_processing(self, query: str, session: SessionContext) -> None:
        """Print processing message."""
        print(f"\n 🔄 ID #{session.session_id}")
        print(f"\n🔄 Processing: '{query}'")
        if len(session.conversation_history) > 0:
            print(f"💬 Context: {len(session.conversation_history)} previous messages")
        print("⏳ Working...")

    def print_results(self, result: ExecutionResult) -> None:
        """Print execution results."""
        if self.verbose:
            self._print_verbose_results(result)
        else:
            self._print_normal_results(result)

    def _print_normal_results(self, result: ExecutionResult) -> None:
        """Print results in normal mode."""
        # Create main panel
        if result.success:
            title = "📊 [green]SUCCESS[/green]"
            border_style = "green"
        else:
            title = "📊 [red]FAILED[/red]"
            border_style = "red"

        # Build content
        content_parts = []

        if result.ai_response:
            content_parts.append(
                f"🤖 [bold cyan]AI Response:[/bold cyan]\n{result.ai_response}"
            )
        elif result.error:
            content_parts.append(f"❌ [bold red]Error:[/bold red]\n{result.error}")

        # Add agent collaboration summary
        if result.agent_flow:
            collaboration = self.formatter.format_agent_collaboration_summary(result)
            if collaboration:
                content_parts.append(collaboration)

        content = "\n\n".join(content_parts)
        self.console.print(Panel(content, title=title, border_style=border_style))

    def _print_verbose_results(self, result: ExecutionResult) -> None:
        """Print results in verbose mode."""
        # First print normal results
        self._print_normal_results(result)

        # Tool Details Panel (NEW: detailed agent responses)
        tool_details = self.formatter.create_tool_details_panel(result)
        if tool_details and tool_details != "No detailed responses available.":
            self.console.print("\n")
            tool_details_panel = Panel(
                tool_details,
                title="🔧 [bold magenta]Tool Details[/bold magenta]",
                border_style="magenta",
                padding=(1, 1),
            )
            self.console.print(tool_details_panel)

        # Tool Calls Panel (separate panel for better organization)
        if result.tool_calls:
            tool_table = self.formatter.format_tool_calls_table(result.tool_calls)
            if tool_table:
                self.console.print("\n")
                tool_panel = Panel(
                    tool_table,
                    title="🔧 [bold cyan]Tool Calls Details[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 1),
                )
                self.console.print(tool_panel)

        # Simplified Agent Flow (handoffs only)
        if result.agent_flow:
            flow_tree = self.formatter.format_agent_flow_tree(result)
            if flow_tree:
                self.console.print("\n")
                self.console.print(flow_tree)

        if result.token_usage:
            token_table = self.formatter.format_token_usage_table(result.token_usage)
            self.console.print("\n")
            self.console.print(token_table)

        # Execution statistics
        stats_table = self.formatter.format_execution_stats(result)
        self.console.print("\n")
        self.console.print(stats_table)

        # Raw data preview
        if result.raw_data and self.verbose:
            self.console.print(
                f"\n🔧 [bold]Raw Data:[/bold] [dim]{str(result.raw_data)[:200]}...[/dim]"
            )

    def print_goodbye(self) -> None:
        """Print goodbye message."""
        print("\n👋 Goodbye! Thanks for using the Multi-Agent System!")

    def print_session_summary(self, session: SessionContext) -> None:
        """Print session summary."""
        print("\n📊 Session Summary:")
        print(f"   • Queries processed: {session.query_count}")
        print(f"   • Session ID: {session.session_id}")
        print("   • Thank you for using the Multi-Agent System! 🎉")

    def print_error(self, error: str, show_traceback: bool = False) -> None:
        """Print error message."""
        print(f"\n❌ {error}")
        if show_traceback and self.verbose:
            import traceback

            print(f"🔧 Full traceback:\n{traceback.format_exc()}")

    def print_tip(self, tip: str) -> None:
        """Print a helpful tip."""
        print(f"\n💡 Tip: {tip}")

    def print_separator(self) -> None:
        """Print a separator line."""
        print("\n" + "=" * 60)
