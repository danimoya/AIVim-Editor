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
            # File operations
            r'^w!(?:\s+(.+))?$': lambda filename: bool(self.editor.save_file(filename, force=True)),
            r'^tabclose\s+(save|discard|cancel)$': self.editor.close_current_tab,
            r'^nexttab$': self._cmd_next_tab,
            r'^prevtab$': self._cmd_prev_tab,
            r'^reject$': self._cmd_confirm_no,
            r'^apply$': lambda: self.editor.confirm_ai_action(True, copy=False),
            r'^w$': self._cmd_write,
            r'^w\s+(.+)$': self._cmd_write_as,
            r'^q$': self._cmd_quit,
            r'^wq$': self._cmd_write_quit,
            r'^q!$': self._cmd_force_quit,
            r'^e$': self._cmd_edit_current,  # Edit current file (reload)
            r'^e\s+(.+)$': self._cmd_edit,    # Edit specified file
            r'^e!$': self._cmd_force_edit_current,  # Force reload current file
            r'^e!\s+(.+)$': self._cmd_force_edit,   # Force edit specified file
            r'^new$': self._cmd_new_buffer,   # Create new buffer/tab
            r'^new\s+(.+)$': self._cmd_new_buffer_named,  # Create new buffer with name
            r'^saveas\s+(.+)$': self._cmd_save_as,  # Save with different filename
            r'^browse$': self._cmd_browse_files,     # Open file browser
            # AI operations
            r'^explain\s+(\d+)\s+(\d+)$': self._cmd_explain,
            r'^improve\s+(\d+)\s+(\d+)$': self._cmd_improve,
            r'^analyze\s+(\d+)\s+(\d+)$': self._cmd_analyze,
            r'^generate\s+(\d+)\s+(.+)$': self._cmd_generate,
            r'^ai\s+(.+)$': self._cmd_ai_query,
            # Settings commands - more specific patterns first
            r'^set\?$': self._cmd_set_help,
            r'^set\s+all$': self._cmd_set_all,
            r'^set\s+(\w+)!$': self._cmd_set_toggle,
            r'^set\s+no(\w+)$': self._cmd_set_no_option,
            r'^set\s+(\w+)=(.*)$': self._cmd_set_value,
            r'^set\s+(\w+)$': self._cmd_set_show,
            r'^source\s+(.+)$': self._cmd_source,
            r'^source$': self._cmd_source_default,
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
            r'^nlpcontext$': lambda: self.editor.show_dialog('Selected context', [str(c) for c in self.editor.nlp_handler.context_preview()] if self.editor.nlp_handler else ['No context selected']),
            r'^nlpcontext\s+(.+)$': self._cmd_nlp_context,
            r'^nlp$': self._cmd_enter_nlp_mode,
            r'^nlpmark\s+(\d+)\s+(\d+)$': self._cmd_mark_nlp_section,
            r'^nlptranslate$': self._cmd_translate_nlp,
            r'^nlplive$': self._cmd_toggle_nlp_live_mode,
            # Debug mode command
            r'^debug$': self._cmd_toggle_debug_mode,
            # Search/Replace commands
            r'^noh$': self._cmd_no_highlight,
            r'^nohlsearch$': self._cmd_no_highlight,
            # Substitution patterns (must be more specific before general)
            r'^%s/([^/]*)/([^/]*)/(g?c?)$': self._cmd_substitute_all,
            r'^(\d+),(\d+)s/([^/]*)/([^/]*)/(g?c?)$': self._cmd_substitute_range,
            r'^s/([^/]*)/([^/]*)/(g?c?)$': self._cmd_substitute_current,
            r'^\'<,\'>s/([^/]*)/([^/]*)/(g?c?)$': self._cmd_substitute_visual,
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
        
        from .substitution import parse
        try:
            parsed=parse(command_line,self.editor)
            if parsed:
                pattern,replacement,bounds,flags=parsed
                self.editor.substitute(pattern,replacement,bounds,('g' in flags)^self.editor.settings.search.gdefault,'c' in flags,flags=flags)
                return True
        except (ValueError,re.error) as exc:
            self.editor.set_status_message(str(exc));return False
        # Find matching command pattern
        for pattern, handler in self.commands.items():
            match = re.match(pattern, command_line)
            if match:
                logging.info("Command dispatched")
                try:return handler(*match.groups())
                except (ValueError,OSError) as exc:
                    self.editor.set_status_message('Command failed; input preserved: '+str(exc));return False
        
        self.editor.set_status_message(f"Unknown command: {command_line}")
        return False
    
    def _cmd_write(self):
        return bool(self.editor.save_file())
    
    def _cmd_write_as(self, filename):
        return bool(self.editor.save_file(os.path.expanduser(filename)))
    
    def _cmd_quit(self):
        return self.editor.quit()
    
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
    
    def _cmd_set_help(self) -> bool:
        """
        Handle the set help command (:set?).

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            help_lines = self.editor.settings.get_help()
            self.editor.display.show_dialog("Settings Help", help_lines)
            return True
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_set_all(self) -> bool:
        """
        Handle the set all command (:set all).

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            all_settings = self.editor.settings.get_all()
            lines = ["All Settings", "=" * 50, ""]
            
            for category, settings in all_settings.items():
                lines.append(f"{category.upper()} Settings:")
                for key, value in settings.items():
                    lines.append(f"  {key}={value}")
                lines.append("")
            
            self.editor.display.show_dialog("All Settings", lines)
            return True
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_set_toggle(self, option: str) -> bool:
        """
        Handle the set toggle command (:set option!).

        Args:
            option: Option to toggle

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            if self.editor.settings.toggle(option):
                value = self.editor.settings.get(option)
                self.editor.set_status_message(f"{option}={value}")
                # Apply the setting immediately if relevant
                self._apply_setting(option, value)
                return True
            else:
                self.editor.set_status_message(f"Cannot toggle option: {option}")
                return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_set_no_option(self, option: str) -> bool:
        """
        Handle the set no option command (:set nooption).

        Args:
            option: Option to turn off

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            # Only works for boolean options
            current = self.editor.settings.get(option)
            if isinstance(current, bool):
                if self.editor.settings.set(option, False):
                    self.editor.set_status_message(f"no{option}")
                    # Apply the setting immediately if relevant
                    self._apply_setting(option, False)
                    return True
            self.editor.set_status_message(f"Invalid option: no{option}")
            return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_set_value(self, option: str, value: str) -> bool:
        """
        Handle the set value command (:set option=value).

        Args:
            option: Option name
            value: New value

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            # Strip quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            if self.editor.settings.set(option, value):
                self.editor.set_status_message(f"{option}={value}")
                # Apply the setting immediately if relevant
                self._apply_setting(option, self.editor.settings.get(option))
                return True
            else:
                self.editor.set_status_message(f"Error setting {option}={value}")
                return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_set_show(self, option: str) -> bool:
        """
        Handle the set show command (:set option).

        Args:
            option: Option to show

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            value = self.editor.settings.get(option)
            if value is not None:
                # For boolean options, show with "no" prefix if False
                if isinstance(value, bool):
                    if value:
                        self.editor.set_status_message(f"{option}")
                    else:
                        self.editor.set_status_message(f"no{option}")
                else:
                    self.editor.set_status_message(f"{option}={value}")
                return True
            else:
                self.editor.set_status_message(f"Unknown option: {option}")
                return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_source(self, path: str) -> bool:
        """
        Handle the source command (:source path).

        Args:
            path: Path to settings file to load

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            # Expand tilde and environment variables
            path = os.path.expandvars(os.path.expanduser(path))
            
            if self.editor.settings.load(path):
                self.editor.set_status_message(f"Sourced {path}")
                # Apply all settings
                self._apply_all_settings()
                return True
            else:
                self.editor.set_status_message(f"Error sourcing {path}")
                return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _cmd_source_default(self) -> bool:
        """
        Handle the source command without path (:source).
        Reloads the default config file.

        Returns:
            True if successful, False otherwise
        """
        if hasattr(self.editor, 'settings'):
            if self.editor.settings.load():
                self.editor.set_status_message("Reloaded settings")
                # Apply all settings
                self._apply_all_settings()
                return True
            else:
                self.editor.set_status_message("Error reloading settings")
                return False
        else:
            self.editor.set_status_message("Settings system not initialized")
            return False
    
    def _apply_setting(self, option: str, value: Any) -> None:
        """
        Apply a setting to the editor immediately.

        Args:
            option: Setting name
            value: Setting value
        """
        self.editor.ai_service.settings=self.editor.settings
        self.editor.ai_service.ai_timeout=self.editor.settings.ai.timeout
        self.editor.ai_service.current_openai_model=self.editor.settings.ai.openai_model
        self.editor.ai_service.current_anthropic_model=self.editor.settings.ai.anthropic_model
        for tab in self.editor.tabs:tab.history.max_history=self.editor.settings.file.undolevels
        # Map settings to editor properties/methods
        if option == "number" or option == "relativenumber":
            # Trigger display refresh
            if hasattr(self.editor, 'display') and self.editor.display:
                self.editor.display.refresh = True
        elif option == "cursorline" or option == "cursorcolumn":
            # Trigger display refresh
            if hasattr(self.editor, 'display') and self.editor.display:
                self.editor.display.refresh = True
        elif option in ["ignorecase", "smartcase", "hlsearch", "incsearch"]:
            # Update search settings
            if option == "hlsearch":
                self.editor.search_highlighting = value
            # Other search settings are handled dynamically during search
        elif option == "default_model":
            # Update AI model
            if hasattr(self.editor, 'set_ai_model'):
                self.editor.set_ai_model(value)
        elif option == "nlp_live_mode":
            # Update NLP live mode
            if hasattr(self.editor, 'nlp_handler') and self.editor.nlp_handler:
                self.editor.nlp_handler.live_mode_enabled = value
    
    def _apply_all_settings(self) -> None:
        """
        Apply all current settings to the editor.
        """
        if not hasattr(self.editor, 'settings'):
            return
        
        self._apply_setting("",None)
        # Apply display settings
        if hasattr(self.editor, 'display') and self.editor.display:
            self.editor.display.refresh = True
        
        # Apply search settings
        self.editor.search_highlighting = self.editor.settings.search.hlsearch
        
        # Apply AI settings
        if hasattr(self.editor, 'set_ai_model'):
            self.editor.set_ai_model(self.editor.settings.ai.default_model)
    
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
            if model_name.lower() in ["openai", "claude", "local", "olares", "compatible"]:
                self.editor.set_ai_model(model_name.lower())
                return True
            else:
                self.editor.set_status_message(f"Unknown model: {model_name}. Valid options: openai, claude, local, olares, compatible")
                return False
        except Exception as e:
            self.editor.set_status_message(f"Error setting AI model: {str(e)}")
            return False
            

    def _cmd_confirm_yes(self):
        return self.editor.confirm_ai_action(True,copy=True)
            
    def _cmd_confirm_no(self):
        return self.editor.confirm_ai_action(False)
    
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
            "  :model name    - Set AI model directly (openai, claude, local, olares)",
            "  :set model     - Legacy command to set AI model (openai, claude, local, olares)",
            "  :y             - Create a new tab with AI improved code",
            "  :n             - Reject AI suggestion",
            "",
            "NLP Mode:",
            "  :nlp           - Enter Natural Language Programming mode",
            "  nl (in normal) - Enter NLP mode (press 'n' then 'l')",
            "  :nlpmark s e   - Mark lines s through e as NLP section",
            "  :nlptranslate  - Force translation of NLP sections",
            "  :nlplive       - Toggle NLP Live Mode (auto-detect natural language)",
            "  #nlp <query>   - Single line AI query",
            "  #nlp           - Mark lines for multi-line AI query (multiple #nlp marks can be scattered in file)",
            "  Ctrl+Enter     - In NLP mode, sends entire script with context to AI",
            "  F9             - Force immediate submission of NLP content",
            "",
            "Debug Mode:",
            "  :debug         - Toggle debug mode (logs AI calls to file)",
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
    
    def _cmd_edit_current(self) -> bool:
        """
        Handle the edit command without filename (:e).
        Reloads the current file from disk.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.editor.filename:
            self.editor.set_status_message("No file to reload")
            return False
            
        if self.editor.buffer.is_modified():
            self.editor.set_status_message("File has unsaved changes (use :e! to force)")
            return False
            
        try:
            self.editor.reload_file()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error reloading file: {str(e)}")
            return False
    
    def _cmd_edit(self, filename: str) -> bool:
        """
        Handle the edit command with filename (:e filename).
        Opens the specified file in the current tab.
        
        Args:
            filename: File to open
            
        Returns:
            True if successful, False otherwise
        """
        if self.editor.buffer.is_modified():
            self.editor.set_status_message("Current buffer has unsaved changes (use :e! to force)")
            return False
            
        try:
            # Expand path (handle ~, etc.)
            filename = os.path.expanduser(filename)
            
            # Check if file is binary
            if self.editor.is_binary_file(filename):
                self.editor.set_status_message(f"Cannot edit binary file: {filename}")
                return False
            
            self.editor.load_file_with_permissions_check(filename)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error opening file: {str(e)}")
            return False
    
    def _cmd_force_edit_current(self) -> bool:
        """
        Handle the force edit command without filename (:e!).
        Force reloads the current file from disk, discarding changes.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.editor.filename:
            self.editor.set_status_message("No file to reload")
            return False
            
        try:
            self.editor.reload_file(force=True)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error reloading file: {str(e)}")
            return False
    
    def _cmd_force_edit(self, filename: str) -> bool:
        """
        Handle the force edit command with filename (:e! filename).
        Force opens the specified file, discarding current changes.
        
        Args:
            filename: File to open
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Expand path (handle ~, etc.)
            filename = os.path.expanduser(filename)
            
            # Check if file is binary
            if self.editor.is_binary_file(filename):
                self.editor.set_status_message(f"Cannot edit binary file: {filename}")
                return False
            
            self.editor.load_file_with_permissions_check(filename, force=True)
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error opening file: {str(e)}")
            return False
    
    def _cmd_new_buffer(self) -> bool:
        """
        Handle the new buffer command (:new).
        Creates a new empty buffer in a new tab.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            index = self.editor.create_tab("Untitled")
            self.editor.switch_to_tab(index)
            self.editor.set_status_message("Created new buffer")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error creating new buffer: {str(e)}")
            return False
    
    def _cmd_new_buffer_named(self, name: str) -> bool:
        """
        Handle the new buffer command with name (:new name).
        Creates a new empty buffer in a new tab with the specified name.
        
        Args:
            name: Name for the new buffer/tab
            
        Returns:
            True if successful, False otherwise
        """
        try:
            index = self.editor.create_tab(name)
            self.editor.switch_to_tab(index)
            self.editor.set_status_message(f"Created new buffer: {name}")
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error creating new buffer: {str(e)}")
            return False
    
    def _cmd_save_as(self, filename):
        return bool(self.editor.save_file(os.path.expanduser(filename)))
    
    def _cmd_browse_files(self) -> bool:
        """
        Handle the browse command (:browse).
        Opens the file browser/explorer.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.open_file_browser()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error opening file browser: {str(e)}")
            return False
        
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
            
    def _cmd_translate_nlp(self):
        if not self.editor.nlp_handler:
            from .nlp_mode import NLPHandler
            self.editor.nlp_handler=NLPHandler(self.editor)
        return self.editor.nlp_handler.force_submit()
    
    def _cmd_toggle_nlp_live_mode(self) -> bool:
        """
        Handle the command to toggle NLP live mode (:nlplive).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure we're in NLP mode
            if self.editor.mode != "NLP":
                self.editor.set_status_message("NLP Live Mode can only be toggled while in NLP mode")
                return False
                
            # Make sure NLP handler is initialized
            if not self.editor.nlp_handler:
                from aivim.nlp_mode import NLPHandler
                self.editor.nlp_handler = NLPHandler(self.editor)
                
            # Toggle live mode
            self.editor.nlp_handler.toggle_live_mode()
            return True
            
        except Exception as e:
            self.editor.set_status_message(f"Error toggling NLP live mode: {str(e)}")
            logging.error("command_handler operation failed")
            return False
            
    def _cmd_toggle_debug_mode(self) -> bool:
        """
        Handle the command to toggle debug mode (:debug).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.editor.ai_service:
                status_msg = self.editor.ai_service.toggle_debug_mode()
                self.editor.set_status_message(status_msg)
                return True
            else:
                self.editor.set_status_message("AI service not available")
                return False
                
        except Exception as e:
            self.editor.set_status_message(f"Error toggling debug mode: {str(e)}")
            logging.error("command_handler operation failed")
            return False
    
    def _cmd_no_highlight(self) -> bool:
        """
        Handle the no highlight command (:noh or :nohlsearch).
        Clears search highlighting.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.editor.clear_search_highlights()
            return True
        except Exception as e:
            self.editor.set_status_message(f"Error clearing highlights: {str(e)}")
            return False
    
    def _cmd_substitute_current(self, pattern: str, replacement: str, flags: str) -> bool:
        """
        Handle substitution on current line (:s/pattern/replacement/flags).
        
        Args:
            pattern: The search pattern
            replacement: The replacement text
            flags: Optional flags (g, c, gc)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            global_flag = 'g' in flags
            confirm = 'c' in flags
            
            count = self.editor.substitute(pattern, replacement, 
                                          line_range=None,
                                          global_flag=global_flag,
                                          confirm=confirm)
            return count > 0 or pattern == ""
        except Exception as e:
            self.editor.set_status_message(f"Error in substitution: {str(e)}")
            return False
    
    def _cmd_substitute_all(self, pattern: str, replacement: str, flags: str) -> bool:
        """
        Handle substitution on all lines (:%s/pattern/replacement/flags).
        
        Args:
            pattern: The search pattern
            replacement: The replacement text
            flags: Optional flags (g, c, gc)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            global_flag = 'g' in flags
            confirm = 'c' in flags
            
            # Get total line count
            total_lines = len(self.editor.buffer.get_lines())
            line_range = (0, total_lines - 1) if total_lines > 0 else (0, 0)
            
            count = self.editor.substitute(pattern, replacement,
                                          line_range=line_range,
                                          global_flag=global_flag,
                                          confirm=confirm)
            return count > 0 or pattern == ""
        except Exception as e:
            self.editor.set_status_message(f"Error in substitution: {str(e)}")
            return False
    
    def _cmd_substitute_range(self, start_line: str, end_line: str, 
                              pattern: str, replacement: str, flags: str) -> bool:
        """
        Handle substitution on line range (:start,end s/pattern/replacement/flags).
        
        Args:
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)
            pattern: The search pattern
            replacement: The replacement text
            flags: Optional flags (g, c, gc)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to 0-based indexing
            start = int(start_line) - 1
            end = int(end_line) - 1
            
            global_flag = 'g' in flags
            confirm = 'c' in flags
            
            count = self.editor.substitute(pattern, replacement,
                                          line_range=(start, end),
                                          global_flag=global_flag,
                                          confirm=confirm)
            return count > 0 or pattern == ""
        except Exception as e:
            self.editor.set_status_message(f"Error in substitution: {str(e)}")
            return False
    
    def _cmd_substitute_visual(self, pattern: str, replacement: str, flags: str) -> bool:
        """
        Handle substitution on visual selection (:'<,'>s/pattern/replacement/flags).
        
        Args:
            pattern: The search pattern
            replacement: The replacement text
            flags: Optional flags (g, c, gc)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get visual selection range
            if hasattr(self.editor.buffer, 'selection_start') and hasattr(self.editor.buffer, 'selection_end'):
                start_y = self.editor.buffer.selection_start[0]
                end_y = self.editor.buffer.selection_end[0]
                
                # Ensure correct order
                if start_y > end_y:
                    start_y, end_y = end_y, start_y
                
                global_flag = 'g' in flags
                confirm = 'c' in flags
                
                count = self.editor.substitute(pattern, replacement,
                                              line_range=(start_y, end_y),
                                              global_flag=global_flag,
                                              confirm=confirm)
                return count > 0 or pattern == ""
            else:
                self.editor.set_status_message("No visual selection")
                return False
        except Exception as e:
            self.editor.set_status_message(f"Error in substitution: {str(e)}")
            return False


    def _cmd_nlp_context(self,value):
        from .nlp_mode import NLPHandler
        if not self.editor.nlp_handler:self.editor.nlp_handler=NLPHandler(self.editor)
        try:
            indices=[] if value=='none' else [int(x)-1 for x in value.split(',')]
            if any(i<0 or i>=len(self.editor.tabs) for i in indices):raise ValueError('Invalid context tab')
            self.editor.nlp_handler.select_context([self.editor.tabs[i].document_id for i in indices])
            self.editor.show_dialog('Context that will be transmitted',[str(c) for c in self.editor.nlp_handler.context_preview()]);return True
        except ValueError as exc:self.editor.set_status_message(str(exc));return False
