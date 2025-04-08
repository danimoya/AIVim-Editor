"""
Command handler module for processing command-line commands.
"""

import re
from typing import Dict, Callable, List, Optional, Tuple, Any

class CommandHandler:
    """
    Handler for Vim-style commands.
    """
    
    def __init__(self, editor):
        """
        Initialize the command handler.

        Args:
            editor: Reference to the editor
        """
        self.editor = editor
        self.commands = self._register_commands()
    
    def _register_commands(self) -> Dict[str, Callable]:
        """
        Register command handlers.

        Returns:
            Dictionary mapping command patterns to handler functions
        """
        return {
            r'^w$': self._cmd_write,
            r'^w\s+(.+)$': self._cmd_write_as,
            r'^q$': self._cmd_quit,
            r'^wq$': self._cmd_write_quit,
            r'^q!$': self._cmd_force_quit,
            r'^explain\s+(\d+)\s+(\d+)$': self._cmd_explain,
            r'^improve\s+(\d+)\s+(\d+)$': self._cmd_improve,
            r'^generate\s+(\d+)\s+(.+)$': self._cmd_generate,
            r'^ai\s+(.+)$': self._cmd_ai_query,
            r'^set\s+(.+)$': self._cmd_set_option,
            r'^help$': self._cmd_help,
        }
    
    def execute(self, command_line: str) -> bool:
        """
        Execute a command.

        Args:
            command_line: The command string

        Returns:
            True if the command was recognized and executed, False otherwise
        """
        command = command_line.strip()
        
        for pattern, handler in self.commands.items():
            match = re.match(pattern, command)
            if match:
                return handler(*match.groups())
        
        self.editor.set_status_message(f"Unknown command: {command}")
        return False
    
    def _cmd_write(self) -> bool:
        """
        Handle the write command (:w).

        Returns:
            True if successful, False otherwise
        """
        return self.editor.save_file()
    
    def _cmd_write_as(self, filename: str) -> bool:
        """
        Handle the write as command (:w filename).

        Args:
            filename: Target filename

        Returns:
            True if successful, False otherwise
        """
        return self.editor.save_file_as(filename)
    
    def _cmd_quit(self) -> bool:
        """
        Handle the quit command (:q).

        Returns:
            True if successful, False otherwise
        """
        # Check for unsaved changes
        # In a real implementation, we would check for buffer modifications
        self.editor.quit = True
        return True
    
    def _cmd_write_quit(self) -> bool:
        """
        Handle the write and quit command (:wq).

        Returns:
            True if successful, False otherwise
        """
        if self.editor.save_file():
            self.editor.quit = True
            return True
        return False
    
    def _cmd_force_quit(self) -> bool:
        """
        Handle the force quit command (:q!).

        Returns:
            True if successful, False otherwise
        """
        self.editor.quit = True
        return True
    
    def _cmd_explain(self, start_line: str, end_line: str) -> bool:
        """
        Handle the explain command (:explain start end).

        Args:
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 0-based indexing
            start = int(start_line) - 1
            end = int(end_line) - 1
            
            self.editor.ai_explain(start, end)
            return True
        except ValueError:
            self.editor.set_status_message("Invalid line numbers")
            return False
    
    def _cmd_improve(self, start_line: str, end_line: str) -> bool:
        """
        Handle the improve command (:improve start end).

        Args:
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 0-based indexing
            start = int(start_line) - 1
            end = int(end_line) - 1
            
            self.editor.ai_improve(start, end)
            return True
        except ValueError:
            self.editor.set_status_message("Invalid line numbers")
            return False
    
    def _cmd_generate(self, start_line: str, description: str) -> bool:
        """
        Handle the generate command (:generate line_number description).

        Args:
            start_line: Starting line number for insertion (1-based)
            description: Description of what code to generate

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 0-based indexing
            start = int(start_line) - 1
            
            # Call ai_generate with the starting line and description
            self.editor.ai_generate(start, description)
            return True
        except ValueError:
            self.editor.set_status_message("Invalid line number")
            return False
    
    def _cmd_ai_query(self, query: str) -> bool:
        """
        Handle the AI query command (:ai query).

        Args:
            query: The query string

        Returns:
            True if successful, False otherwise
        """
        self.editor.ai_custom_query(query)
        return True
    
    def _cmd_set_option(self, option: str) -> bool:
        """
        Handle the set option command (:set option).

        Args:
            option: The option string

        Returns:
            True if successful, False otherwise
        """
        # Not implemented yet, but could be used for editor settings
        self.editor.set_status_message(f"Option setting not implemented: {option}")
        return True
    
    def _cmd_help(self) -> bool:
        """
        Handle the help command (:help).

        Returns:
            True if successful, False otherwise
        """
        help_text = [
            "AIVim Commands:",
            "  :w                   - Write file",
            "  :w filename          - Write to filename",
            "  :q                   - Quit",
            "  :wq                  - Write and quit",
            "  :q!                  - Force quit",
            "  :explain m n         - Explain lines m through n",
            "  :improve m n         - Improve lines m through n",
            "  :generate line desc  - Generate code at line based on description",
            "  :ai query            - Send custom query to AI",
            "  :help                - Show this help",
            "",
            "Navigation:",
            "  Ctrl+Left/Right - Navigate AI version history",
            "",
            "Press any key to continue..."
        ]
        
        # In a real implementation, we would display this in a scrollable window
        self.editor.set_status_message("\n".join(help_text[:3]) + "...")
        return True
