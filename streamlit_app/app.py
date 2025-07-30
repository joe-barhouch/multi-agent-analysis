"""
Streamlit Multi-Agent Supervisor System
A web-based chat interface for financial data analysis with multi-agent coordination.
"""

import asyncio
import os
import sys
from datetime import datetime

import streamlit as st

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from st_cb_handler import get_streamlit_cb

from src.agents.data_manager import DataManager
from src.agents.supervisor.agent import Supervisor
from src.core.runner import AgentRunner
from streamlit_app.formatters import StreamlitFormatter

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Financial Analysis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        background-color: #f8f9fa;
    }
    
    .user-message {
        border-left-color: #28a745;
        background-color: #e8f5e9;
    }
    
    .agent-message {
        border-left-color: #1f77b4;
        background-color: #e3f2fd;
    }
    
    .error-message {
        border-left-color: #dc3545;
        background-color: #ffebee;
    }
    
    .success-badge {
        background-color: #28a745;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
    
    .failed-badge {
        background-color: #dc3545;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
    
    .metric-box {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


class StreamlitApp:
    """Main Streamlit application class."""

    def __init__(self):
        self.initialize_session_state()
        self.formatter = StreamlitFormatter()

    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "session_context" not in st.session_state:
            st.session_state.session_context = None

        if "agent_runner" not in st.session_state:
            st.session_state.agent_runner = None

        if "data_manager" not in st.session_state:
            st.session_state.data_manager = None

        if "query_count" not in st.session_state:
            st.session_state.query_count = 0

        if "global_state" not in st.session_state:
            st.session_state.global_state = None

    def setup_sidebar(self):
        """Setup the sidebar with configuration and controls."""
        st.sidebar.markdown("# 🤖 Multi-Agent System")
        st.sidebar.markdown("---")

        # API Key Configuration
        st.sidebar.markdown("### 🔑 Configuration")
        api_key = st.sidebar.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Enter your OpenAI API key for agent operations",
        )

        # Database Configuration
        db_path = st.sidebar.text_input(
            "Database Path",
            value="financial_data.db",
            help="Path to the SQLite database",
        )

        # System Status
        st.sidebar.markdown("### 📊 System Status")

        # Initialize components if not already done
        if not st.session_state.agent_runner or not st.session_state.data_manager:
            try:
                st.session_state.data_manager = DataManager(path=db_path)
                st.session_state.agent_runner = AgentRunner(api_key=api_key)

                if not st.session_state.session_context:
                    st.session_state.session_context = (
                        st.session_state.agent_runner.create_session()
                    )

                st.sidebar.success("✅ System Initialized")
                st.sidebar.info(
                    f"📅 Session: {st.session_state.session_context.session_id}"
                )

            except Exception as e:
                st.sidebar.error(f"❌ Initialization Error: {str(e)}")
                return False

        # Display status
        col1, col2 = st.sidebar.columns(2)

        with col1:
            if api_key:
                st.markdown(
                    '<div class="success-badge">API Key ✅</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="failed-badge">API Key ❌</div>', unsafe_allow_html=True
                )

        with col2:
            if os.path.exists(db_path):
                st.markdown(
                    '<div class="success-badge">Database ✅</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="failed-badge">Database ❌</div>',
                    unsafe_allow_html=True,
                )

        # Session Statistics
        st.sidebar.markdown("### 📈 Session Stats")
        st.sidebar.metric("Queries Processed", st.session_state.query_count)
        st.sidebar.metric("Messages", len(st.session_state.messages))

        # Controls
        st.sidebar.markdown("### 🛠️ Controls")
        # TODO: this should clear history only, not reset the session
        if st.sidebar.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.session_state.query_count = 0
            st.rerun()

        if st.sidebar.button("🔄 Reset Session"):
            st.session_state.session_context = (
                st.session_state.agent_runner.create_session()
            )
            st.session_state.messages = []
            st.session_state.query_count = 0
            st.rerun()

        return True

    def display_chat_history(self):
        """Display the chat message history."""
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f"**You:** {message['content']}")

            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown("**🤖 AI Assistant:**")

                    # Display AI response
                    if message.get("ai_response"):
                        st.markdown(message["ai_response"])

                    # Display execution results in expandable sections
                    if message.get("execution_result"):
                        result = message["execution_result"]

                        # Agent Collaboration
                        if result.agent_flow:
                            with st.expander("🔄 Agent Collaboration", expanded=False):
                                self.formatter.display_agent_collaboration(result)

                        # Tool Details
                        if result.agent_flow:
                            with st.expander("🔧 Tool Details", expanded=False):
                                self.formatter.display_tool_details(result)

                        # Tool Calls Table
                        if result.tool_calls:
                            with st.expander("📋 Tool Calls Details", expanded=False):
                                self.formatter.display_tool_calls_table(
                                    result.tool_calls
                                )

                        # Global State Display
                        if result.final_global_state:
                            with st.expander("🔍 Global State", expanded=False):
                                self.formatter.display_global_state(
                                    result.final_global_state
                                )

                        # Execution Statistics
                        with st.expander("📊 Execution Statistics", expanded=False):
                            self.formatter.display_execution_stats(result)

            elif message["role"] == "error":
                with st.chat_message("assistant"):
                    st.error(f"❌ **Error:** {message['content']}")

    async def process_query_async(self, query: str, cb=None):
        """Process query asynchronously."""
        try:
            # Create supervisor factory
            def create_supervisor(name, global_state, config):
                """Factory function to create a Supervisor agent."""
                # Add cb to config if provided
                if cb:
                    config = config or {}
                    config["callbacks"] = [cb]

                supervisor = Supervisor(
                    name=name,
                    global_state=global_state,
                    data_manager=st.session_state.data_manager,
                    config=config,
                    streaming=False,
                )
                return supervisor

            # Execute query
            result = await st.session_state.agent_runner.execute_query(
                query, st.session_state.session_context, create_supervisor
            )

            return result

        except Exception as e:
            raise e

    def process_user_input(self, user_input: str):
        """Process user input and generate response."""
        # Add user message to chat
        st.session_state.messages.append(
            {"role": "user", "content": user_input, "timestamp": datetime.now()}
        )

        # Show processing message
        with st.chat_message("assistant"):
            with st.spinner("🤖 Processing your request..."):
                try:
                    # ST Callback Handler
                    st_cb = get_streamlit_cb(st.container())
                    # Run async query processing
                    result = asyncio.run(self.process_query_async(user_input, st_cb))

                    # Extract AI response
                    ai_response = (
                        result.ai_response
                        if result.ai_response
                        else "Query processed successfully."
                    )

                    # Add assistant response to chat
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": ai_response,
                            "ai_response": ai_response,
                            "execution_result": result,
                            "timestamp": datetime.now(),
                        }
                    )

                    # Update query count
                    st.session_state.query_count += 1

                    # Display results immediately
                    st.markdown("**🤖 AI Assistant:**")
                    st.markdown(ai_response)

                    # Update global state in session
                    if result.final_global_state:
                        st.session_state.global_state = result.final_global_state

                    # Display execution results
                    if result.agent_flow:
                        with st.expander("🔄 Agent Collaboration", expanded=True):
                            self.formatter.display_agent_collaboration(result)

                    if result.agent_flow:
                        with st.expander("🔧 Tool Details", expanded=False):
                            self.formatter.display_tool_details(result)

                    if result.tool_calls:
                        with st.expander("📋 Tool Calls Details", expanded=False):
                            self.formatter.display_tool_calls_table(result.tool_calls)

                    # Display global state
                    if result.final_global_state:
                        with st.expander("🔍 Global State", expanded=False):
                            self.formatter.display_global_state(
                                result.final_global_state
                            )

                    with st.expander("📊 Execution Statistics", expanded=False):
                        self.formatter.display_execution_stats(result)

                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.error(error_msg)

                    # Add error message to chat
                    st.session_state.messages.append(
                        {
                            "role": "error",
                            "content": error_msg,
                            "timestamp": datetime.now(),
                        }
                    )

    def run(self):
        """Main application entry point."""
        # Header
        st.markdown(
            '<h1 class="main-header">🤖 Multi-Agent Financial Analysis System</h1>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Setup sidebar
        if not self.setup_sidebar():
            st.error("Please configure the system using the sidebar before proceeding.")
            return

        # Main chat interface
        st.markdown("### 💬 Chat with the Multi-Agent System")

        # Display chat history
        self.display_chat_history()

        # Chat input
        if prompt := st.chat_input("Ask me anything about financial data analysis..."):
            self.process_user_input(prompt)
            st.rerun()


def main():
    """Main function to run the Streamlit app."""
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()
