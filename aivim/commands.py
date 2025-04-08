"""
Command processing for AIVim
"""
import re
from typing import List


class CommandProcessor:
    """
    Processes command-line commands in AIVim
    """
    def __init__(self, editor):
        self.editor = editor
    
    def process(self, command: str) -> None:
        """
        Process a command entered in the command line
        
        Args:
            command: The command string (without the initial ':')
        """
        # Split command into command name and arguments
        parts = command.split()
        if not parts:
            return
        
        cmd_name = parts[0]
        args = parts[1:]
        
        # File operations
        if cmd_name in ['w', 'write']:
            filename = args[0] if args else self.editor.filename
            self.editor.save_file(filename)
            if filename:
                self.editor.buffer.mark_as_saved()
        
        # Quit operations
        elif cmd_name in ['q', 'quit']:
            self.editor.quit()
        elif cmd_name in ['q!', 'quit!']:
            self.editor.quit(force=True)
        elif cmd_name in ['wq']:
            filename = args[0] if args else self.editor.filename
            self.editor.save_file(filename)
            self.editor.quit()
        
        # Line operations
        elif re.match(r'^\d+$', cmd_name):  # Line number
            try:
                line_num = int(cmd_name) - 1  # Convert to 0-based indexing
                if 0 <= line_num < len(self.editor.buffer.get_lines()):
                    self.editor.cursor_y = line_num
                    self.editor.cursor_x = 0
                else:
                    self.editor.status_message = "Invalid line number"
            except ValueError:
                self.editor.status_message = "Invalid line number"
        
        # AI commands
        elif cmd_name in ['explain', 'improve', 'generate', 'ai']:
            self.editor.run_ai_command(cmd_name, args)
        
        # Help command
        elif cmd_name in ['help']:
            self._show_help()
        
        # Unknown command
        else:
            self.editor.status_message = f"Unknown command: {cmd_name}"
    
    def _show_help(self) -> None:
        """Display help information"""
        help_text = [
            "AIVim Help",
            "==========",
            "",
            "File Commands:",
            "  :w [filename]    - Write buffer to file",
            "  :q               - Quit (fails if unsaved changes)",
            "  :q!              - Force quit (discards changes)",
            "  :wq              - Write and quit",
            "",
            "Navigation:",
            "  h, j, k, l       - Move left, down, up, right",
            "  Arrow keys       - Move cursor",
            "  :<number>        - Go to line number",
            "",
            "Editing Modes:",
            "  i                - Enter insert mode",
            "  v                - Enter visual mode",
            "  ESC              - Return to normal mode",
            "",
            "AI Commands:",
            "  :explain <start> <end>    - Get explanation for lines",
            "  :improve <start> <end>    - Get improved version of lines",
            "  :generate <start> <end>   - Generate code based on lines",
            "  :ai <query>               - Custom AI query",
            "",
            "Version Navigation:",
            "  Ctrl+E           - Next version (after AI changes)",
            "  Ctrl+W           - Previous version",
            "",
            "Press ESC to return to editing",
        ]
        
        # Create a new temporary buffer with the help text
        old_lines = self.editor.buffer.get_lines()
        self.editor.buffer.set_lines(help_text)
        self.editor.status_message = "Help (Press ESC to exit help)"
        
        # Enter a mini-mode for viewing help
        self.editor.display.refresh(
            self.editor.buffer.get_lines(),
            0, 0, self.editor.mode,
            "HELP MODE", 
            "Press ESC to exit help", 
            False
        )
        
        # Wait for ESC key
        while True:
            key = self.editor.display.stdscr.getch()
            if key == 27:  # ESC
                break
            elif key == ord('j') and self.editor.cursor_y < len(help_text) - 1:
                self.editor.cursor_y += 1
            elif key == ord('k') and self.editor.cursor_y > 0:
                self.editor.cursor_y -= 1
            
            self.editor.display.refresh(
                self.editor.buffer.get_lines(),
                self.editor.cursor_y, 0, 
                self.editor.mode,
                "HELP MODE", 
                "Press ESC to exit help", 
                False
            )
        
        # Restore original buffer
        self.editor.buffer.set_lines(old_lines)
        self.editor.status_message = "Exited help"
