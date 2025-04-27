"""
Command handler module for processing command-line commands.
"""
import logging
import os
import os.path
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
            r'^analyze\s+(\d+)\s+(\d+)$': self._cmd_analyze,
            r'^generate\s+(\d+)\s+(.+)$': self._cmd_generate,
            r'^ai\s+(.+)$': self._cmd_ai_query,
            r'^set\s+(.+)$': self._cmd_set_option,
            r'^model$': self._cmd_model_selector,
            r'^model\s+(.+)$': self._cmd_set_model,
            r'^y$': self._cmd_confirm_yes,
            r'^n$': self._cmd_next_tab,    # Changed from nexttab back to n as requested
            r'^help$': self._cmd_help,
            # Tab navigation commands
            r'^N$': self._cmd_prev_tab,
            r'^tabnew$': self._cmd_tab_new,
            r'^tabnew\s+(.+)$': self._cmd_tab_new_file,
            r'^tabclose$': self._cmd_tab_close,
            # NLP mode commands
            r'^nlp$': self._cmd_enter_nlp_mode,
            r'^nlpmark\s+(\d+)\s+(\d+)$': self._cmd_mark_nlp_section,
            r'^nlptranslate$': self._cmd_translate_nlp,
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
            
            # Use non-blocking mode by default
            self.editor.ai_explain(start, end, blocking=False)
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
            
            # Use non-blocking mode by default
            self.editor.ai_improve(start, end, blocking=False)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing improve command: {str(e)}")
            return False
            
    def _cmd_analyze(self, start_line: str, end_line: str) -> bool:
        """
        Handle the analyze command (:analyze start end).
        Analyzes code complexity and potential bugs in the specified line range.

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
            
            # Use non-blocking mode by default
            self.editor.ai_analyze_code(start, end, blocking=False)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error executing analyze command: {str(e)}")
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
            
            # Use non-blocking mode by default
            self.editor.ai_generate(start, description, blocking=False)
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
            # Use non-blocking mode by default
            self.editor.ai_custom_query(query, blocking=False)
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
        # Handle AI model selection (for backward compatibility)
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
    
    def _cmd_model_selector(self) -> bool:
        """
        Handle the model selector command (:model).
        Shows a dialog to select an AI model.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.show_model_selector()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error showing model selector: {str(e)}")
            return False
    
    def _cmd_set_model(self, model_name: str) -> bool:
        """
        Handle the set model command (:model name).
        Sets the AI model directly.

        Args:
            model_name: The name of the model to set ('openai', 'claude', 'local')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the model name is valid
            if model_name.lower() in ["openai", "claude", "local"]:
                self.editor.set_ai_model(model_name.lower())
                return True
            else:
                self.editor.set_status_message(f"Unknown model: {model_name}. Valid options: openai, claude, local")
                return False
        except Exception as e:
            self.editor.set_status_message(f"Error setting AI model: {str(e)}")
            return False
            

    def _cmd_confirm_yes(self) -> bool:
        """
        Handle the confirm yes command (:y).
        Used to confirm AI improvement suggestions and create a new tab with
        the improved content.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Pass True for create_new_tab to open the improved code in a new tab
            self.editor.confirm_ai_action(True, create_new_tab=True)
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
    
    def _cmd_next_tab(self) -> bool:
        """
        Handle the next tab command (:nexttab).
        Switches to the next tab in the list.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.next_tab()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error switching to next tab: {str(e)}")
            return False
    
    def _cmd_prev_tab(self) -> bool:
        """
        Handle the previous tab command (:N).
        Switches to the previous tab in the list.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.prev_tab()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error switching to previous tab: {str(e)}")
            return False
    
    def _cmd_tab_new(self) -> bool:
        """
        Handle the tab new command (:tabnew).
        Creates a new empty tab.

        Returns:
            True if successful, False otherwise
        """
        try:
            tab_index = self.editor.create_tab("Untitled")
            self.editor.switch_to_tab(tab_index)
            self.editor.set_status_message("Created new tab")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error creating new tab: {str(e)}")
            return False
    
    def _cmd_tab_new_file(self, filename: str) -> bool:
        """
        Handle the tab new file command (:tabnew filename).
        Creates a new tab and opens the specified file.

        Args:
            filename: The file to open

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a new tab
            tab_index = self.editor.create_tab(os.path.basename(filename), filename=filename)
            self.editor.switch_to_tab(tab_index)
            
            # Load the file
            self.editor.load_file(filename)
            self.editor.set_status_message(f"Opened {filename} in new tab")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error opening file in new tab: {str(e)}")
            return False
    
    def _cmd_tab_close(self) -> bool:
        """
        Handle the tab close command (:tabclose).
        Closes the current tab.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.editor.close_current_tab():
                self.editor.set_status_message("Closed tab")
                return True
            else:
                # close_current_tab already sets an appropriate status message
                return False
        except Exception as e:
            self.editor.set_status_message(f"Error closing tab: {str(e)}")
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
            "Tab Management:",
            "  :n             - Switch to next tab",
            "  :N             - Switch to previous tab",
            "  :tabnew        - Create a new empty tab",
            "  :tabnew file   - Open file in a new tab",
            "  :tabclose      - Close the current tab",
            "",
            "AI Commands:",
            "  :explain s e   - Explain lines s through e",
            "  :improve s e   - Improve code from lines s through e",
            "  :analyze s e   - Analyze code complexity and bugs in lines s through e",
            "  :generate l d  - Generate code at line l based on description d",
            "  :ai query      - Ask AI about the current code",
            "  :model         - Show AI model selector popup with arrow key navigation",
            "  :model name    - Set AI model directly (openai, claude, local)",
            "  :set model     - Legacy command to set AI model (openai, claude, local)",
            "  :y             - Create a new tab with AI improved code",
            "  :n             - Reject AI suggestion",
            "",
            "NLP Mode:",
            "  :nlp           - Enter Natural Language Programming mode",
            "  nl (in normal) - Enter NLP mode (press 'n' then 'l')",
            "  :nlpmark s e   - Mark lines s through e as NLP section",
            "  :nlptranslate  - Force translation of NLP sections",
            "  #nlp <query>   - Single line AI query",
            "  #nlp           - Mark lines for multi-line AI query (multiple #nlp marks can be scattered in file)",
            "  Ctrl+Enter     - In NLP mode, sends entire script with context to AI",
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
        
    def _cmd_enter_nlp_mode(self) -> bool:
        """
        Handle the command to enter NLP mode (:nlp).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.mode = "NLP"
            # NLP handler will be initialized when handling input
            self.editor.set_status_message("-- NLP MODE --")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error entering NLP mode: {str(e)}")
            return False
            
    def _cmd_mark_nlp_section(self, start_line: str, end_line: str) -> bool:
        """
        Handle the command to mark an NLP section (:nlpmark start end).
        
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
            
            # Validate range
            if start < 0 or end >= len(self.editor.buffer.get_lines()) or start > end:
                self.editor.set_status_message("Invalid line range")
                return False
                
            # Insert NLP markers
            start_marker = "# NLP-BEGIN"
            end_marker = "# NLP-END"
            
            # Check if we need to adapt the markers to file type
            filename = self.editor.filename
            if filename:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ['.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cs']:
                    start_marker = "// NLP-BEGIN"
                    end_marker = "// NLP-END"
                elif ext in ['.html', '.xml', '.svg']:
                    start_marker = "<!-- NLP-BEGIN -->"
                    end_marker = "<!-- NLP-END -->"
                    
            # Add the markers
            self.editor.buffer.insert_line(start, start_marker)
            self.editor.buffer.insert_line(end + 2, end_marker)  # +2 because we inserted a line
            
            self.editor.set_status_message(f"Marked lines {start+1}-{end+1} as NLP section")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error marking NLP section: {str(e)}")
            return False
            
    def _cmd_translate_nlp(self) -> bool:
        """
        Handle the command to force translation of NLP sections (:nlptranslate).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure NLP handler is initialized
            if not self.editor.nlp_handler:
                from aivim.nlp_mode import NLPHandler
                self.editor.nlp_handler = NLPHandler(self.editor)
            
            # Show loading animation
            if hasattr(self.editor.display, "start_loading_animation"):
                self.editor.display.start_loading_animation("Processing NLP sections...")
                
            # First scan for any NLP sections
            self.editor.nlp_handler.scan_buffer_for_nlp_sections()
            
            # Check if we found any sections
            if not hasattr(self.editor.nlp_handler, "nlp_sections") or not self.editor.nlp_handler.nlp_sections:
                if hasattr(self.editor.display, "stop_loading_animation"):
                    self.editor.display.stop_loading_animation()
                self.editor.set_status_message("No NLP sections found to translate")
                return False
                
            # Process NLP sections
            self.editor.nlp_handler.process_nlp_sections()
            return True
        except Exception as e:
            # Make sure to stop the animation if there's an error
            if hasattr(self.editor.display, "stop_loading_animation"):
                self.editor.display.stop_loading_animation()
            self.editor.set_status_message(f"Error translating NLP sections: {str(e)}")
            logging.error(f"Error executing nlptranslate command: {str(e)}")
            return False