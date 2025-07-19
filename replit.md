# AIVim Project Documentation

## Overview
AIVim is an advanced AI-powered Vim clone that revolutionizes code editing through intelligent, adaptive interactions and multi-provider AI assistance. It provides a next-generation coding environment that blends modal editing with AI-driven insights, transforming how developers interact with their code.

## Project Architecture

### Core Components
- **Editor (`aivim/editor.py`)**: Main editor class that coordinates all components
- **Buffer (`aivim/buffer.py`)**: Manages text content, cursor position, and history
- **Display (`aivim/display.py`)**: Handles terminal UI rendering
- **Command Handler (`aivim/command_handler.py`)**: Processes Vim-style commands
- **Key Handler (`aivim/key_handler.py`)**: Manages keyboard input across different modes
- **NLP Mode (`aivim/nlp_mode.py`)**: Natural Language Programming capabilities with live detection

### Key Features
- **Modal Editing**: NORMAL, INSERT, VISUAL, COMMAND, and NLP modes
- **Multi-tab Support**: Work with multiple files simultaneously
- **AI Integration**: Support for OpenAI, Anthropic, and other AI providers
- **Natural Language Programming**: Enhanced NLP Live Mode with intelligent detection

## Recent Changes (2025-01-19)

### Major Improvements to NLP Live Mode
Based on user feedback, the following enhancements were implemented:

1. **Integrated Smart Detection within Live Mode**:
   - Removed separate `:nlpsmart` command
   - Smart detection is now an integral part of live mode
   - Single `:nlplive` command toggles both features together
   - Clearer status messages showing when auto-detect is active

2. **Configurable Timeout and Force Submission**:
   - Added 30-second configurable timeout for AI calls
   - F9 key now forces immediate submission of queued NLP content
   - Timeout prevents UI freezing during network issues
   - Force submission bypasses debounce timing for urgent processing

3. **Enhanced AI Service Features**:
   - Added `refresh_available_models()` to fetch models from providers
   - OpenAI model list now dynamically retrieved from API
   - Debug logging capability with `enable_debug_logging()`
   - All AI calls logged to temporary file when debug enabled
   - Configurable timeout (default 30s) for all AI providers

4. **Technical Improvements**:
   - Timeout support added to OpenAI, Anthropic, and local LLM calls
   - Debug logs include system prompts, user prompts, responses, and timing
   - Better error handling with specific timeout messages
   - Maintains backward compatibility with existing features

### Previous Implementation (2025-01-09)

#### Enhanced NLP Live Mode Implementation
Implemented a revolutionary NLP Live Mode that provides:

1. **Intelligent NLP Detection**: 
   - Automatically differentiates between natural language and code
   - No need for explicit markers (though #nlp markers still work)
   - Smart pattern recognition for comments that look like instructions

2. **Real-time Processing**:
   - Asynchronous background processing as you type
   - Debounced updates to avoid excessive API calls
   - Visual indicators for regions being processed

3. **Context-aware Processing**:
   - Uses entire file content as context
   - Includes all open tabs for comprehensive understanding
   - Maintains code structure and style consistency

### User Preferences
- Live NLP detection enabled by default in NLP mode
- Smart detection integrated within live mode (not separate)
- Processing happens after 1 second of typing pause
- High-confidence regions (>60%) are processed automatically
- F9 key for force submission of NLP content
- 30-second timeout for AI calls
- Debug logging available on demand

## Testing
All existing tests continue to pass:
- `test_nlp_shift_enter.py` - Tests Shift+Enter functionality
- `test_nlptranslate_command.py` - Tests :nlptranslate command
- Full test suite validates backward compatibility

## Stack
- Python 3.11
- Curses-based terminal UI
- Threading for asynchronous operations
- OpenAI/Anthropic API integration
- Comprehensive test coverage with pytest

## Usage Tips
1. Enter NLP mode with `nl` in NORMAL mode
2. Type natural language instructions in comments or prose
3. The system automatically detects and processes NLP regions
4. Use `:nlplive` to toggle live detection
5. Use `:nlpsmart` to toggle intelligent detection
6. Traditional #nlp markers still work for explicit control