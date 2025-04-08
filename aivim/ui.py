"""
UI module for rendering the editor interface.
"""

import curses
import time
from typing import List, Tuple, Dict, Any, Optional

class UI:
    """
    UI renderer for the editor.
    """
    
    def __init__(self, stdscr):
        """
        Initialize the UI.

        Args:
            stdscr: curses standard screen
        """
        self.stdscr = stdscr
        self.line_number_width = 4  # Width of line number column
        self.status_height = 2  # Height of status/command bar
        self.rows, self.cols = stdscr.getmaxyx()
        
        # Color pairs
        self.NORMAL_COLOR = 1
        self.STATUS_COLOR = 2
        self.LINENR_COLOR = 3
        self.COMMAND_COLOR = 4
        self.VISUAL_COLOR = 5
        self.AI_COLOR = 6
    
    def render(self, editor) -> None:
        """
        Render the editor UI.

        Args:
            editor: The editor instance
        """
        # Update terminal size
        self.rows, self.cols = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # Calculate visible area
        visible_rows = self.rows - self.status_height
        scroll_offset = editor.scroll_y
        
        # Render line numbers and text
        for i in range(visible_rows):
            line_idx = i + scroll_offset
            if line_idx >= len(editor.buffer.lines):
                break
            
            self._render_line_number(i, line_idx + 1)
            self._render_line(editor, i, line_idx)
        
        # Render status bar and command line
        self._render_status_bar(editor)
        self._render_command_line(editor)
        
        # Position cursor
        cursor_y = editor.cursor_y - scroll_offset
        cursor_x = editor.cursor_x + self.line_number_width + 1
        
        if 0 <= cursor_y < visible_rows:
            self.stdscr.move(cursor_y, cursor_x)
        
        self.stdscr.refresh()
    
    def _render_line_number(self, row: int, line_number: int) -> None:
        """
        Render a line number.

        Args:
            row: Screen row
            line_number: Line number to display (1-based)
        """
        line_nr_str = f"{line_number:>{self.line_number_width-1}} "
        self.stdscr.addstr(row, 0, line_nr_str, curses.color_pair(self.LINENR_COLOR))
    
    def _render_line(self, editor, row: int, line_idx: int) -> None:
        """
        Render a line of text.

        Args:
            editor: The editor instance
            row: Screen row
            line_idx: Line index in the buffer
        """
        line = editor.buffer.get_line(line_idx)
        max_line_length = self.cols - self.line_number_width - 1
        
        # Determine if this line is part of a visual selection
        is_visual_selection = False
        if editor.mode == editor.VISUAL_MODE:
            min_y = min(editor.visual_start_y, editor.cursor_y)
            max_y = max(editor.visual_start_y, editor.cursor_y)
            is_visual_selection = min_y <= line_idx <= max_y
        
        # Truncate line if needed
        displayed_line = line[:max_line_length]
        
        # Determine color based on mode and selection
        color = curses.color_pair(self.NORMAL_COLOR)
        
        # Check if this line was modified by AI
        if editor.version_control.is_ai_modified_line(line_idx):
            color = curses.color_pair(self.AI_COLOR)
        
        # Visual selection takes precedence
        if is_visual_selection:
            color = curses.color_pair(self.VISUAL_COLOR)
        
        # Render the line
        self.stdscr.addstr(row, self.line_number_width, displayed_line, color)
    
    def _render_status_bar(self, editor) -> None:
        """
        Render the status bar.

        Args:
            editor: The editor instance
        """
        status_line = self.rows - 2
        
        # Clear status line
        self.stdscr.addstr(status_line, 0, " " * self.cols, curses.color_pair(self.STATUS_COLOR))
        
        # Left side: filename and modified indicator
        filename = editor.filename or "[No Name]"
        left_status = f" {filename} "
        if editor.version_control.is_modified():
            left_status += "[+] "
        
        # Right side: line/column info
        line_col = f"Ln {editor.cursor_y + 1}, Col {editor.cursor_x + 1} "
        
        # Middle: mode indicator
        mode_text = self._get_mode_text(editor.mode)
        
        # Status message
        status_msg = editor.status_message if time.time() < editor.status_message_timeout else ""
        
        # Calculate positions
        right_start = self.cols - len(line_col)
        mode_start = (self.cols - len(mode_text)) // 2
        msg_start = len(left_status)
        msg_width = mode_start - msg_start - 1
        
        # Render components
        self.stdscr.addstr(status_line, 0, left_status, curses.color_pair(self.STATUS_COLOR))
        
        if status_msg and len(status_msg) <= msg_width:
            self.stdscr.addstr(status_line, msg_start, status_msg, curses.color_pair(self.STATUS_COLOR))
        
        self.stdscr.addstr(status_line, mode_start, mode_text, curses.color_pair(self.STATUS_COLOR))
        self.stdscr.addstr(status_line, right_start, line_col, curses.color_pair(self.STATUS_COLOR))
    
    def _render_command_line(self, editor) -> None:
        """
        Render the command line.

        Args:
            editor: The editor instance
        """
        command_line_row = self.rows - 1
        
        # Clear command line
        self.stdscr.addstr(command_line_row, 0, " " * self.cols, curses.color_pair(self.NORMAL_COLOR))
        
        # Show command line in command mode
        if editor.mode == editor.COMMAND_MODE:
            prompt = ":"
            command = editor.command_line
            
            if len(prompt) + len(command) > self.cols:
                # Truncate if command is too long
                visible_cmd = command[-(self.cols - len(prompt)):]
            else:
                visible_cmd = command
            
            self.stdscr.addstr(command_line_row, 0, prompt, curses.color_pair(self.COMMAND_COLOR))
            self.stdscr.addstr(command_line_row, len(prompt), visible_cmd, curses.color_pair(self.COMMAND_COLOR))
            
            # Position cursor in command line
            cursor_x = len(prompt) + editor.command_cursor
            if cursor_x >= self.cols:
                cursor_x = self.cols - 1
            self.stdscr.move(command_line_row, cursor_x)
    
    def _get_mode_text(self, mode: str) -> str:
        """
        Get the display text for the current mode.

        Args:
            mode: Current editor mode

        Returns:
            Mode display text
        """
        mode_display = {
            "normal": "NORMAL",
            "insert": "INSERT",
            "visual": "VISUAL",
            "command": "COMMAND"
        }
        return mode_display.get(mode, mode.upper())
