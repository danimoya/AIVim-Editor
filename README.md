# AIVim - AI-Enhanced Text Editor

AIVim is an AI-enhanced version of Vim built in Python, offering intelligent code assistance and generation capabilities while maintaining the core modal editing experience. Combining the power of different AI models with familiar Vim interactions, AIVim helps developers understand, improve, and generate code more efficiently.

## Features

### Modal Editing
- **Normal Mode**: Navigate and edit text using Vim-style commands
- **Insert Mode**: Type and modify text directly
- **Visual Mode**: Select text for operations 
- **Command Mode**: Enter commands with the `:` prefix

### AI-Powered Assistance
- **Code Explanation**: Understand complex code with detailed explanations
- **Code Improvement**: Get AI-powered refactoring and optimization suggestions with diff-style presentation
- **Code Generation**: Generate new code based on natural language descriptions
- **Custom AI Queries**: Ask questions about your code and receive contextual answers
- **Interactive Chat**: Have multi-turn conversations with AI about your code
- **Code Analysis**: Get complexity analysis and bug detection for your code
- **Multi-Tab Interface**: View and compare original and AI-improved code in tabs
- **Version History**: Automatic tracking of file changes with metadata
- **File Backups**: Automatic backup creation when applying improvements (with timestamps)
- **Multi-Provider Support**: Choose between OpenAI, Anthropic Claude, or local LLM models
- **Loading Indicators**: Visual feedback when AI operations are in progress

### Advanced UI Features
- **Multi-Tab System**: Seamlessly switch between different files and AI suggestions
- **Tab Navigation**: Use `:nexttab` (or alias `:n`) and `:prevtab` (or alias `:N`) to navigate tabs
- **Tab Management**: Create new tabs with `:tabnew` or `:tabnew filename`, close with `:tabclose`
- **Status Line**: Displays current mode, filename, cursor position, and tab information
- **Animated Loading**: Visual indicators during AI operations to show progress
- **Syntax Highlighting**: Basic syntax highlighting for improved code readability
- **Line Numbers**: Display line numbers for easier navigation and reference
## AI Commands

AIVim provides the following AI-specific commands:

| Command | Description |
|---------|-------------|
| `:explain <start> <end>` | Get an explanation of lines `start` through `end` |
| `:improve <start> <end>` | Get improvement suggestions for lines `start` through `end` |
| `:generate <line> <description>` | Generate code at `line` based on the `description` |
| `:analyze <start> <end>` | Analyze code complexity and detect bugs in lines `start` through `end` |
| `:ai <query>` | Ask a custom question about the current file |
| `:set model=<provider>` | Set the AI model provider (openai, claude, local) |
| `:chat` | Start an interactive chat with the AI about your code |

## Tab Navigation Commands

| Command | Description |
|---------|-------------|
| `:nexttab` or `:n` | Switch to the next tab |
| `:prevtab` or `:N` | Switch to the previous tab |
| `:tabnew` | Create a new empty tab |
| `:tabnew <filename>` | Create a new tab and open the specified file |
| `:tabclose` | Close the current tab |

## Usage

### Basic Editing
- Press `i` to enter insert mode, `ESC` to return to normal mode
- Use `:w` to save, `:q` to quit, `:wq` to save and quit
- Navigation works with arrow keys (primary) or `h`, `j`, `k`, `l` keys (alternative)

### AI Features
1. Navigate to the code you want to work with
2. In normal mode, type `:explain 10 20` to explain lines 10-20
3. Use `:improve 10 20` to get improvement suggestions:
   - A new tab opens showing a colorized diff view of proposed changes
   - Review the modifications in the diff view
   - To apply the changes, switch back to the original tab and confirm
   - A backup of the original file is automatically created with a timestamp
4. Generate code with `:generate 5 "Create a function that calculates factorial"`
5. Analyze code with `:analyze 10 20` to identify complexity issues and potential bugs
6. Ask questions with `:ai How does this algorithm work?`
7. Start an interactive chat with `:chat` and have a multi-turn conversation about your code
8. Switch between AI providers with `:set model=openai`, `:set model=claude`, or `:set model=local`

## Installation

To install AIVim:

```bash
# Install from source
git clone https://github.com/yourusername/aivim.git
cd aivim
pip install -e .

# Run AIVim
python -m aivim.run_editor file.py
```

## Setting Up Local LLM Support

AIVim supports using local LLM models via llama-cpp-python:

```bash
# Install the local LLM package
pip install llama-cpp-python

# Download a small model using the provided script
python download_local_model.py --model tinyllama

# Or list available models
python download_local_model.py --list

# Once downloaded, you can use it by setting the model:
# Inside AIVim: :set model=local
```

The download_local_model.py script supports several small models suitable for local execution:

| Model | Size | Description |
|-------|------|-------------|
| tinyllama | ~1GB | Small but capable model for code assistance |
| phi2 | ~1.7GB | Microsoft compact yet powerful model |
| stablelm | ~1.5GB | Stability AI efficient language model |

## Web Interface

AIVim also includes a web interface for easy access:

```bash
# Start the web server
python main.py

# Access AIVim in your browser at:
# http://localhost:5000
```

## Embedding AIVim

AIVim can be embedded into other Python applications:

```python
from aivim import embed_editor

# Open a file in the embedded editor
embed_editor("path/to/file.py")

# Or create a new file
embed_editor()
```

## Requirements

- Python 3.8 or higher
- OpenAI API key (set as OPENAI_API_KEY environment variable)
- Optional: Anthropic API key (set as ANTHROPIC_API_KEY environment variable)
- Optional: Local LLM model (set model path as LLAMA_MODEL_PATH environment variable)
- curses library (included with Python on most systems)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
