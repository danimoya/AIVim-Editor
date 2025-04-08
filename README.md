# AIVim

An AI-enhanced version of Vim implemented in Python with OpenAI integration.

## Features

- Vim-like modal editing (normal, insert, visual, command modes)
- AI-powered code assistance and generation
- Lightweight and embeddable in other applications
- Cross-platform compatibility

## AI Commands

AIVim extends the traditional Vim command set with AI-specific commands:

- `:explain m n` - Get an explanation of lines m through n
- `:improve m n` - Improve the code in lines m through n
- `:generate line description` - Generate code at the specified line based on a description
- `:ai query` - Ask a custom query about the current file

## Requirements

- Python 3.11 or higher
- OpenAI API key

## Usage

### Standalone Editor

```bash
# Open a file
python main.py path/to/file.py

# Create a new file
python main.py new_file.py
```

### Embedded in Other Applications

```python
from aivim.editor import Editor
from main import embed_editor

# Use the embed_editor function for proper curses setup
embed_editor("path/to/file.py")
```

## License

MIT
