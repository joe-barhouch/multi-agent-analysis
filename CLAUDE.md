# Multi-Agent Supervisor System - Claude Documentation

## Project Overview
A multi-agent system for financial data analysis with supervisor coordination, query interpretation, and data preparation capabilities.

## Current Architecture
- **Supervisor Agent**: Coordinates all tasks and agents
- **Interpreter Agent**: Processes and interprets user queries
- **Data Prep Agent**: Handles data preparation tasks
- **Data Manager**: Manages Snowflake database operations

## Configuration
- **Model**: GPT-4.1-mini (OpenAI)
- **Database**: Snowflake (INVEST_NEXT_DEV/GENAI)
- **Framework**: LangChain + LangGraph
- **Environment**: Python with UV package manager

## Recent Changes
### 2025-07-27: Interactive CLI Implementation
- **Status**: ✅ Completed
- **Goal**: Transform single-execution script into interactive CLI with while loop
- **Features Added**:
  - [x] Interactive while loop for continuous operation
  - [x] Cool banner with emojis and timestamp
  - [x] Configuration display at startup showing API key status, model, database
  - [x] Real-time query processing with visual feedback
  - [x] Graceful exit handling (exit/quit/Ctrl+C)
  - [x] Session management with unique session IDs
  - [x] Query counter and session summary
  - [x] Error handling and recovery
  - [x] Fresh global state for each query

### 2025-07-27: Enhanced Output Formatting
- **Status**: ✅ Completed
- **Goal**: Add human-friendly output with verbose debug option
- **Features Added**:
  - [x] Command line argument parsing with `--verbose`/`-v` flag
  - [x] Smart AI response extraction from LangChain messages
  - [x] Clean, conversational output format (default mode)
  - [x] Verbose debug mode showing technical details
  - [x] Token usage tracking and display
  - [x] Enhanced error handling with optional stack traces
  - [x] Dual output modes: normal vs verbose

### 2025-07-27: Rich CLI Enhancement & Agent Coordination Visualization
- **Status**: ✅ Completed
- **Goal**: Beautiful CLI with agent handoff visualization using Rich library
- **Features Added**:
  - [x] Rich library integration for beautiful CLI formatting
  - [x] Color-coded success/failure panels with borders
  - [x] Agent coordination flow visualization (Normal mode)
  - [x] Detailed agent handoff tree structure (Verbose mode)
  - [x] Professional token usage tables
  - [x] Tool usage extraction and display
  - [x] Visual agent flow: `Supervisor → Data Prep → Supervisor`
  - [x] Enhanced error formatting with Rich styling
  - [x] Clear separation between user info and debug details

### 2025-07-27: Chat History & Conversational Flow Implementation
- **Status**: ✅ Completed
- **Goal**: Transform single-query system into conversational flow with persistent memory
- **Features Added**:
  - [x] Added `langgraph-checkpoint-sqlite>=2.0.0` dependency
  - [x] Updated `GlobalState` to include proper message history with `List[BaseMessage]`
  - [x] Created `MessagesState` type for LangGraph integration with `add_messages` annotation
  - [x] Replaced `InMemorySaver` with `SqliteSaver` for persistent storage (`chat_history.db`)
  - [x] Implemented message trimming (max 20 messages) to manage token limits
  - [x] Added conversation context display in CLI (`💬 Context: X previous messages`)
  - [x] Updated supervisor agent to pass conversation history to workflow
  - [x] Session-persistent conversation history within same CLI session
  - [x] Automatic conversation history management with error handling
  - [x] Enhanced CLI status display showing chat history configuration

### 2025-07-30: CLI Output Enhancement & Bug Fixes - Phase 1
- **Status**: ✅ Completed
- **Goal**: Fix CLI output formatting issues and improve tool call display
- **Features Fixed**:
  - [x] Removed debugger breakpoints from supervisor and runner
  - [x] Fixed missing tool arguments in Arguments/Query column
  - [x] Enhanced tool argument formatting for SQL queries, Python code, and transfers  
  - [x] Cleaned up Agent Flow section to show only clean agent transitions
  - [x] Created separate Rich panel for detailed tool calls information
  - [x] Improved tool result display with better truncation and formatting
  - [x] Enhanced transfer tool result messages
- **Technical Implementation**:
  - **Breakpoint Removal**: Removed `breakpoint()` calls from `supervisor/agent.py:167` and `runner.py:313`
  - **Argument Extraction**: Enhanced `_format_sql_query()`, `_format_args()`, and `_format_python_code()` methods
  - **Clean Agent Flow**: Simplified `format_agent_collaboration_summary()` to show only agent names
  - **Separate Tool Panel**: Added dedicated Rich panel for tool calls in verbose mode with cyan border
  - **Better Formatting**: Improved argument display for SQL queries, table schemas, and transfers

### 2025-07-30: CLI Output Enhancement - Phase 2 (Advanced)
- **Status**: ✅ Completed  
- **Goal**: Fix agent flow truncation and capture missing SQL tool calls from sub-agents
- **Issues Addressed**:
  - Agent Flow responses truncated at 60 characters
  - Missing SQL tool calls in Tool Calls Details panel (only transfer operations shown)
- **Features Implemented**:
  - [x] Enhanced Agent Flow content display with smart truncation (60→200 characters)
  - [x] Improved tool call extraction to capture nested workflow operations
  - [x] Added hierarchical tool call organization by agent workflow
  - [x] Enhanced LangGraph supervisor configuration for better tool tracking
  - [x] Added comprehensive debugging output for tool call analysis
  - [x] Implemented agent context tracking and tool call inference
- **Technical Implementation**:
  - **Agent Flow Enhancement**: `formatters.py` - Increased truncation limits and smart sentence-boundary breaking
  - **Tool Extraction Overhaul**: `runner.py:_extract_tool_calls()` - Enhanced to capture ToolMessages and infer agents
  - **LangGraph Configuration**: `supervisor/agent.py` - Enabled `add_handoff_messages=True` for detailed handoff tracking
  - **Hierarchical Display**: `formatters.py` - New `_add_tool_row_to_table()` method with agent-grouped organization
  - **Context Tracking**: Added agent context tracking through message sequences for better tool attribution
  - **Debug Infrastructure**: Added comprehensive message type analysis for troubleshooting tool call extraction

### 2025-07-30: CLI Output Enhancement - Phase 3 (Deep Tool Extraction)
- **Status**: ✅ Completed
- **Goal**: Extract nested SQL tool calls from sub-agent workflows and restructure UI panels
- **Root Cause Identified**: LangGraph ReAct agents encapsulate SQL tool calls within internal workflows - these don't propagate to supervisor message stream
- **Features Implemented**:
  - [x] Deep debugging infrastructure with comprehensive message analysis
  - [x] Enhanced checkpointer access to investigate sub-agent workflow states  
  - [x] Recursive message traversal through nested LangGraph checkpoints
  - [x] Experimental nested tool call extraction from checkpointer metadata
  - [x] Separate "Tool Details" panel for detailed agent responses (magenta border)
  - [x] Simplified Agent Flow showing only handoffs: `User → Agent: [Processing...] → Transfer`
  - [x] Enhanced debug output showing tool call arguments and content previews
- **Technical Implementation**:
  - **Deep Debug Infrastructure**: `runner.py` - Enhanced message analysis with tool call arguments and content previews
  - **Checkpointer Investigation**: `supervisor/agent.py` - Added checkpointer state analysis and storage inspection
  - **Nested Tool Extraction**: `runner.py:_extract_nested_tool_calls()` - Experimental method to traverse checkpointer storage
  - **UI Restructure**: `cli/manager.py` - New Tool Details panel (magenta) separate from Tool Calls Details (cyan)
  - **Simplified Agent Flow**: `formatters.py:format_agent_flow_tree()` - Clean handoff display without detailed responses
  - **Enhanced Tool Details**: `formatters.py:create_tool_details_panel()` - Structured display of agent thinking and results
- **Architecture Challenge**: LangGraph's `create_react_agent()` creates isolated workflows where SQL tool calls remain internal to sub-agents, requiring deeper inspection methods to extract complete tool call history

### 2025-07-27: Real-Time Streaming Implementation
- **Status**: 🚧 In Progress
- **Goal**: Add streaming responses for real-time agent output and better user experience
- **Implementation Plan**:
  - [ ] Create streaming infrastructure (`src/core/streaming.py`)
  - [ ] Add streaming state fields to `GlobalState` and `MessagesState`
  - [ ] Update supervisor agent to use `astream()` instead of `ainvoke()`
  - [ ] Enhance CLI with Rich live displays and progress visualization
  - [ ] Implement multiple stream modes: `messages`, `updates`, `values`, `debug`
  - [ ] Add real-time token counting and cost tracking during streaming
  - [ ] Create buffered streaming output with agent handoff indicators
  - [ ] Implement streaming error handling and graceful degradation
  - [ ] Add CLI progress bars and spinners for agent operations
  - [ ] Enable live conversation history updates during streaming
  - [ ] Support stream interruption and cancellation (Ctrl+C)
- **Technical Details**:
  - **Stream Modes**: LangGraph supports `values`, `updates`, `custom`, `messages`, `debug`
  - **Rich Integration**: `rich.live.Live` for real-time terminal updates
  - **Buffer Management**: Handle streaming chunks and format appropriately
  - **Fallback Strategy**: Gracefully degrade to non-streaming if errors occur

### Standard Test Query
- **Default Query**: `explore financial_data.db`
- **Usage**: Always use this as the standard test query for debugging and development
- **Purpose**: Tests database exploration capabilities and agent coordination

## Chat History Implementation Details

### Architecture
- **Storage**: SQLite database (`chat_history.db`) for persistent conversation checkpoints
- **Memory Management**: In-session conversation history with automatic trimming
- **Message Format**: LangChain `BaseMessage` types (`HumanMessage`, `AIMessage`)
- **Context Window**: Maximum 20 messages per conversation thread
- **State Integration**: Conversation history embedded in `GlobalState` and passed to agents

### Key Components
- `SqliteSaver.from_conn_string("chat_history.db")`: Persistent checkpointer
- `MessagesState` with `add_messages` annotation for LangGraph compatibility  
- `trim_messages()` and `update_conversation_history()` functions for memory management
- Enhanced `process_query()` to maintain conversation context across queries
- Modified supervisor agent to include conversation history in workflow execution

### Benefits
- ✅ Conversational continuity within CLI sessions
- ✅ Token-efficient memory management with automatic trimming
- ✅ Persistent storage survives application restarts
- ✅ Context-aware agent responses
- ✅ Visual feedback showing conversation context size

## Environment Variables Required
- `OPENAI_API_KEY`: Required for agent operations

## Usage
```bash
# Normal mode with clean, human-friendly output
python main.py
uv run main.py

# Verbose mode with debug information and technical details
python main.py --verbose
uv run main.py --verbose
uv run main.py -v

# Help
python main.py --help
```

### Output Modes
- **Normal Mode**: Clean AI responses, easy to read
- **Verbose Mode**: Technical details, token usage, raw data, debug info

## File Structure
```
src/
├── agents/          # Agent implementations
├── core/           # Base classes and models
└── graph/          # Graph workflow definitions
```

## Notes
- System handles missing API keys gracefully with warnings
- Uses financial dataset (finance_economics_dataset.csv)
- Async/await pattern for agent execution
