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
    cli = CLIManager(verbose=verbose)
    data_manager = create_snowflake_manager()
    data_manager.get_sql_database()

    runner = AgentRunner(api_key=OPENAI_API_KEY, data_manager=data_manager)

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

    session = runner.create_session()

    def create_supervisor(name, global_state, config):
        supervisor = Supervisor(
            name=name,
            global_state=global_state,
            data_manager=data_manager,
            config=config,
        )
        supervisor.draw_graph()

        return supervisor

    while True:
        try:
            user_query = cli.get_user_input(session.query_count)

            if user_query is None:
                cli.print_goodbye()
                break

            if not user_query:
                continue

            cli.print_processing(user_query, session)
            result = await runner.execute_query(user_query, session, create_supervisor)

            cli.print_results(result)

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
