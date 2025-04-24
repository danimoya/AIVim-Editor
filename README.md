
# AIVim - AI-Enhanced Text Editor

AIVim is an AI-enhanced version of Vim built in Python, offering intelligent code assistance and generation capabilities while maintaining the core modal editing experience. Combining the power of different AI models with familiar Vim interactions, AIVim helps developers understand, improve, and generate code more efficiently.

## Features

### Modal Editing
- **Normal Mode**: Navigate and edit text using Vim-style commands
- **Insert Mode**: Type and modify text directly
- **Visual Mode**: Select text for operations 
- **Command Mode**: Enter commands with the `:` prefix
- **NLP Mode**: Edit code using natural language that's automatically translated to code
  - **Enhanced NLP Mode**: Now with improved keyboard handling:
    - **Enter**: Creates a new line (like standard editing)
    - **Shift+Enter**: Process current file NLP sections only
    - **Ctrl+Enter**: Process entire script with all tabs as context

### AI-Powered Assistance
- **Code Explanation**: Understand complex code with detailed explanations
- **Code Improvement**: Get AI-powered refactoring and optimization suggestions with diff-style presentation
- **Code Generation**: Generate new code based on natural language descriptions
- **Custom AI Queries**: Ask questions about your code and receive contextual answers
- **Code Analysis**: Get complexity analysis and bug detection for your code
- **Natural Language Programming**: Edit code using natural language that's automatically translated to code
- **Multi-Provider Support**: Choose between OpenAI, Anthropic Claude, or local LLM models
  - **Model Selection UI**: Interactive dialog for selecting AI providers and specific models
  - **Command-Line Control**: Use `:model` command to view and change AI models directly

### Editor Features
- **Vim-Style Commands**: Familiar commands like `dd` (delete line), `yy` (yank line), `p` (paste)
- **Multi-Tab Interface**: View and compare original and AI-improved code in tabs
- **Version History**: Automatic tracking of file changes with metadata
- **File Backups**: Automatic backup creation when applying improvements (with timestamps)
- **Loading Indicators**: Visual feedback when AI operations are in progress
- **Line Numbers**: Display line numbers for easier navigation and reference
- **Enhanced Command Feedback**: Improved error handling and status messaging
- **Performance Logging**: Better handling of model performance metrics and logs
- **Status Line**: Displays current mode, filename, cursor position, and tab information
- **Syntax Highlighting**: Basic syntax highlighting for improved code readability
- **Animated Loading**: Visual indicators during AI operations to show progress

### Web Interface
- **Browser Access**: Access AIVim from a web browser via Flask
- **Code Editor**: Edit and modify code directly in the browser
- **AI Operations**: Access all AI capabilities through the web interface
- **Results Display**: View AI-generated output in a dedicated results area

## AI Commands

AIVim provides the following AI-specific commands:

| Command | Description |
|---------|-------------|
| `:explain <start> <end>` | Get an explanation of lines `start` through `end` |
| `:improve <start> <end>` | Get improvement suggestions for lines `start` through `end` |
| `:generate <line> <description>` | Generate code at `line` based on the `description` |
| `:analyze <start> <end>` | Analyze code complexity and detect bugs in lines `start` through `end` |
| `:ai <query>` | Ask a custom question about the current file |
| `:model` | Show AI model selector popup with arrow key navigation |
| `:model <provider>` | Set the AI model provider directly (openai, claude, local) |
| `:set model=<provider>` | Legacy command to set the AI model provider |
| `:nlp` | Enter NLP mode |
| `nl` | Enter NLP mode by pressing 'n' then 'l' in normal mode |
| `#nlp <query>` | Single line AI query |
| `#nlp` | Mark lines for multi-line AI query |
| `Enter` | In NLP mode, creates a new line just like in INSERT mode |
| `Shift+Enter` | In NLP mode, processes only the current file NLP sections |
| `Ctrl+Enter` | In NLP mode, sends entire script with all tabs as context to AI |
| `:nlpmark <start> <end>` | Mark lines `start` through `end` as an NLP section |
| `:nlptranslate` | Force translation of NLP sections (now with improved feedback) |

## Tab Navigation Commands

| Command | Description |
|---------|-------------|
| `:nexttab` or `:n` | Switch to the next tab |
| `:prevtab` or `:N` | Switch to the previous tab |
| `:tabnew` | Create a new empty tab |
| `:tabnew <filename>` | Create a new tab and open the specified file |
| `:tabclose` | Close the current tab |

## Vim Commands Supported

| Command | Description |
|---------|-------------|
| `dd` | Delete current line |
| `yy` | Yank (copy) current line |
| `p` | Paste after cursor |
| `P` | Paste before cursor |
| `o` | Open new line below cursor and enter insert mode |
| `O` | Open new line above cursor and enter insert mode |
| `x` | Delete character under cursor |
| `s` | Delete character under cursor and enter insert mode |
| `u` | Undo last change |
| `Ctrl+r` | Redo |
| `i` | Enter insert mode |
| `v` | Enter visual mode |
| `nl` | Enter NLP mode (press 'n' then 'l') |
| `Ctrl+X Ctrl+N` | Enter NLP mode from insert mode |
| `gg` | Go to first line |
| `G` | Go to last line |
| `$` | Go to end of line |
| `/pattern` | Search forward for pattern |
| `?pattern` | Search backward for pattern |
| `n` | Find next search match |
| `N` | Find previous search match |
| `:%s/old/new/g` | Replace all occurrences of 'old' with 'new' |
| `:<line_number>` | Jump to line number (integer expected) |
| `:$` | Jump to last line of the file |

## Usage

### Basic Editing
- Press `i` to enter insert mode, `ESC` to return to normal mode
- Use `:w` to save, `:q` to quit, `:wq` to save and quit
- Navigation works with arrow keys (primary) or `h`, `j`, `k`, `l` keys (alternative)
- Jump to specific lines with `:1`, `:14` or `:$` (last line)
- Search for text with `/pattern` (forward) or `?pattern` (backward)
- Use `n` to find next match, `N` to find previous match
- Replace text with `:%s/old/new/g` syntax

### NLP Mode
- Enter NLP mode with command `:nlp` or by pressing `n` then `l` in normal mode
- In insert mode, use `Ctrl+X` then `Ctrl+N` to switch to NLP mode
- Write code using natural language comments that will be automatically translated to code
- Mark NLP sections in your code with special comments:
  ```
  # NLP-BEGIN
  # Create a function that calculates the factorial of a number
  # NLP-END
  ```
  Or with the new inline format:
  ```
  #nlp Calculate factorial of a number recursively
  ```
- The editor will automatically detect comment blocks and translate them to code
- Changes are applied after you stop typing (debounce delay)
- **Enhanced keyboard shortcuts**:
  - `Enter` creates a new line just like in INSERT mode
  - `Shift+Enter` processes only the current file's NLP sections
  - `Ctrl+Enter` processes the entire script with all tabs as context
- Use `:nlpmark <start> <end>` to manually mark a section for translation
- Force immediate translation with `:nlptranslate` command (improved with visual feedback)
- All open files in tabs are considered context for better code generation

### AI Features
1. Navigate to the code you want to work with
2. In normal mode, type `:explain 10 20` to explain lines 10-20
3. Use `:improve 10 20` to get improvement suggestions:
   - A new tab opens showing a colorized diff view of proposed changes
   - Review the modifications in the diff view
   - To apply the changes, switch back to the original tab and confirm
   - A backup of the original file is automatically created with a timestamp
4. Generate code with `:generate 5 "Create a function that calculates factorial"` - It will be inserted at the line 5 of your current file.
5. Analyze code with `:analyze 10 20` to identify complexity issues and potential bugs
6. Ask questions with `:ai query How does this algorithm work?`
7. Switch between AI providers:
   - Use `:model` to open an interactive model selector with arrow key navigation
   - Use `:model openai` to directly switch to OpenAI
   - Use `:model claude` to directly switch to Anthropic Claude
   - Use `:model local` to directly switch to local LLM
   - Legacy: `:set model=openai`, `:set model=claude`, or `:set model=local`

## Installation from GitHub/Source

To install AIVim:

```bash
# Install from source
git clone https://github.com/danimoya/aivim-editor.git
cd AIVim-Editor
pip install -r requirements.txt

# Run AIVim
python -m aivim.run_editor <file>
```

To make an alias for current session or install in .bash_profile, try something like:
```bash
alias aivim="python -m aivim.run_editor"
```

#### System-wide Installation

To make AIVim available as a system-wide command (`aivim`), follow these steps:

```bash
# For temporary use in current session
alias aivim='python -m aivim.run_editor'

# For permanent installation, add to your shell configuration
echo 'alias aivim="python -m aivim.run_editor"' >> ~/.bashrc
# Or for Zsh
echo 'alias aivim="python -m aivim.run_editor"' >> ~/.zshrc

# Apply changes without restarting the terminal
source ~/.bashrc  # or source ~/.zshrc
```

For a more robust system-wide installation, create a symbolic link:

```bash
# Create a symbolic link in a directory that's in your PATH
sudo ln -s "$(which python) $(pwd)/run_editor.py" /usr/local/bin/aivim
sudo chmod +x /usr/local/bin/aivim

# Now you can run AIVim from anywhere
aivim myfile.py
```

### VENV Installation

To isolate "aivim" from system Python libraries, do the following:

```bash
python -m venv aivim
source aivim/bin/activate
pip install aivim
pip install anthropic llama-cpp-python
```

### Configuration File

Instead of setting environment variables, you can create a configuration file for storing API keys. AIVim will automatically check the following locations for a config file:

1. `~/.aivim/config`
2. `~/.config/aivim/config`
3. `~/.aivimrc`
4. `./aivim.config` (in the current directory)

Create a configuration file with the following format:

```ini
# AIVim Configuration File

[General]
# Choose your default AI model provider: openai, claude, or local
default_model = openai

[OpenAI]
# Your OpenAI API key (get it from https://platform.openai.com/account/api-keys)
api_key = your_openai_api_key_here

[Anthropic]
# Your Anthropic Claude API key (get it from https://console.anthropic.com/)
api_key = your_anthropic_api_key_here

[LocalLLM]
# Path to your local model file (generally a .gguf file)
model_path = /path/to/your/local/model.gguf
```

To create this configuration file:

```bash
# Create a config directory
mkdir -p ~/.config/aivim

# Create and edit the configuration file
nano ~/.config/aivim/config

# Set proper permissions to protect your API keys
chmod 600 ~/.config/aivim/config
```

When AIVim starts, it will display information about the config file it loaded and the AI model being used in the status bar.

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
# Inside AIVim: :model local (or :model to show the selector)
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
# http://0.0.0.0:5000
```

The web interface provides access to all the AI-powered features through a more traditional web IDE experience. It communicates with the same AI services backend as the terminal-based editor.

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

