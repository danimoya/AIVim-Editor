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

## Recent Changes (2025-01-09)

### Enhanced NLP Live Mode Implementation
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

4. **New Commands**:
   - `:nlplive` - Toggle live NLP detection on/off
   - `:nlpsmart` - Toggle intelligent detection on/off

### Technical Implementation Details
- Added `_start_live_detection()` and `_stop_live_detection()` for background thread management
- Implemented `_detect_nlp_regions_smart()` for intelligent language detection
- Created `_is_natural_language_line()` with confidence scoring
- Added queue-based processing with `_process_queued_regions()`
- Maintains backward compatibility with existing NLP features

### User Preferences
- Live NLP detection enabled by default in NLP mode
- Smart detection identifies natural language patterns automatically
- Processing happens after 1 second of typing pause
- High-confidence regions (>60%) are processed automatically

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