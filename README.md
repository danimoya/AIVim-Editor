# AIVim - AI-Enhanced Text Editor

AIVim is an AI-enhanced version of Vim built in Python, offering intelligent code assistance and generation capabilities while maintaining the core modal editing experience.

## Features

### Modal Editing
- **Normal Mode**: Navigate and edit text using Vim-style commands
- **Insert Mode**: Type and modify text directly
- **Visual Mode**: Select text for operations
- **Command Mode**: Enter commands with the `:` prefix

### AI-Powered Assistance
- **Code Explanation**: Understand complex code with detailed explanations
- **Code Improvement**: Get AI-powered refactoring and optimization suggestions
- **Code Generation**: Generate new code based on natural language descriptions
- **Custom AI Queries**: Ask questions about your code and receive contextual answers

## AI Commands

AIVim provides the following AI-specific commands:

| Command | Description |
|---------|-------------|
| `:explain <start> <end>` | Get an explanation of lines `start` through `end` |
| `:improve <start> <end>` | Get improvement suggestions for lines `start` through `end` |
| `:generate <line> <description>` | Generate code at `line` based on the `description` |
| `:ai <query>` | Ask a custom question about the current file |

## Usage

### Basic Editing
- Press `i` to enter insert mode, `ESC` to return to normal mode
- Use `:w` to save, `:q` to quit, `:wq` to save and quit
- Navigation works with `h`, `j`, `k`, `l` keys (left, down, up, right)

### AI Features
1. Navigate to the code you want to work with
2. In normal mode, type `:explain 10 20` to explain lines 10-20
3. Use `:improve 10 20` to get improvement suggestions with a colorized diff view
4. Add `:generate 5 "Create a function that calculates factorial"` to generate code
5. Ask questions with `:ai How does this algorithm work?`

## Installation

```bash
# Install from source
git clone https://github.com/yourusername/aivim.git
cd aivim
pip install -e .

# Run AIVim
python -m aivim.run_editor file.py
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
- curses library (included with Python on most systems)

## License

This project is licensed under the MIT License - see the LICENSE file for details.