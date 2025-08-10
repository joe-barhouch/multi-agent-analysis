"""Main entry point for the multi-agent supervisor system."""

import argparse
import asyncio
import sys

from src.agents.database_manager import create_snowflake_manager
from src.agents.supervisor.agent import Supervisor
from src.cli.manager import CLIManager
from src.config import OPENAI_API_KEY
from src.core.runner import AgentRunner


async def main(verbose: bool = False) -> None:
    """Main application entry point.

    Args:
        verbose: Enable verbose output mode
    """
    # Initialize components
    cli = CLIManager(verbose=verbose)
    # Use Snowflake connection instead of SQLite
    data_manager = create_snowflake_manager()

    # Get API key and initialize runner
    runner = AgentRunner(api_key=OPENAI_API_KEY)

    # Display startup information
    cli.print_banner()
    db_info = (
        f"Snowflake: {data_manager.config['database']}/{data_manager.config['schema']}"
    )
    cli.print_configuration(
        has_api_key=bool(OPENAI_API_KEY),
        has_model=bool(runner.model),
        db_path=db_info,
    )
    cli.print_ready_message()

    # Create session
    session = runner.create_session()

    # Create supervisor factory
    def create_supervisor(name, global_state, config):
        supervisor = Supervisor(
            name=name,
            state=global_state,
            data_manager=data_manager,
            config=config,
        )
        supervisor.draw_graph()

        return supervisor

    # Main interaction loop
    while True:
        try:
            # Get user input
            user_query = cli.get_user_input(session.query_count)

            # Check for exit
            if user_query is None:
                cli.print_goodbye()
                break

            # Skip empty queries
            if not user_query:
                continue

            # Process the query
            cli.print_processing(user_query, session)
            result = await runner.execute_query(user_query, session, create_supervisor)

            # Display results
            cli.print_results(result)

            # Show tips if needed
            if not result.success and not OPENAI_API_KEY:
                cli.print_tip(
                    "Set OPENAI_API_KEY environment variable for full functionality."
                )

            cli.print_separator()

        except KeyboardInterrupt:
            print("\n\n⛔ Interrupted by user. Shutting down...")
            break
        except EOFError:
            print("\n\n⛔ End of input detected. Shutting down...")
            break
        except Exception as e:
            cli.print_error(f"Unexpected error: {e}", show_traceback=True)
            print("🔄 Continuing... (type 'exit' to quit)")

    # Print session summary
    cli.print_session_summary(session)


def parse_arguments() -> argparse.Namespace:
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
        args = parse_arguments()
        asyncio.run(main(verbose=args.verbose))
    except KeyboardInterrupt:
        print("\n\n⛔ Program terminated by user.")
        sys.exit(0)
