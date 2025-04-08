"""
Display handling for AIVim using curses
"""
import curses
import logging
from typing import List, Optional, Tuple

from aivim.modes import Mode
from aivim.utils import get_color_pair


class Display:
    """
    Handles the display and rendering for AIVim
    """
    def __init__(self, stdscr):
        """
        Initialize the display
        
        Args:
            stdscr: Curses standard screen
        """
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.scroll_offset_y = 0
        self.scroll_offset_x = 0
        self.status_line_height = 2  # Status line + command line
        self.max_visible_lines = self.height - self.status_line_height
    
    def setup(self) -> None:
        """Initialize the display settings"""
        # Set up colors
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        # Default colors
        curses.init_pair(1, curses.COLOR_WHITE, -1)  # Normal text
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Status line
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Command line
        curses.init_pair(4, curses.COLOR_CYAN, -1)  # Highlighted text
        curses.init_pair(5, curses.COLOR_GREEN, -1)  # Comments
        curses.init_pair(6, curses.COLOR_RED, -1)  # Keywords
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)  # Selected text
        curses.init_pair(8, curses.COLOR_BLUE, -1)  # Line numbers
        
        # Hide cursor
        curses.curs_set(0)
        
        # Enable keypad mode
        self.stdscr.keypad(True)
        
        # No delay on getch()
        self.stdscr.nodelay(False)
    
    def refresh(self, 
               lines: List[str], 
               cursor_y: int, 
               cursor_x: int, 
               mode: Mode, 
               command_line: str,
               status_message: str,
               ai_processing: bool,
               selection: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> None:
        """
        Refresh the display with current content
        
        Args:
            lines: The lines of text to display
            cursor_y: Current cursor Y position
            cursor_x: Current cursor X position
            mode: Current editor mode
            command_line: Content of the command line
            status_message: Status message to display
            ai_processing: Whether AI is currently processing
            selection: Current selection (start_pos, end_pos) or None
        """
        try:
            # Clear screen
            self.stdscr.clear()
            
            # Update dimensions
            self.height, self.width = self.stdscr.getmaxyx()
            self.max_visible_lines = self.height - self.status_line_height
            
            # Adjust scroll if cursor is outside visible area
            self._adjust_scroll(cursor_y, cursor_x, lines)
            
            # Draw text lines
            visible_lines = min(self.max_visible_lines, len(lines))
            for i in range(visible_lines):
                line_idx = i + self.scroll_offset_y
                if line_idx < len(lines):
                    # Line number margin (3 chars wide plus 1 space)
                    line_num = str(line_idx + 1).rjust(3)
                    self.stdscr.addstr(i, 0, line_num, curses.color_pair(8))
                    self.stdscr.addstr(i, 4, " ")
                    
                    # Draw the actual line content with highlighting
                    self._draw_line_with_highlighting(
                        i, 5, lines[line_idx], cursor_y, cursor_x, mode, line_idx, selection
                    )
            
            # Draw status line and command line
            self._draw_status_line(mode, ai_processing, status_message)
            self._draw_command_line(command_line)
            
            # Position cursor
            if cursor_y - self.scroll_offset_y < self.max_visible_lines and cursor_y >= self.scroll_offset_y:
                # Make cursor visible
                curses.curs_set(1)
                self.stdscr.move(cursor_y - self.scroll_offset_y, cursor_x - self.scroll_offset_x + 5)
            else:
                # Hide cursor when it's outside visible area
                curses.curs_set(0)
            
            # Refresh the screen
            self.stdscr.refresh()
            
        except Exception as e:
            logging.error(f"Display refresh error: {str(e)}")
    
    def _adjust_scroll(self, cursor_y: int, cursor_x: int, lines: List[str]) -> None:
        """
        Adjust scroll offsets based on cursor position
        
        Args:
            cursor_y: Cursor Y position
            cursor_x: Cursor X position
            lines: Text lines
        """
        # Vertical scrolling
        if cursor_y < self.scroll_offset_y:
            # Cursor above visible area - scroll up
            self.scroll_offset_y = cursor_y
        elif cursor_y >= self.scroll_offset_y + self.max_visible_lines:
            # Cursor below visible area - scroll down
            self.scroll_offset_y = cursor_y - self.max_visible_lines + 1
        
        # Horizontal scrolling (handle long lines)
        content_width = self.width - 5  # Account for line number margin
        if cursor_x < self.scroll_offset_x:
            # Cursor left of visible area - scroll left
            self.scroll_offset_x = cursor_x
        elif cursor_x >= self.scroll_offset_x + content_width:
            # Cursor right of visible area - scroll right
            self.scroll_offset_x = cursor_x - content_width + 1
    
    def _draw_line_with_highlighting(self, 
                                   screen_y: int, 
                                   start_x: int, 
                                   line: str,
                                   cursor_y: int,
                                   cursor_x: int,
                                   mode: Mode,
                                   line_idx: int,
                                   selection: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None) -> None:
        """
        Draw a single line with syntax highlighting
        
        Args:
            screen_y: Screen Y position to draw at
            start_x: Screen X position to start drawing
            line: Line content to draw
            cursor_y: Current cursor Y position
            cursor_x: Current cursor X position
            mode: Current editor mode
            line_idx: Index of the line being drawn
            selection: Current selection as ((start_y, start_x), (end_y, end_x)) or None
        """
        # Apply horizontal scrolling
        if self.scroll_offset_x < len(line):
            line_to_draw = line[self.scroll_offset_x:self.scroll_offset_x + self.width - start_x]
        else:
            line_to_draw = ""
        
        # Draw the line
        try:
            # Handle selection highlighting
            if selection:
                start_pos, end_pos = selection
                start_y, start_x = start_pos
                end_y, end_x = end_pos
                
                # Ensure start position is before end position
                if start_y > end_y or (start_y == end_y and start_x > end_x):
                    start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
                
                # Check if this line is in the selection
                if start_y <= line_idx <= end_y:
                    # Draw the line with selection highlighting
                    x_pos = start_x
                    
                    # Handle single line selection
                    if start_y == end_y:
                        # Draw before selection
                        if x_pos > self.scroll_offset_x:
                            before_selection = line_to_draw[:min(x_pos - self.scroll_offset_x, len(line_to_draw))]
                            self.stdscr.addstr(screen_y, start_x, before_selection, curses.color_pair(1))
                        
                        # Draw selection
                        selection_start = max(0, start_x - self.scroll_offset_x)
                        selection_end = min(len(line_to_draw), end_x - self.scroll_offset_x)
                        
                        if selection_end > selection_start:
                            selection_text = line_to_draw[selection_start:selection_end]
                            self.stdscr.addstr(
                                screen_y, 
                                start_x + selection_start, 
                                selection_text, 
                                curses.color_pair(7)
                            )
                        
                        # Draw after selection
                        if end_x - self.scroll_offset_x < len(line_to_draw):
                            after_selection = line_to_draw[end_x - self.scroll_offset_x:]
                            self.stdscr.addstr(
                                screen_y, 
                                start_x + end_x - self.scroll_offset_x, 
                                after_selection, 
                                curses.color_pair(1)
                            )
                    
                    # Handle multi-line selection
                    else:
                        if line_idx == start_y:
                            # First line of selection
                            if start_x > self.scroll_offset_x:
                                before_selection = line_to_draw[:start_x - self.scroll_offset_x]
                                self.stdscr.addstr(screen_y, start_x, before_selection, curses.color_pair(1))
                            
                            # Selection part
                            selection_text = line_to_draw[max(0, start_x - self.scroll_offset_x):]
                            if selection_text:
                                self.stdscr.addstr(
                                    screen_y, 
                                    start_x + max(0, start_x - self.scroll_offset_x), 
                                    selection_text, 
                                    curses.color_pair(7)
                                )
                        
                        elif line_idx == end_y:
                            # Last line of selection
                            selection_text = line_to_draw[:min(len(line_to_draw), end_x - self.scroll_offset_x)]
                            if selection_text:
                                self.stdscr.addstr(
                                    screen_y, 
                                    start_x, 
                                    selection_text, 
                                    curses.color_pair(7)
                                )
                            
                            # After selection
                            if end_x - self.scroll_offset_x < len(line_to_draw):
                                after_selection = line_to_draw[end_x - self.scroll_offset_x:]
                                self.stdscr.addstr(
                                    screen_y, 
                                    start_x + end_x - self.scroll_offset_x, 
                                    after_selection, 
                                    curses.color_pair(1)
                                )
                        
                        else:
                            # Middle line - fully selected
                            self.stdscr.addstr(screen_y, start_x, line_to_draw, curses.color_pair(7))
                    
                    return
            
            # If no selection or line not in selection, draw normally with syntax highlighting
            self.stdscr.addstr(screen_y, start_x, line_to_draw, curses.color_pair(1))
                
        except Exception as e:
            logging.error(f"Error drawing line: {str(e)}")
    
    def _draw_status_line(self, mode: Mode, ai_processing: bool, status_message: str) -> None:
        """
        Draw the status line at the bottom of the screen
        
        Args:
            mode: Current editor mode
            ai_processing: Whether AI is currently processing
            status_message: Status message to display
        """
        try:
            status_y = self.height - 2
            
            # Clear status line
            self.stdscr.move(status_y, 0)
            self.stdscr.clrtoeol()
            
            # Create status line content
            mode_display = f" {mode.name} "
            ai_status = " AI:PROCESSING " if ai_processing else ""
            
            # Draw mode indicator
            self.stdscr.addstr(status_y, 0, mode_display, curses.color_pair(2))
            
            # Draw AI processing indicator if active
            if ai_processing:
                self.stdscr.addstr(status_y, len(mode_display), ai_status, curses.color_pair(6))
            
            # Draw status message (truncated if needed)
            message_start = len(mode_display) + len(ai_status)
            max_message_len = self.width - message_start - 1
            
            if status_message and max_message_len > 0:
                if len(status_message) > max_message_len:
                    display_message = status_message[:max_message_len - 3] + "..."
                else:
                    display_message = status_message
                
                self.stdscr.addstr(status_y, message_start, display_message, curses.color_pair(1))
        
        except Exception as e:
            logging.error(f"Error drawing status line: {str(e)}")
    
    def _draw_command_line(self, command_line: str) -> None:
        """
        Draw the command line
        
        Args:
            command_line: Current command line content
        """
        try:
            command_y = self.height - 1
            
            # Clear command line
            self.stdscr.move(command_y, 0)
            self.stdscr.clrtoeol()
            
            # Draw command line
            if command_line:
                # Ensure command line fits in the available width
                if len(command_line) > self.width - 1:
                    command_line = command_line[:self.width - 4] + "..."
                
                self.stdscr.addstr(command_y, 0, command_line, curses.color_pair(3))
        
        except Exception as e:
            logging.error(f"Error drawing command line: {str(e)}")
    
    def show_dialog(self, title: str, content: List[str], wait_for_key: bool = True) -> None:
        """
        Show a dialog box with content
        
        Args:
            title: Dialog title
            content: List of content lines
            wait_for_key: Whether to wait for a key press before returning
        """
        try:
            # Calculate dialog size
            max_content_width = max(len(line) for line in content) if content else 0
            dialog_width = max(max_content_width + 4, len(title) + 4)
            dialog_height = len(content) + 4  # Title + borders + padding
            
            # Calculate dialog position
            dialog_y = max(0, (self.height - dialog_height) // 2)
            dialog_x = max(0, (self.width - dialog_width) // 2)
            
            # Create dialog window
            dialog = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
            dialog.box()
            
            # Draw title
            dialog.addstr(0, (dialog_width - len(title)) // 2, title, curses.A_BOLD)
            
            # Draw content
            for i, line in enumerate(content):
                dialog.addstr(2 + i, 2, line[:dialog_width - 4])
            
            # Draw footer
            if wait_for_key:
                footer = "Press any key to continue"
                dialog.addstr(dialog_height - 1, (dialog_width - len(footer)) // 2, footer)
            
            # Show dialog
            dialog.refresh()
            
            # Wait for key if required
            if wait_for_key:
                dialog.getch()
        
        except Exception as e:
            logging.error(f"Error showing dialog: {str(e)}")
    
    def ask_input(self, prompt: str, default: str = "") -> str:
        """
        Ask for user input
        
        Args:
            prompt: Prompt text
            default: Default value
            
        Returns:
            User input string
        """
        try:
            input_y = self.height - 1
            
            # Clear input line
            self.stdscr.move(input_y, 0)
            self.stdscr.clrtoeol()
            
            # Show prompt
            self.stdscr.addstr(input_y, 0, prompt, curses.color_pair(3))
            
            # Show default value
            if default:
                self.stdscr.addstr(input_y, len(prompt), default, curses.color_pair(3))
                current_value = default
            else:
                current_value = ""
            
            cursor_x = len(prompt) + len(current_value)
            self.stdscr.move(input_y, cursor_x)
            
            # Make cursor visible
            curses.curs_set(1)
            
            # Enable echo and get input
            curses.echo()
            
            # Process input
            result = current_value
            while True:
                key = self.stdscr.getch()
                
                if key == curses.KEY_ENTER or key == 10 or key == 13:
                    # Enter - confirm input
                    break
                elif key == 27:
                    # Escape - cancel
                    result = ""
                    break
                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                    # Backspace - delete character
                    if result:
                        result = result[:-1]
                        self.stdscr.move(input_y, 0)
                        self.stdscr.clrtoeol()
                        self.stdscr.addstr(input_y, 0, prompt, curses.color_pair(3))
                        self.stdscr.addstr(input_y, len(prompt), result, curses.color_pair(3))
                        cursor_x = len(prompt) + len(result)
                        self.stdscr.move(input_y, cursor_x)
                else:
                    # Add character
                    char = chr(key)
                    result += char
                    self.stdscr.addstr(input_y, cursor_x, char, curses.color_pair(3))
                    cursor_x += 1
                    self.stdscr.move(input_y, cursor_x)
            
            # Reset terminal settings
            curses.noecho()
            curses.curs_set(0)
            
            return result
        
        except Exception as e:
            logging.error(f"Error getting input: {str(e)}")
            return ""