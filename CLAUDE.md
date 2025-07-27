# Multi-Agent Supervisor System - Claude Documentation

## Project Overview
A multi-agent system for financial data analysis with supervisor coordination, query interpretation, and data preparation capabilities.

## Current Architecture
- **Supervisor Agent**: Coordinates all tasks and agents
- **Interpreter Agent**: Processes and interprets user queries
- **Data Prep Agent**: Handles data preparation tasks
- **Data Manager**: Manages SQLite database operations

## Configuration
- **Model**: GPT-4o-mini (OpenAI)
- **Database**: SQLite (financial_data.db)
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

### 2025-07-27: Real-Time Streaming Implementation
- **Status**: 🚧 In Progress
- **Goal**: Add streaming responses for real-time agent output and better user experience
- **Features Planned**:
  - [ ] Streaming response support using LangChain's streaming capabilities
  - [ ] Real-time agent progress visualization with Rich live updates
  - [ ] Live token counting and cost tracking during streaming
  - [ ] Buffered streaming output with agent handoff indicators
  - [ ] Streaming error handling and graceful degradation
  - [ ] CLI progress bars and spinners for agent operations
  - [ ] Live conversation history updates during streaming
  - [ ] Stream interruption and cancellation support

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