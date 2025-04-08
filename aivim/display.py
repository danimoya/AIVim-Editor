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
        
        # Display lines
        for i in range(display_lines):
            line_num = scroll_y + i
            line = lines[line_num]
            
            # Display line number
            gutter = f"{line_num+1:3d} "
            self.text_win.addstr(i, 0, gutter, self.COLOR_LINENO)
            
            # Display line content
            if not selection_start or not selection_end:
                # No selection, simple display
                self.text_win.addstr(i, self.gutter_width, line)
            else:
                # Handle display with selection
                if line_num < selection_start[0] or line_num > selection_end[0]:
                    # Line is outside selection
                    self.text_win.addstr(i, self.gutter_width, line)
                elif line_num == selection_start[0] and line_num == selection_end[0]:
                    # Selection starts and ends on this line
                    if selection_start[1] < len(line):
                        self.text_win.addstr(i, self.gutter_width, line[:selection_start[1]])
                    
                    selected_text = line[selection_start[1]:selection_end[1]]
                    if selected_text:
                        self.text_win.addstr(i, self.gutter_width + selection_start[1], 
                                           selected_text, self.COLOR_SELECTION)
                    
                    if selection_end[1] < len(line):
                        self.text_win.addstr(i, self.gutter_width + selection_end[1], 
                                           line[selection_end[1]:])
                elif line_num == selection_start[0]:
                    # Selection starts on this line
                    if selection_start[1] < len(line):
                        self.text_win.addstr(i, self.gutter_width, line[:selection_start[1]])
                        self.text_win.addstr(i, self.gutter_width + selection_start[1], 
                                           line[selection_start[1]:], self.COLOR_SELECTION)
                elif line_num == selection_end[0]:
                    # Selection ends on this line
                    if selection_end[1] > 0:
                        self.text_win.addstr(i, self.gutter_width, line[:selection_end[1]], 
                                           self.COLOR_SELECTION)
                    
                    if selection_end[1] < len(line):
                        self.text_win.addstr(i, self.gutter_width + selection_end[1], 
                                           line[selection_end[1]:])
                else:
                    # Line is fully selected
                    self.text_win.addstr(i, self.gutter_width, line, self.COLOR_SELECTION)
        
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
    
    def update_mode(self, mode: str) -> None:
        """
        Update the display to show the current mode
        
        Args:
            mode: Current editor mode
        """
        # Add mode to the right side of the status line
        mode_text = f" {mode} "
        self.status_win.addstr(0, self.width - len(mode_text) - 1, mode_text)
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
