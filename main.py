"""Main entry point for the multi-agent supervisor system."""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from src.agents.data_manager import DataManager
from src.agents.supervisor.agent import Supervisor
from src.cli.manager import CLIManager
from src.core.runner import AgentRunner

# Load environment variables
load_dotenv()


async def main(verbose: bool = False) -> None:
    """Main application entry point.

    Args:
        verbose: Enable verbose output mode
    """
    # Initialize components
    cli = CLIManager(verbose=verbose)
    data_manager = DataManager(path="financial_data.db")

    # Get API key and initialize runner
    api_key = os.getenv("OPENAI_API_KEY")
    runner = AgentRunner(api_key=api_key)

    # Display startup information
    cli.print_banner()
    cli.print_configuration(
        has_api_key=bool(api_key),
        has_model=bool(runner.model),
        db_path=data_manager.path,
    )
    cli.print_ready_message()

    # Create session
    session = runner.create_session()

    # Create supervisor factory
    def create_supervisor(name, global_state, config):
        supervisor = Supervisor(
            name=name,
            global_state=global_state,
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
            if not result.success and not api_key:
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
