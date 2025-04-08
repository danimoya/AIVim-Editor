"""
Command processing for AIVim
"""
import logging
import re
from typing import Dict, Callable, List, Optional

from aivim.utils import tokenize_command, parse_line_range


class CommandProcessor:
    """
    Processes command-line commands in AIVim
    """
    def __init__(self, editor):
        """
        Initialize the command processor
        
        Args:
            editor: Reference to the editor
        """
        self.editor = editor
        self.command_handlers = self._register_commands()
    
    def _register_commands(self) -> Dict[str, Callable]:
        """
        Register command handlers
        
        Returns:
            Dictionary mapping command patterns to handler functions
        """
        return {
            # File operations
            r'^w$': self._cmd_write,
            r'^w\s+(.+)$': self._cmd_write_as,
            r'^q$': self._cmd_quit,
            r'^q!$': self._cmd_force_quit,
            r'^wq$': self._cmd_write_quit,
            
            # AI operations
            r'^explain\s+(\d+)\s+(\d+)$': self._cmd_explain,
            r'^improve\s+(\d+)\s+(\d+)$': self._cmd_improve,
            r'^generate\s+(\d+)\s+(.+)$': self._cmd_generate,
            r'^ai\s+(.+)$': self._cmd_ai_query,
            
            # Settings
            r'^set\s+(.+)$': self._cmd_set_option,
            
            # Help
            r'^help$': self._cmd_help,
        }
    
    def process(self, command: str) -> bool:
        """
        Process a command entered in the command line
        
        Args:
            command: The command string (without the initial ':')
            
        Returns:
            True if command was recognized and executed, False otherwise
        """
        if not command:
            return False
        
        # Log command
        logging.info(f"Processing command: {command}")
        
        # Match command against patterns
        for pattern, handler in self.command_handlers.items():
            match = re.match(pattern, command)
            if match:
                try:
                    # Call the handler with matched groups as arguments
                    return handler(*match.groups())
                except Exception as e:
                    logging.error(f"Error executing command '{command}': {str(e)}")
                    self.editor.set_status_message(f"Error: {str(e)}")
                    return False
        
        self.editor.set_status_message(f"Unknown command: {command}")
        return False
    
    def _cmd_write(self) -> bool:
        """
        Handle the write command (:w)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.editor.filename:
            self.editor.set_status_message("No filename specified (use :w filename)")
            return False
        
        self.editor.save_file()
        return True
    
    def _cmd_write_as(self, filename: str) -> bool:
        """
        Handle the write as command (:w filename)
        
        Args:
            filename: Target filename
            
        Returns:
            True if successful, False otherwise
        """
        self.editor.save_file(filename)
        return True
    
    def _cmd_quit(self) -> bool:
        """
        Handle the quit command (:q)
        
        Returns:
            True if successful, False otherwise
        """
        if self.editor.buffer.is_modified():
            self.editor.set_status_message("No write since last change (use :q! to override)")
            return False
        
        self.editor.quit()
        return True
    
    def _cmd_force_quit(self) -> bool:
        """
        Handle the force quit command (:q!)
        
        Returns:
            True if successful, False otherwise
        """
        self.editor.quit(force=True)
        return True
    
    def _cmd_write_quit(self) -> bool:
        """
        Handle the write and quit command (:wq)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.editor.filename:
            self.editor.set_status_message("No filename specified")
            return False
        
        self.editor.save_file()
        self.editor.quit()
        return True
    
    def _cmd_explain(self, start_line: str, end_line: str) -> bool:
        """
        Handle the explain command (:explain start end)
        
        Args:
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)
            
        Returns:
            True if successful, False otherwise
        """
        start, end = parse_line_range(start_line, end_line)
        if start < 0 or end < 0:
            self.editor.set_status_message("Invalid line range")
            return False
        
        self.editor.ai_explain(start, end)
        return True
    
    def _cmd_improve(self, start_line: str, end_line: str) -> bool:
        """
        Handle the improve command (:improve start end)
        
        Args:
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)
            
        Returns:
            True if successful, False otherwise
        """
        start, end = parse_line_range(start_line, end_line)
        if start < 0 or end < 0:
            self.editor.set_status_message("Invalid line range")
            return False
        
        self.editor.ai_improve(start, end)
        return True
    
    def _cmd_generate(self, start_line: str, description: str) -> bool:
        """
        Handle the generate command (:generate line_number description)
        
        Args:
            start_line: Starting line number for insertion (1-based)
            description: Description of what code to generate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 0-based
            start = int(start_line) - 1
            
            if start < 0 or start > len(self.editor.buffer.get_lines()):
                self.editor.set_status_message("Invalid line number")
                return False
            
            self.editor.ai_generate(start, description)
            return True
            
        except ValueError:
            self.editor.set_status_message("Invalid line number")
            return False
    
    def _cmd_ai_query(self, query: str) -> bool:
        """
        Handle the AI query command (:ai query)
        
        Args:
            query: The query string
            
        Returns:
            True if successful, False otherwise
        """
        self.editor.ai_custom_query(query)
        return True
    
    def _cmd_set_option(self, option: str) -> bool:
        """
        Handle the set option command (:set option)
        
        Args:
            option: The option string
            
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement settings
        self.editor.set_status_message(f"Set option: {option} (not implemented yet)")
        return True
    
    def _cmd_help(self) -> bool:
        """
        Handle the help command (:help)
        
        Returns:
            True if successful, False otherwise
        """
        self._show_help()
        return True
    
    def _show_help(self) -> None:
        """Display help information"""
        help_text = [
            "AIVim Help",
            "----------",
            "",
            "Navigation:",
            "  Arrow keys - Move cursor (primary)",
            "  h, j, k, l - Alternative cursor movement",
            "",
            "Modes:",
            "  i - Enter insert mode",
            "  ESC - Return to normal mode",
            "  v - Enter visual mode",
            "  : - Enter command mode",
            "",
            "File Operations:",
            "  :w - Write file",
            "  :w filename - Write to filename",
            "  :q - Quit",
            "  :q! - Force quit (discard changes)",
            "  :wq - Write and quit",
            "",
            "AI Commands:",
            "  :explain m n - Explain lines m through n",
            "  :improve m n - Improve code in lines m through n",
            "  :generate n text - Generate code at line n based on description",
            "  :ai query - Ask a custom query about the code",
            "",
            "History:",
            "  Ctrl+E - Next version (after AI changes)",
            "  Ctrl+W - Previous version",
        ]
        
        self.editor.display.show_dialog("Help", help_text)