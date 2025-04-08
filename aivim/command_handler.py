"""
Command handler module for processing command-line commands.
"""
import logging
import os
import re
from typing import Dict, Callable, List, Any, Optional, Match


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
        commands = {
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
            r'^chat$': self._cmd_chat,
            r'^y$': self._cmd_confirm_yes,
            r'^n$': self._cmd_confirm_no,
            r'^help$': self._cmd_help,
        }
        
        return commands
    
    def execute(self, command_line: str) -> bool:
        """
        Execute a command.

        Args:
            command_line: The command string

        Returns:
            True if the command was recognized and executed, False otherwise
        """
        # Strip leading : if present
        if command_line.startswith(':'):
            command_line = command_line[1:]
        
        # Find matching command pattern
        for pattern, handler in self.commands.items():
            match = re.match(pattern, command_line)
            if match:
                logging.info(f"Executing command: {command_line}")
                return handler(*match.groups())
        
        self.editor.set_status_message(f"Unknown command: {command_line}")
        return False
    
    def _cmd_write(self) -> bool:
        """
        Handle the write command (:w).

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.save_file()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error saving file: {str(e)}")
            return False
    
    def _cmd_write_as(self, filename: str) -> bool:
        """
        Handle the write as command (:w filename).

        Args:
            filename: Target filename

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.save_file(filename)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error saving file: {str(e)}")
            return False
    
    def _cmd_quit(self) -> bool:
        """
        Handle the quit command (:q).

        Returns:
            True if successful, False otherwise
        """
        self.editor.quit()
        return True
    
    def _cmd_write_quit(self) -> bool:
        """
        Handle the write and quit command (:wq).

        Returns:
            True if successful, False otherwise
        """
        if self._cmd_write():
            return self._cmd_quit()
        return False
    
    def _cmd_force_quit(self) -> bool:
        """
        Handle the force quit command (:q!).

        Returns:
            True if successful, False otherwise
        """
        self.editor.quit(force=True)
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
            # Convert to 0-based
            start = int(start_line) - 1
            end = int(end_line) - 1
            
            self.editor.ai_explain(start, end)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing explain command: {str(e)}")
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
            # Convert to 0-based
            start = int(start_line) - 1
            end = int(end_line) - 1
            
            self.editor.ai_improve(start, end)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing improve command: {str(e)}")
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
            # Convert to 0-based
            start = int(start_line) - 1
            
            self.editor.ai_generate(start, description)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing generate command: {str(e)}")
            return False
    
    def _cmd_ai_query(self, query: str) -> bool:
        """
        Handle the AI query command (:ai query).

        Args:
            query: The query string

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.ai_custom_query(query)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing AI query: {str(e)}")
            return False
    
    def _cmd_set_option(self, option: str) -> bool:
        """
        Handle the set option command (:set option).

        Args:
            option: The option string

        Returns:
            True if successful, False otherwise
        """
        # Handle AI model selection
        if option.lower() in ["openai", "claude", "local"]:
            try:
                self.editor.set_ai_model(option.lower())
                self.editor.set_status_message(f"AI model set to: {option}")
                return True
            except Exception as e:
                self.editor.set_status_message(f"Error setting AI model: {str(e)}")
                return False
        else:
            self.editor.set_status_message(f"Unknown option: {option}")
            return False
            
    def _cmd_chat(self) -> bool:
        """
        Handle the chat command (:chat).
        Opens an interactive chat dialog with the AI.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.start_ai_chat()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error starting chat: {str(e)}")
            return False
            
    def _cmd_confirm_yes(self) -> bool:
        """
        Handle the confirm yes command (:y).
        Used to confirm AI improvement suggestions.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.confirm_ai_action(True)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error handling confirmation: {str(e)}")
            return False
            
    def _cmd_confirm_no(self) -> bool:
        """
        Handle the confirm no command (:n).
        Used to reject AI improvement suggestions.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.confirm_ai_action(False)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error handling rejection: {str(e)}")
            return False
    
    def _cmd_help(self) -> bool:
        """
        Handle the help command (:help).

        Returns:
            True if successful, False otherwise
        """
        help_text = [
            "AIVim Commands:",
            "",
            "File Operations:",
            "  :w             - Save the current file",
            "  :w filename    - Save as filename",
            "  :q             - Quit (fails if unsaved changes)",
            "  :q!            - Force quit (discard changes)",
            "  :wq            - Save and quit",
            "",
            "AI Commands:",
            "  :explain s e   - Explain lines s through e",
            "  :improve s e   - Improve code from lines s through e",
            "  :generate l d  - Generate code at line l based on description d",
            "  :ai query      - Ask AI about the current code",
            "  :chat          - Start an interactive chat with AI",
            "  :set model     - Set AI model (openai, claude, local)",
            "  :y             - Confirm AI suggestion",
            "  :n             - Reject AI suggestion",
            "",
            "Navigation:",
            "  Arrow keys     - Move cursor (primary method)",
            "  h,j,k,l        - Alternative cursor movement",
            "  i              - Enter insert mode",
            "  Esc            - Return to normal mode",
            "  v              - Enter visual mode for selection",
            "",
            "Normal Mode:",
            "  dd             - Delete current line",
            "  p              - Paste after cursor",
            "  u              - Undo",
            "  Ctrl+r         - Redo",
        ]
        
        self.editor.display.show_dialog("Help", help_text)
        return True