# Multi-Agent Supervisor System - Streamlit App

A web-based chat interface for the Multi-Agent Financial Analysis System, providing the same functionality as the CLI in an intuitive browser-based interface.

## Features

### 🎯 Core Functionality
- **Interactive Chat Interface**: Natural language queries with real-time responses
- **Multi-Agent Coordination**: Visual display of agent collaboration flow
- **Tool Call Tracking**: Detailed table showing all tool calls and their results
- **Execution Statistics**: Real-time metrics and performance data
- **Session Management**: Persistent chat history and session controls

### 🔧 Advanced Features
- **Tool Details Panel**: Separate panel showing detailed agent responses with thinking process
- **Agent Flow Visualization**: Clean display of agent handoffs and transfers
- **SQL Query Display**: Formatted display of database queries and results
- **Error Handling**: Comprehensive error display and debugging information
- **Responsive Design**: Works on desktop and mobile devices

### 📊 Display Components
1. **Main Chat Interface**: Primary conversation area with user and AI messages
2. **Agent Collaboration**: Shows the flow of agents involved in processing
3. **Tool Details**: Expandable section with detailed agent thinking and results
4. **Tool Calls Table**: Comprehensive table of all tool calls with arguments and results
5. **Execution Statistics**: Performance metrics and token usage information

## Installation & Setup

### Prerequisites
- Python 3.8+
- All main project dependencies installed
- OpenAI API key (for agent operations)
- Snowflake database access (INVEST_NEXT_DEV/GENAI)

### Installation

1. **Install Streamlit dependencies:**
   ```bash
   cd streamlit_app
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Access the app:**
   Open your browser to `http://localhost:8501`

## Usage

### Basic Usage
1. **Configure System**: Enter your OpenAI API key in the sidebar
2. **Start Chatting**: Type your financial data analysis questions in the chat input
3. **Explore Results**: Expand the various sections to see detailed execution information
4. **Session Management**: Use sidebar controls to clear history or reset session

### Example Queries
- "Show me the schema of the database"
- "What are the top 3 stocks by average monthly GDP growth?"
- "Analyze the correlation between interest rates and stock performance"
- "Create a summary of trading volume trends"

### Advanced Features
- **Agent Flow**: See which agents processed your request and in what order
- **Tool Details**: View the detailed thinking process of each agent
- **SQL Queries**: See the actual database queries executed
- **Token Usage**: Monitor API usage and costs
- **Error Debugging**: Detailed error information for troubleshooting

## Interface Components

### Sidebar Configuration
- **🔑 API Key**: Enter your OpenAI API key
- **📊 Database Path**: Configure database location
- **📈 Session Stats**: View query count and message history
- **🛠️ Controls**: Clear chat, reset session

### Main Interface
- **💬 Chat Messages**: User queries and AI responses
- **🔄 Agent Collaboration**: Visual flow of agent handoffs
- **🔧 Tool Details**: Detailed agent responses with thinking process
- **📋 Tool Calls**: Table of all tool executions
- **📊 Statistics**: Performance and usage metrics

### Expandable Sections
Each query result includes expandable sections for:
- Agent collaboration flow
- Tool details with thinking process
- Tool calls table with arguments and results
- Execution statistics and metrics

## Architecture

### Components
- **`app.py`**: Main Streamlit application with chat interface
- **`formatters.py`**: Streamlit-specific result formatters
- **`requirements.txt`**: Streamlit-specific dependencies

### Integration
- Uses existing `AgentRunner` from the CLI system
- Integrates with all existing agents (Supervisor, Data Prep, Interpreter)
- Maintains the same multi-agent workflow as CLI
- Provides enhanced visual feedback and organization

### Session Management
- **Session State**: Maintains chat history and context
- **Query Context**: Preserves conversation history for agents
- **Error Handling**: Graceful error display and recovery
- **Performance**: Async query processing for responsiveness

## Comparison with CLI

| Feature | CLI | Streamlit App |
|---------|-----|---------------|
| **Interface** | Terminal-based | Web browser |
| **Chat History** | Session-only | Persistent with UI |
| **Tool Details** | Rich panels | Expandable sections |
| **Agent Flow** | Tree structure | Visual flow diagram |
| **Tool Calls** | Table format | Interactive DataFrame |
| **Configuration** | Command line args | Sidebar controls |
| **Error Display** | Text-based | Rich error formatting |
| **Accessibility** | Terminal required | Any web browser |

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure you're in the correct directory and have all dependencies
2. **API Key Issues**: Verify your OpenAI API key is correctly set
3. **Database Errors**: Check that Snowflake connection is properly configured with credentials
4. **Port Conflicts**: Use `streamlit run app.py --server.port 8502` for different port

### Debug Mode
The app includes comprehensive debugging information:
- Detailed error messages in the UI
- Session state information in sidebar
- Debug output in Streamlit console
- Tool call extraction debugging

## Development

### Adding New Features
1. **New Formatters**: Add methods to `StreamlitFormatter` class
2. **UI Components**: Extend the main app class with new display methods
3. **Agent Integration**: Modify the query processing workflow
4. **Styling**: Update CSS in the main app file

### Testing
- Test with various query types
- Verify all agent workflows function correctly  
- Check responsive design on different screen sizes
- Validate error handling and edge cases

## Support

For issues or questions:
1. Check the main project documentation
2. Review Streamlit logs for error details
3. Ensure all dependencies are correctly installed
4. Verify API key and database configuration