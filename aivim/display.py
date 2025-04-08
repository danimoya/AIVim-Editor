"""
Display handling for AIVim using curses
"""
import curses
from typing import List, Optional, Tuple

from aivim.modes import Mode
from aivim.syntax import SyntaxHighlighter


class Display:
    """
    Handles the display and rendering for AIVim
    """
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.syntax_highlighter = SyntaxHighlighter()
        self.scroll_offset_y = 0
        self.selection_active = False
        self.selection_start = (0, 0)
        self.selection_end = (0, 0)
    
    def setup(self) -> None:
        """Initialize the display settings"""
        # Initialize colors if terminal supports them
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(1, curses.COLOR_WHITE, -1)     # Normal text
            curses.init_pair(2, curses.COLOR_CYAN, -1)      # Status line
            curses.init_pair(3, curses.COLOR_YELLOW, -1)    # Line numbers
            curses.init_pair(4, curses.COLOR_GREEN, -1)     # Keywords
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)   # Strings
            curses.init_pair(6, curses.COLOR_RED, -1)       # Comments
            curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selection
            curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Visual mode selection
        
        # Hide cursor during setup
        curses.curs_set(0)
        
        # No delay for ESC key
        self.stdscr.nodelay(0)
        
        # Enable keypad for special keys
        self.stdscr.keypad(True)
    
    def refresh(self, 
               lines: List[str], 
               cursor_y: int, 
               cursor_x: int, 
               mode: Mode, 
               command_line: str,
               status_message: str,
               ai_processing: bool) -> None:
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
        """
        # Clear the screen
        self.stdscr.clear()
        
        # Update the window dimensions
        self.height, self.width = self.stdscr.getmaxyx()
        
        # Calculate the available height for text (minus status lines)
        text_height = self.height - 2
        
        # Adjust scroll if cursor is out of view
        if cursor_y < self.scroll_offset_y:
            self.scroll_offset_y = cursor_y
        elif cursor_y >= self.scroll_offset_y + text_height:
            self.scroll_offset_y = cursor_y - text_height + 1
        
        # Draw line numbers and content
        line_num_width = len(str(len(lines))) + 1
        for i in range(text_height):
            line_idx = i + self.scroll_offset_y
            
            if line_idx < len(lines):
                # Draw line number
                line_num_str = f"{line_idx + 1}".rjust(line_num_width - 1) + " "
                self.stdscr.addstr(i, 0, line_num_str, curses.color_pair(3))
                
                # Draw line content with syntax highlighting
                line = lines[line_idx]
                self._draw_line_with_highlighting(i, line_num_width, line, cursor_y, cursor_x, mode, line_idx)
        
        # Draw status line
        self._draw_status_line(mode, ai_processing, status_message)
        
        # Draw command line
        if command_line:
            self.stdscr.addstr(self.height - 1, 0, command_line)
        
        # Position cursor
        if mode == Mode.COMMAND:
            # Place cursor at end of command line
            self.stdscr.move(self.height - 1, len(command_line))
        else:
            # Place cursor at editing position
            cursor_row = cursor_y - self.scroll_offset_y
            if 0 <= cursor_row < text_height:
                visible_x = min(cursor_x, self.width - line_num_width - 1)
                self.stdscr.move(cursor_row, line_num_width + visible_x)
        
        # Make cursor visible
        curses.curs_set(1)
        
        # Refresh the screen
        self.stdscr.refresh()
    
    def _draw_line_with_highlighting(self, 
                                   screen_y: int, 
                                   start_x: int, 
                                   line: str,
                                   cursor_y: int,
                                   cursor_x: int,
                                   mode: Mode,
                                   line_idx: int) -> None:
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
        """
        # Calculate the width available for text
        available_width = self.width - start_x - 1
        
        # Truncate line if it's too long
        display_line = line[:available_width]
        
        # Get syntax highlighting for this line
        highlights = self.syntax_highlighter.highlight(display_line)
        
        # Draw each character with its highlighting
        for x, char in enumerate(display_line):
            attr = curses.color_pair(highlights.get(x, 1))
            
            # Handle selection highlighting in visual mode
            if mode == Mode.VISUAL and hasattr(self, 'selection_start') and hasattr(self, 'selection_end'):
                start_y, start_x = getattr(self, 'selection_start', (0, 0))
                end_y, end_x = getattr(self, 'selection_end', (0, 0))
                
                # Ensure start is before end
                if start_y > end_y or (start_y == end_y and start_x > end_x):
                    start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
                
                if (start_y <= line_idx <= end_y) and (
                    (line_idx > start_y and line_idx < end_y) or
                    (line_idx == start_y and x >= start_x) or
                    (line_idx == end_y and x <= end_x) or
                    (start_y == end_y and start_x <= x <= end_x)
                ):
                    attr = curses.color_pair(8)  # Visual selection color
            
            try:
                self.stdscr.addch(screen_y, start_x + x, ord(char), attr)
            except curses.error:
                # This happens when trying to draw at the bottom-right corner of the screen
                pass
    
    def _draw_status_line(self, mode: Mode, ai_processing: bool, status_message: str) -> None:
        """
        Draw the status line at the bottom of the screen
        
        Args:
            mode: Current editor mode
            ai_processing: Whether AI is currently processing
            status_message: Status message to display
        """
        # Create the mode display string
        mode_str = f"-- {mode.name} --"
        
        # Create the AI status string
        ai_status = "AI PROCESSING..." if ai_processing else ""
        
        # Combine all status elements
        left_status = f" {mode_str} "
        middle_status = f" {status_message} "
        right_status = f" {ai_status} "
        
        # Calculate spacing
        remaining_space = self.width - len(left_status) - len(right_status)
        middle_space = max(0, remaining_space - len(middle_status))
        padding = " " * middle_space
        
        # Truncate if too long
        status_line = (left_status + middle_status + padding + right_status)[:self.width]
        
        # Draw the status line
        try:
            self.stdscr.addstr(self.height - 2, 0, status_line, curses.color_pair(2) | curses.A_REVERSE)
        except curses.error:
            # This can happen if the terminal size changes
            pass
