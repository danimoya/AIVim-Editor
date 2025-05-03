"""
Display handling for AIVim
"""
import curses
import time
import threading
from typing import List, Optional, Tuple, Dict, Any

from aivim.utils import split_diff_line


class Display:
    """
    Handles all display-related operations
    """
    def __init__(self, stdscr):
        """
        Initialize the display
        
        Args:
            stdscr: The curses standard screen
        """
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Colors
        curses.start_color()
        curses.use_default_colors()
        
        # Normal text
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        # Status line
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        # Message line
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Line numbers
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        # Selected text
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
        # Dialog
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Dialog title
        curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLUE)
        # Diff - added
        curses.init_pair(8, curses.COLOR_GREEN, -1)
        # Diff - removed
        curses.init_pair(9, curses.COLOR_RED, -1)
        # Diff - header
        curses.init_pair(10, curses.COLOR_MAGENTA, -1)
        
        # Define colors
        self.COLOR_NORMAL = curses.color_pair(1)
        self.COLOR_STATUS = curses.color_pair(2)
        self.COLOR_MESSAGE = curses.color_pair(3)
        self.COLOR_LINENO = curses.color_pair(4)
        self.COLOR_SELECTION = curses.color_pair(5)
        self.COLOR_DIALOG = curses.color_pair(6)
        self.COLOR_DIALOG_TITLE = curses.color_pair(7)
        self.COLOR_DIFF_ADDED = curses.color_pair(8)
        self.COLOR_DIFF_REMOVED = curses.color_pair(9)
        self.COLOR_DIFF_HEADER = curses.color_pair(10)
        
        # Line number gutter width
        self.gutter_width = 4
        
        # Calculate usable text area
        self.max_text_height = self.height - 2  # account for status and message lines
        self.max_text_width = self.width - self.gutter_width
        
        # Create windows
        self.text_win = curses.newwin(
            self.max_text_height, 
            self.width, 
            0, 
            0
        )
        self.status_win = curses.newwin(1, self.width, self.height - 2, 0)
        self.command_win = curses.newwin(1, self.width, self.height - 1, 0)
        
        # For dialog and dialog navigation
        self.dialog_win = None
        self.dialog_content = []
        self.dialog_views = []
        self.current_view_index = 0
        self.dialog_view_titles = []
        self.dialog_scroll_position = 0
        
        # Enable special keys
        self.stdscr.keypad(True)
        
        # Don't echo typed characters
        curses.noecho()
        
        # Don't wait for Enter
        curses.cbreak()
        
        # Hide cursor initially
        curses.curs_set(0)
        
        # Loading Animation
        self.loading_animation = None
        self.loading_message = ""
        self.loading_thread = None
        self.loading_stop_event = threading.Event()
        
        # Performance optimization message has been removed as requested
    
    def resize(self) -> None:
        """Handle terminal resize"""
        self.height, self.width = self.stdscr.getmaxyx()
        
        # Recalculate usable text area
        self.max_text_height = self.height - 2
        self.max_text_width = self.width - self.gutter_width
        
        # Resize windows
        self.text_win.resize(self.max_text_height, self.width)
        self.status_win.resize(1, self.width)
        self.status_win.mvwin(self.height - 2, 0)
        self.command_win.resize(1, self.width)
        self.command_win.mvwin(self.height - 1, 0)
        
        # If dialog is open, resize it too
        if self.dialog_win:
            self._setup_dialog_window()
    
    def update_text(self, lines: List[str], cursor_y: int, cursor_x: int, 
                    scroll_y: int, selection: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> None:
        """
        Update the text display
        
        Args:
            lines: Text lines to display
            cursor_y: Cursor y position (line number)
            cursor_x: Cursor x position (column)
            scroll_y: First visible line number
            selection: Optional tuple of ((start_y, start_x), (end_y, end_x)) for selection
        """
        if self.is_dialog_open():
            return
        
        # Store current state to determine if we need to redraw
        self._last_cursor_pos = getattr(self, '_last_cursor_pos', None)
        self._last_scroll_y = getattr(self, '_last_scroll_y', None)
        current_cursor_pos = (cursor_y, cursor_x)
        
        # Optimize: Only clear and redraw if something significant changed
        need_full_redraw = (
            self._last_cursor_pos != current_cursor_pos or
            self._last_scroll_y != scroll_y or
            not hasattr(self, '_has_drawn_initial_screen')
        )
        
        # Update saved state
        self._last_cursor_pos = current_cursor_pos
        self._last_scroll_y = scroll_y
        self._has_drawn_initial_screen = True
        
        if need_full_redraw:
            self.text_win.clear()
            self.text_win.bkgd(' ', self.COLOR_NORMAL)
        
        # Number of lines to display
        display_lines = min(self.max_text_height, len(lines) - scroll_y)
        
        # Process selection
        selection_start = None
        selection_end = None
        
        if selection and selection[0] and selection[1]:
            start_y, start_x = selection[0]
            end_y, end_x = selection[1]
            
            # Ensure start is before end
            if (start_y > end_y) or (start_y == end_y and start_x > end_x):
                start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
                
            selection_start = (start_y, start_x)
            selection_end = (end_y, end_x)
        
        # Get window dimensions to prevent writing outside the window
        max_y, max_x = self.text_win.getmaxyx()
        
        # Display lines
        for i in range(display_lines):
            line_num = scroll_y + i
            line = lines[line_num]
            
            # Check if we're at the bottom edge of the window
            if i >= max_y:
                break
                
            # Display line number
            gutter = f"{line_num+1:3d} "
            try:
                self.text_win.addstr(i, 0, gutter, self.COLOR_LINENO)
            except curses.error:
                # Skip if we can't write the line number (shouldn't happen)
                continue
            
            # Calculate available width for text (don't draw past edge)
            available_width = max_x - self.gutter_width - 1  # Leave 1 char margin
            
            # If the line is too long, truncate it
            display_line = line
            if len(display_line) > available_width:
                display_line = display_line[:available_width]
            
            # Handle displaying line content with or without selection
            # Each section has its own try/except to handle potential curses errors safely
            if not selection_start or not selection_end:
                # No selection, simple display
                try:
                    self.text_win.addstr(i, self.gutter_width, display_line)
                except curses.error:
                    pass
            else:
                # With selection - determine which case applies
                if line_num < selection_start[0] or line_num > selection_end[0]:
                    # Line is outside selection
                    try:
                        self.text_win.addstr(i, self.gutter_width, display_line)
                    except curses.error:
                        pass
                        
                elif line_num == selection_start[0] and line_num == selection_end[0]:
                    # Selection starts and ends on this line
                    try:
                        # Calculate safe bounds
                        sel_start = min(selection_start[1], len(display_line))
                        sel_end = min(selection_end[1], len(display_line))
                        
                        # Display pre-selection segment
                        if sel_start > 0:
                            self.text_win.addstr(i, self.gutter_width, display_line[:sel_start])
                        
                        # Display selected segment
                        selected_text = display_line[sel_start:sel_end]
                        if selected_text:
                            self.text_win.addstr(i, self.gutter_width + sel_start, 
                                               selected_text, self.COLOR_SELECTION)
                        
                        # Display post-selection segment
                        if sel_end < len(display_line):
                            self.text_win.addstr(i, self.gutter_width + sel_end, 
                                               display_line[sel_end:])
                    except curses.error:
                        pass
                        
                elif line_num == selection_start[0]:
                    # Selection starts on this line
                    try:
                        sel_start = min(selection_start[1], len(display_line))
                        
                        # Display pre-selection segment
                        if sel_start > 0:
                            self.text_win.addstr(i, self.gutter_width, display_line[:sel_start])
                        
                        # Display selected segment
                        if sel_start < len(display_line):
                            self.text_win.addstr(i, self.gutter_width + sel_start, 
                                               display_line[sel_start:], self.COLOR_SELECTION)
                    except curses.error:
                        pass
                        
                elif line_num == selection_end[0]:
                    # Selection ends on this line
                    try:
                        sel_end = min(selection_end[1], len(display_line))
                        
                        # Display selected segment
                        if sel_end > 0:
                            self.text_win.addstr(i, self.gutter_width, display_line[:sel_end], 
                                               self.COLOR_SELECTION)
                        
                        # Display post-selection segment
                        if sel_end < len(display_line):
                            self.text_win.addstr(i, self.gutter_width + sel_end, 
                                               display_line[sel_end:])
                    except curses.error:
                        pass
                        
                else:
                    # Line is fully selected
                    try:
                        self.text_win.addstr(i, self.gutter_width, display_line, self.COLOR_SELECTION)
                    except curses.error:
                        pass
        
        # Position cursor
        if cursor_y >= scroll_y and cursor_y < scroll_y + self.max_text_height:
            curses.curs_set(1)  # Show cursor
            self.text_win.move(cursor_y - scroll_y, self.gutter_width + cursor_x)
        else:
            curses.curs_set(0)  # Hide cursor
        
        # Refresh display
        self.text_win.refresh()
    
    def update_status(self, status: str) -> None:
        """
        Update status line
        
        Args:
            status: Status text
        """
        self.status_win.clear()
        self.status_win.bkgd(' ', self.COLOR_STATUS)
        
        # Truncate status if too long
        if len(status) > self.width - 1:
            status = status[:self.width - 4] + "..."
        
        self.status_win.addstr(0, 0, status)
        self.status_win.move(0, min(len(status), self.width - 1))
        
        self.status_win.refresh()
    
    def update_mode(self, mode: str, model_info: Optional[str] = None) -> None:
        """
        Update the display to show the current mode and AI model
        
        Args:
            mode: Current editor mode
            model_info: Optional AI model information to display
        """
        # Add mode to the right side of the status line
        mode_text = f" {mode} "
        
        # Add AI model info if provided
        if model_info:
            # Format for improved display
            if "not configured" in model_info:
                model_text = f"[AI: {model_info}] "
            else:
                model_text = f"[AI: {model_info}] "
                
            # If in an AI-related mode, make it more prominent
            if mode in ["NLP"] or "AI" in mode:
                model_text = f"[AI: {model_info}] "
                
            # Position model info before the mode
            model_pos = self.width - len(mode_text) - len(model_text) - 1
            if model_pos > 0:  # Make sure we don't go out of bounds
                try:
                    # Use a different attribute to make it stand out
                    self.status_win.addstr(0, model_pos, model_text, curses.A_BOLD)
                except curses.error:
                    # Handle potential overflow
                    pass
        
        # Add mode
        try:
            self.status_win.addstr(0, self.width - len(mode_text) - 1, mode_text)
        except curses.error:
            # Handle potential overflow
            pass
            
        self.status_win.refresh()
    
    def update_command_line(self, command: str, cursor_pos: int) -> None:
        """
        Update command line
        
        Args:
            command: Command text
            cursor_pos: Cursor position in the command
        """
        self.command_win.clear()
        self.command_win.bkgd(' ', self.COLOR_MESSAGE)
        
        # Truncate command if too long
        if len(command) > self.width - 1:
            visible_start = max(0, cursor_pos - (self.width // 2))
            visible_end = min(len(command), visible_start + self.width - 1)
            visible_command = command[visible_start:visible_end]
            
            # Adjust cursor position for the visible portion
            cursor_pos -= visible_start
        else:
            visible_command = command
        
        self.command_win.addstr(0, 0, visible_command)
        self.command_win.move(0, min(cursor_pos, self.width - 1))
        
        self.command_win.refresh()
    
    def show_dialog(self, title: str, content: List[str]) -> None:
        """
        Show a dialog box
        
        Args:
            title: Dialog title
            content: List of content lines
        """
        self.dialog_content = content
        self.dialog_views = [content]
        self.dialog_view_titles = [title]
        self.current_view_index = 0
        self.dialog_scroll_position = 0
        self._setup_dialog_window()
        self._draw_dialog(title)
        
    def add_dialog_view(self, title: str, content: List[str]) -> None:
        """
        Add an additional view to the current dialog
        
        Args:
            title: View title
            content: View content lines
        """
        if not self.is_dialog_open():
            # If no dialog is open, just show as a new dialog
            self.show_dialog(title, content)
            return
            
        self.dialog_views.append(content)
        self.dialog_view_titles.append(title)
        
    def next_dialog_view(self) -> None:
        """Switch to the next dialog view if multiple views exist"""
        if not self.is_dialog_open() or len(self.dialog_views) <= 1:
            return
            
        self.current_view_index = (self.current_view_index + 1) % len(self.dialog_views)
        self.dialog_content = self.dialog_views[self.current_view_index]
        self.dialog_scroll_position = 0
        self._draw_dialog(self.dialog_view_titles[self.current_view_index])
        
    def prev_dialog_view(self) -> None:
        """Switch to the previous dialog view if multiple views exist"""
        if not self.is_dialog_open() or len(self.dialog_views) <= 1:
            return
            
        self.current_view_index = (self.current_view_index - 1) % len(self.dialog_views)
        self.dialog_content = self.dialog_views[self.current_view_index]
        self.dialog_scroll_position = 0
        self._draw_dialog(self.dialog_view_titles[self.current_view_index])
    
    def _setup_dialog_window(self) -> None:
        """Set up the dialog window dimensions"""
        # Calculate dialog dimensions
        dialog_height = min(len(self.dialog_content) + 4, self.height - 4)
        dialog_width = min(max(max(len(line) for line in self.dialog_content) + 4, len("Press 'd' to close") + 4, 40), 
                          self.width - 4)
        
        # Center the dialog
        dialog_y = (self.height - dialog_height) // 2
        dialog_x = (self.width - dialog_width) // 2
        
        # Create or resize the dialog window
        if self.dialog_win:
            self.dialog_win.resize(dialog_height, dialog_width)
            self.dialog_win.mvwin(dialog_y, dialog_x)
        else:
            self.dialog_win = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
    
    def _draw_dialog(self, title: str) -> None:
        """Draw the dialog content"""
        self.dialog_win.clear()
        self.dialog_win.bkgd(' ', self.COLOR_DIALOG)
        
        # Draw border
        self.dialog_win.box()
        
        # Draw title
        title = f" {title} "
        title_x = (self.dialog_win.getmaxyx()[1] - len(title)) // 2
        self.dialog_win.addstr(0, title_x, title, self.COLOR_DIALOG_TITLE)
        
        # Draw view navigation indicators if multiple views
        if len(self.dialog_views) > 1:
            # Display current view indicator
            view_indicator = f"View {self.current_view_index + 1}/{len(self.dialog_views)}"
            self.dialog_win.addstr(0, 2, view_indicator)
            
            # Display navigation hint
            nav_hint = "Use Ctrl+Left/Right to navigate views"
            self.dialog_win.addstr(0, self.dialog_win.getmaxyx()[1] - len(nav_hint) - 2, nav_hint)
        
        # Draw content
        max_content_width = self.dialog_win.getmaxyx()[1] - 4
        visible_lines = min(len(self.dialog_content), self.dialog_win.getmaxyx()[0] - 4)
        
        for i in range(visible_lines):
            line = self.dialog_content[i]
            if len(line) > max_content_width:
                line = line[:max_content_width-3] + "..."
            self.dialog_win.addstr(i + 1, 2, line)
        
        # Draw close instruction
        close_text = "Press 'd' to close"
        self.dialog_win.addstr(self.dialog_win.getmaxyx()[0] - 2, 
                             (self.dialog_win.getmaxyx()[1] - len(close_text)) // 2,
                             close_text)
        
        self.dialog_win.refresh()
    
    def close_dialog(self) -> None:
        """Close the dialog"""
        self.dialog_win = None
        self.dialog_content = []
        self.dialog_views = []
        self.dialog_view_titles = []
        self.current_view_index = 0
        self.dialog_scroll_position = 0
        
        # Refresh main windows
        self.stdscr.touchwin()
        self.stdscr.refresh()
        self.text_win.touchwin()
        self.text_win.refresh()
        self.status_win.touchwin()
        self.status_win.refresh()
        self.command_win.touchwin()
        self.command_win.refresh()
    
    def is_dialog_open(self) -> bool:
        """Check if a dialog is currently open"""
        return self.dialog_win is not None
    
    def show_model_selector(self, current_model: str, callback, ai_service=None) -> None:
        """
        Show a dialog with selectable model options
        
        Args:
            current_model: Currently selected model
            callback: Function to call with the selected model
            ai_service: Optional AI service instance for submodel information
        """
        # Create model options
        models = [
            {"id": "openai", "name": "OpenAI", "description": "GPT-4o: The latest OpenAI model"},
            {"id": "claude", "name": "Claude", "description": "Claude 3.5 Sonnet: Anthropic's newest model"},
            {"id": "local", "name": "Local", "description": "Run local LLMs through llama-cpp-python"}
        ]
        
        # Highlight the current model
        for model in models:
            if model["id"] == current_model:
                model["name"] = f"● {model['name']} (current)"
                # Add submodels if available
                if ai_service and hasattr(ai_service, 'get_available_submodels'):
                    submodels = ai_service.get_available_submodels(model["id"])
                    model["submodels"] = submodels
        
        self.dialog_title = "AI Model Selector"
        self.dialog_content = []
        self.dialog_options = models
        self.selected_index = 0
        self.in_submodel_selection = False
        self.submodel_offset = 0  # Used to track where submodels start in dialog content
        self.submodel_count = 0   # Number of submodels for the selected provider
        self.selected_submodel_index = 0  # Currently selected submodel index
        self.ai_service = ai_service  # Store the AI service reference
        
        # Find index of current model
        for i, model in enumerate(models):
            if model["id"] == current_model:
                self.selected_index = i
                break
        
        # Build content
        for i, model in enumerate(models):
            if i == self.selected_index:
                self.dialog_content.append(f"→ {model['name']}")
            else:
                self.dialog_content.append(f"  {model['name']}")
            
            if model.get("description"):
                self.dialog_content.append(f"    {model['description']}")
            
            # Add a blank line between options
            if i < len(models) - 1:
                self.dialog_content.append("")
        
        # Add instructions
        self.dialog_content.append("")
        self.dialog_content.append("Use ↑/↓ to select, Enter to choose provider or configure submodel")
        self.dialog_content.append("Press Tab to toggle between providers and submodels, Esc to cancel")
        
        # Calculate dialog dimensions
        dialog_height = min(len(self.dialog_content) + 6, self.height - 4)  # Larger to accommodate submodels
        dialog_width = min(max(max(len(line) for line in self.dialog_content) + 4, 60), self.width - 4)
        
        # Center the dialog
        dialog_y = (self.height - dialog_height) // 2
        dialog_x = (self.width - dialog_width) // 2
        
        # Create dialog window
        self.dialog_win = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        self.dialog_win.keypad(True)  # Enable keypad for navigation
        
        # Store callback
        self.model_callback = callback
        
        # Draw the selector
        self._draw_model_selector()
    
    def _draw_model_selector(self) -> None:
        """Draw the model selector dialog"""
        if not self.dialog_win:
            return
        
        self.dialog_win.clear()
        self.dialog_win.bkgd(' ', self.COLOR_DIALOG)
        
        # Draw border
        self.dialog_win.box()
        
        # Draw title
        title = f" {self.dialog_title} "
        title_x = (self.dialog_win.getmaxyx()[1] - len(title)) // 2
        self.dialog_win.addstr(0, title_x, title, self.COLOR_DIALOG_TITLE)
        
        # Draw content
        max_content_width = self.dialog_win.getmaxyx()[1] - 4
        visible_lines = min(len(self.dialog_content), self.dialog_win.getmaxyx()[0] - 2)
        
        for i in range(visible_lines):
            if i >= len(self.dialog_content):
                break
                
            line = self.dialog_content[i]
            if len(line) > max_content_width:
                line = line[:max_content_width-3] + "..."
            
            # If this is a model line (starts with → or spaces followed by a non-space)
            if line.startswith("→ ") or (line.startswith("  ") and len(line) > 2 and line[2] != " "):
                # Bold for model names
                self.dialog_win.addstr(i + 1, 2, line, curses.A_BOLD)
            else:
                # Normal for descriptions and other text
                self.dialog_win.addstr(i + 1, 2, line)
        
        self.dialog_win.refresh()
    
    def process_model_selector_keypress(self, key: int) -> Optional[str]:
        """
        Process keypress in the model selector
        
        Args:
            key: Key code
            
        Returns:
            Selected model ID or None if cancelled
        """
        if key in [27, ord('q')]:  # ESC or 'q'
            if self.in_submodel_selection:
                # Return to main model selection
                self._exit_submodel_selection()
                return None
            else:
                # Close the dialog completely
                self.close_dialog()
                return None
            
        elif key == 9:  # Tab key to toggle between providers and submodels
            if self.in_submodel_selection:
                # Exit submodel selection mode
                self._exit_submodel_selection()
                return None
            else:
                # Enter submodel selection mode if the current model has submodels
                selected_model = self.dialog_options[self.selected_index]
                if "submodels" in selected_model and len(selected_model["submodels"]) > 0:
                    self._enter_submodel_selection(selected_model)
                    return None
                
        elif key == curses.KEY_UP:
            if self.in_submodel_selection:
                # Navigate among submodels
                if self.selected_submodel_index > 0:
                    self.selected_submodel_index -= 1
                    self._update_submodel_selection()
            else:
                # Navigate among main model providers
                # Get the number of model options
                num_models = len(self.dialog_options)
                if self.selected_index > 0:
                    self.selected_index -= 1
                    
                    # Update content with new selection
                    content_idx = 0
                    for i, model in enumerate(self.dialog_options):
                        # Update the arrow for the selected item
                        if i == self.selected_index:
                            self.dialog_content[content_idx] = f"→ {model['name']}"
                        else:
                            self.dialog_content[content_idx] = f"  {model['name']}"
                        
                        # Skip description and blank line
                        content_idx += 1
                        if "description" in model:
                            content_idx += 1
                        if i < num_models - 1:
                            content_idx += 1
                    
                    self._draw_model_selector()
                
        elif key == curses.KEY_DOWN:
            if self.in_submodel_selection:
                # Navigate among submodels
                selected_model = self.dialog_options[self.selected_index]
                if "submodels" in selected_model and self.selected_submodel_index < len(selected_model["submodels"]) - 1:
                    self.selected_submodel_index += 1
                    self._update_submodel_selection()
            else:
                # Navigate among main model providers
                # Get the number of model options
                num_models = len(self.dialog_options)
                if self.selected_index < num_models - 1:
                    self.selected_index += 1
                    
                    # Update content with new selection
                    content_idx = 0
                    for i, model in enumerate(self.dialog_options):
                        # Update the arrow for the selected item
                        if i == self.selected_index:
                            self.dialog_content[content_idx] = f"→ {model['name']}"
                        else:
                            self.dialog_content[content_idx] = f"  {model['name']}"
                        
                        # Skip description and blank line
                        content_idx += 1
                        if "description" in model:
                            content_idx += 1
                        if i < num_models - 1:
                            content_idx += 1
                    
                    self._draw_model_selector()
                
        elif key in [10, curses.KEY_ENTER]:  # Enter key
            if self.in_submodel_selection:
                # Select a specific submodel
                selected_provider = self.dialog_options[self.selected_index]
                selected_submodel = selected_provider["submodels"][self.selected_submodel_index]
                
                # Call the callback to set the provider and then set the submodel
                if self.model_callback and self.ai_service:
                    # First set the main model provider
                    self.model_callback(selected_provider["id"])
                    
                    # Then set the specific submodel
                    self.ai_service.set_submodel(selected_provider["id"], selected_submodel["id"])
                    
                    # Close the dialog
                    self.close_dialog()
                    return selected_provider["id"]
            else:
                # Check if the selected model has submodels
                selected_model = self.dialog_options[self.selected_index]
                if "submodels" in selected_model and len(selected_model["submodels"]) > 0:
                    # Enter submodel selection instead of immediately selecting this provider
                    self._enter_submodel_selection(selected_model)
                    return None
                else:
                    # No submodels, just select the provider directly
                    selected_provider_id = selected_model["id"]
                    if self.model_callback:
                        self.model_callback(selected_provider_id)
                    self.close_dialog()
                    return selected_provider_id
            
        return None
        
    def _enter_submodel_selection(self, selected_model):
        """
        Enter submodel selection mode
        
        Args:
            selected_model: The selected provider model with submodels
        """
        self.in_submodel_selection = True
        self.selected_submodel_index = 0
        
        # Remember original content to restore later
        self.original_content = self.dialog_content.copy()
        self.dialog_title = f"Select {selected_model['name'].replace('●', '').strip()} Model"
        
        # Create new content with just submodels
        self.dialog_content = []
        submodels = selected_model.get("submodels", [])
        
        for i, submodel in enumerate(submodels):
            if i == self.selected_submodel_index:
                self.dialog_content.append(f"→ {submodel['name']}")
            else:
                self.dialog_content.append(f"  {submodel['name']}")
                
            if submodel.get("description"):
                self.dialog_content.append(f"    {submodel['description']}")
                
            # Add blank line between models
            if i < len(submodels) - 1:
                self.dialog_content.append("")
                
        # Add instructions
        self.dialog_content.append("")
        self.dialog_content.append("Use ↑/↓ to select, Enter to set model, Tab/Esc to go back")
        
        # Redraw the dialog
        self._draw_model_selector()
        
    def _exit_submodel_selection(self):
        """Exit submodel selection mode"""
        self.in_submodel_selection = False
        self.selected_submodel_index = 0
        
        # Restore original content
        if hasattr(self, 'original_content'):
            self.dialog_content = self.original_content
            
        # Restore original title
        self.dialog_title = "AI Model Selector"
        
        # Redraw the dialog
        self._draw_model_selector()
        
    def _update_submodel_selection(self):
        """Update the submodel selection"""
        if not self.in_submodel_selection:
            return
        
        selected_model = self.dialog_options[self.selected_index]
        submodels = selected_model.get("submodels", [])
        
        if not submodels:
            return
            
        # Update dialog content with new selection
        content_idx = 0
        for i, submodel in enumerate(submodels):
            if i == self.selected_submodel_index:
                self.dialog_content[content_idx] = f"→ {submodel['name']}"
            else:
                self.dialog_content[content_idx] = f"  {submodel['name']}"
                
            # Skip description and blank line
            content_idx += 1
            if "description" in submodel:
                content_idx += 1
            if i < len(submodels) - 1:
                content_idx += 1
                
        # Redraw the dialog
        self._draw_model_selector()
        
    def show_multi_view_dialog(self, views: List[Dict[str, Any]], explanation: Optional[List[str]] = None, default_view: int = 0) -> None:
        """
        Show a multi-view dialog with different content in each view
        
        Args:
            views: List of view dictionaries with 'title' and 'content' keys
            explanation: Optional explanation to add as an additional view
            default_view: Index of the view to show initially (default is 0)
        """
        self.dialog_views = []
        self.dialog_view_titles = []
        
        # Process the diff view specially (it needs colorizing)
        diff_view_index = None
        diff_colorized_content = None
        
        # Add all the views
        for i, view in enumerate(views):
            title = view.get('title', f"View {i+1}")
            content = view.get('content', [])
            
            # Check if this is a diff view that needs special handling
            if "diff" in title.lower():
                diff_view_index = i
                # Convert diff lines to colorized format for display
                colorized_content = []
                for line in content:
                    diff_type, line_content = split_diff_line(line)
                    colorized_content.append((diff_type, line_content))
                
                self.dialog_views.append([content for _, content in colorized_content])
                diff_colorized_content = colorized_content
            else:
                self.dialog_views.append(content)
            
            self.dialog_view_titles.append(title)
        
        # Add explanation as a separate view if provided
        if explanation and len(explanation) > 0:
            self.dialog_views.append(explanation)
            self.dialog_view_titles.append("Explanation")
        
        # Set the current view
        self.current_view_index = min(default_view, len(self.dialog_views) - 1) if self.dialog_views else 0
        self.dialog_content = self.dialog_views[self.current_view_index] if self.dialog_views else []
        self.dialog_scroll_position = 0
        
        # Setup and draw the dialog
        self._setup_dialog_window()
        
        # Check if the current view is the diff view
        if diff_view_index is not None and self.current_view_index == diff_view_index:
            self._draw_diff_dialog(self.dialog_view_titles[self.current_view_index], diff_colorized_content)
        else:
            self._draw_dialog(self.dialog_view_titles[self.current_view_index])
    
    def show_diff_dialog(self, title: str, diff_lines: List[str], explanation: Optional[List[str]] = None) -> None:
        """
        Show a dialog box with diff content and optionally an explanation in separate views
        
        Args:
            title: Dialog title
            diff_lines: List of formatted diff lines (from utils.create_diff)
            explanation: Optional explanation of the changes to show in a separate view
        """
        views = [{"title": title, "content": diff_lines}]
        default_view = 0
        
        # Use the new multi-view dialog method
        self.show_multi_view_dialog(views, explanation, default_view)
        
    def show_confirmation_dialog(self, title: str, message: List[str]) -> bool:
        """
        Show a confirmation dialog that requires user response (y/n)
        
        Args:
            title: Dialog title
            message: List of message lines
            
        Returns:
            True if user confirmed (pressed 'y'), False otherwise
        """
        # Set up dialog
        self.dialog_content = message + ["", "Press 'y' to confirm or 'n' to cancel"]
        self._setup_dialog_window()
        
        # Draw dialog with special footer
        self.dialog_win.clear()
        self.dialog_win.bkgd(' ', self.COLOR_DIALOG)
        
        # Draw border
        self.dialog_win.box()
        
        # Draw title
        title_str = f" {title} "
        title_x = (self.dialog_win.getmaxyx()[1] - len(title_str)) // 2
        self.dialog_win.addstr(0, title_x, title_str, self.COLOR_DIALOG_TITLE)
        
        # Draw content
        max_content_width = self.dialog_win.getmaxyx()[1] - 4
        visible_lines = min(len(self.dialog_content), self.dialog_win.getmaxyx()[0] - 4)
        
        for i in range(visible_lines):
            line = self.dialog_content[i]
            if len(line) > max_content_width:
                line = line[:max_content_width-3] + "..."
            self.dialog_win.addstr(i + 1, 2, line)
        
        self.dialog_win.refresh()
        
        # Wait for y/n response
        while True:
            key = self.stdscr.getch()
            if key in (ord('y'), ord('Y')):
                self.close_dialog()
                return True
            elif key in (ord('n'), ord('N')):
                self.close_dialog()
                return False
    
    def _draw_diff_dialog(self, title: str, colorized_content: Optional[List[Tuple[str, str]]]) -> None:
        """
        Draw the dialog with diff content
        
        Args:
            title: Dialog title
            colorized_content: List of (diff_type, content) tuples or None
        """
        if colorized_content is None:
            # If no content is provided, fall back to regular dialog
            self._draw_dialog(title)
            return
        self.dialog_win.clear()
        self.dialog_win.bkgd(' ', self.COLOR_DIALOG)
        
        # Draw border
        self.dialog_win.box()
        
        # Draw title
        title = f" {title} "
        title_x = (self.dialog_win.getmaxyx()[1] - len(title)) // 2
        self.dialog_win.addstr(0, title_x, title, self.COLOR_DIALOG_TITLE)
        
        # Draw view navigation indicators if multiple views
        if len(self.dialog_views) > 1:
            # Display current view indicator
            view_indicator = f"View {self.current_view_index + 1}/{len(self.dialog_views)}"
            self.dialog_win.addstr(0, 2, view_indicator)
            
            # Display navigation hint
            nav_hint = "Use Ctrl+Left/Right to navigate views"
            self.dialog_win.addstr(0, self.dialog_win.getmaxyx()[1] - len(nav_hint) - 2, nav_hint)
        
        # Draw content
        max_content_width = self.dialog_win.getmaxyx()[1] - 4
        visible_lines = min(len(colorized_content), self.dialog_win.getmaxyx()[0] - 4)
        
        for i in range(visible_lines):
            diff_type, line = colorized_content[i]
            
            # Truncate if needed
            if len(line) > max_content_width:
                line = line[:max_content_width-3] + "..."
            
            # Choose color based on diff type
            if diff_type == "ADDED":
                color = self.COLOR_DIFF_ADDED
            elif diff_type == "REMOVED":
                color = self.COLOR_DIFF_REMOVED
            elif diff_type == "HEADER":
                color = self.COLOR_DIFF_HEADER
            else:
                color = self.COLOR_NORMAL
                
            self.dialog_win.addstr(i + 1, 2, line, color)
        
        # Draw close instruction
        close_text = "Press 'd' to close"
        self.dialog_win.addstr(self.dialog_win.getmaxyx()[0] - 2, 
                            (self.dialog_win.getmaxyx()[1] - len(close_text)) // 2,
                            close_text)
        
        self.dialog_win.refresh()
        
    # Loading indicator methods
    def start_loading_animation(self, message: str) -> None:
        """
        Start an animated loading indicator in the status line
        
        Args:
            message: Status message to display alongside the animation
        """
        # Store the original message
        self._loading_base_message = message
        self._loading_active = True
        self._loading_frame = 0
        self._loading_frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']  # Spinner animation frames
        
        # Start the animation thread
        self._loading_thread = threading.Thread(target=self._animate_loading)
        self._loading_thread.daemon = True
        self._loading_thread.start()
    
    def stop_loading_animation(self) -> None:
        """Stop the loading animation"""
        if hasattr(self, '_loading_active') and self._loading_active:
            self._loading_active = False
            if hasattr(self, '_loading_thread') and self._loading_thread.is_alive():
                self._loading_thread.join(0.5)  # Wait for thread to finish with timeout
            
            # Clear the animation from status line
            self.update_status(self._loading_base_message)
    
    def _animate_loading(self) -> None:
        """Thread function to animate the loading indicator"""
        try:
            while self._loading_active:
                # Get the current frame
                frame = self._loading_frames[self._loading_frame % len(self._loading_frames)]
                
                # Update status with animation
                animated_message = f"{self._loading_base_message} {frame}"
                self.update_status(animated_message)
                
                # Advance to next frame
                self._loading_frame += 1
                
                # Sleep for a short time
                time.sleep(0.1)
        except Exception as e:
            import logging
            logging.error(f"Error in loading animation: {str(e)}")
            self._loading_active = False
    def show_optimization_message(self) -> None:
        """Method implementation removed as requested"""
        pass
