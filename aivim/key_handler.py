"""
Key handler module for processing keyboard input.
"""

import curses
from typing import Dict, Callable

class KeyHandler:
    """
    Handler for keyboard input.
    """
    
    def __init__(self, editor):
        """
        Initialize the key handler.

        Args:
            editor: Reference to the editor
        """
        self.editor = editor
        
        # Special key codes
        self.KEY_ESC = 27
        self.KEY_ENTER = 10
        self.KEY_BACKSPACE = 127
        self.KEY_DELETE = curses.KEY_DC
        self.KEY_TAB = 9
        
        # Mode handlers
        self.mode_handlers = {
            self.editor.NORMAL_MODE: self._handle_normal_mode,
            self.editor.INSERT_MODE: self._handle_insert_mode,
            self.editor.VISUAL_MODE: self._handle_visual_mode,
            self.editor.COMMAND_MODE: self._handle_command_mode
        }
    
    def handle_key(self, key: int) -> None:
        """
        Process a keyboard input.

        Args:
            key: The key code
        """
        # Check for global keys that work in any mode
        if self._handle_global_keys(key):
            return
        
        # Delegate to mode-specific handler
        if self.editor.mode in self.mode_handlers:
            self.mode_handlers[self.editor.mode](key)
    
    def _handle_global_keys(self, key: int) -> bool:
        """
        Handle keys that work in any mode.

        Args:
            key: The key code

        Returns:
            True if key was handled, False otherwise
        """
        # Check for Ctrl+Left/Right for version navigation
        if key == curses.KEY_LEFT and curses.keyname(key).decode().startswith('^'):
            self.editor.undo_ai_modification()
            return True
        
        if key == curses.KEY_RIGHT and curses.keyname(key).decode().startswith('^'):
            self.editor.redo_ai_modification()
            return True
        
        return False
    
    def _handle_normal_mode(self, key: int) -> None:
        """
        Handle keys in normal mode.

        Args:
            key: The key code
        """
        if key == ord('i'):
            # Enter insert mode
            self.editor.mode = self.editor.INSERT_MODE
            self.editor.set_status_message("-- INSERT --")
        
        elif key == ord('s'):
            # Delete current character and enter insert mode
            line = self.editor.buffer.get_line(self.editor.cursor_y)
            if self.editor.cursor_x < len(line):
                # Delete character under cursor
                new_line = line[:self.editor.cursor_x] + line[self.editor.cursor_x+1:]
                self.editor.buffer.set_line(self.editor.cursor_y, new_line)
                
                # Enter insert mode
                self.editor.mode = self.editor.INSERT_MODE
                self.editor.set_status_message("-- INSERT --")
        
        elif key == ord('v'):
            # Enter visual mode
            self.editor.mode = self.editor.VISUAL_MODE
            self.editor.visual_start_x = self.editor.cursor_x
            self.editor.visual_start_y = self.editor.cursor_y
            self.editor.set_status_message("-- VISUAL --")
        
        elif key == ord(':'):
            # Enter command mode
            self.editor.mode = self.editor.COMMAND_MODE
            self.editor.command_line = ""
            self.editor.command_cursor = 0
        
        # Cursor movement - prioritize arrow keys but keep hjkl as alternatives
        elif key == curses.KEY_LEFT or key == ord('h'):
            self.editor.move_cursor(-1, 0)
        
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.editor.move_cursor(0, 1)
        
        elif key == curses.KEY_UP or key == ord('k'):
            self.editor.move_cursor(0, -1)
        
        elif key == curses.KEY_RIGHT or key == ord('l'):
            self.editor.move_cursor(1, 0)
        
        # Line navigation
        elif key == ord('0'):
            # Beginning of line
            self.editor.cursor_x = 0
        
        elif key == ord('$'):
            # End of line
            if self.editor.cursor_y < len(self.editor.buffer.lines):
                self.editor.cursor_x = max(0, len(self.editor.buffer.lines[self.editor.cursor_y]) - 1)
        
        # File navigation
        elif key == ord('G'):
            # Go to end of file
            self.editor.cursor_y = len(self.editor.buffer.lines) - 1
            self.editor.cursor_x = 0
        
        elif key == ord('g'):
            # Wait for second 'g' to go to beginning of file
            second_key = self.editor.ui.stdscr.getch()
            if second_key == ord('g'):
                self.editor.cursor_y = 0
                self.editor.cursor_x = 0
    
    def _handle_insert_mode(self, key: int) -> None:
        """
        Handle keys in insert mode.

        Args:
            key: The key code
        """
        if key == self.KEY_ESC:
            # Exit insert mode
            self.editor.mode = self.editor.NORMAL_MODE
            self.editor.set_status_message("")
        
        elif key == self.KEY_ENTER:
            # Split line at cursor
            current_line = self.editor.buffer.get_line(self.editor.cursor_y)
            new_line = current_line[self.editor.cursor_x:]
            self.editor.buffer.replace_line(self.editor.cursor_y, current_line[:self.editor.cursor_x])
            self.editor.buffer.insert_line(self.editor.cursor_y + 1, new_line)
            self.editor.cursor_y += 1
            self.editor.cursor_x = 0
        
        elif key == self.KEY_BACKSPACE:
            # Handle backspace
            if self.editor.cursor_x > 0:
                # Delete character before cursor
                current_line = self.editor.buffer.get_line(self.editor.cursor_y)
                self.editor.buffer.replace_line(
                    self.editor.cursor_y,
                    current_line[:self.editor.cursor_x-1] + current_line[self.editor.cursor_x:]
                )
                self.editor.cursor_x -= 1
            elif self.editor.cursor_y > 0:
                # Join with previous line
                current_line = self.editor.buffer.get_line(self.editor.cursor_y)
                previous_line = self.editor.buffer.get_line(self.editor.cursor_y - 1)
                self.editor.cursor_x = len(previous_line)
                self.editor.buffer.replace_line(self.editor.cursor_y - 1, previous_line + current_line)
                self.editor.buffer.delete_line(self.editor.cursor_y)
                self.editor.cursor_y -= 1
        
        elif key == self.KEY_DELETE:
            # Delete character at cursor
            current_line = self.editor.buffer.get_line(self.editor.cursor_y)
            if self.editor.cursor_x < len(current_line):
                self.editor.buffer.replace_line(
                    self.editor.cursor_y,
                    current_line[:self.editor.cursor_x] + current_line[self.editor.cursor_x+1:]
                )
            elif self.editor.cursor_y < len(self.editor.buffer.lines) - 1:
                # Join with next line
                next_line = self.editor.buffer.get_line(self.editor.cursor_y + 1)
                self.editor.buffer.replace_line(self.editor.cursor_y, current_line + next_line)
                self.editor.buffer.delete_line(self.editor.cursor_y + 1)
        
        elif key == self.KEY_TAB:
            # Insert tab (4 spaces)
            for _ in range(4):
                self.editor.insert_char(' ')
        
        elif 32 <= key <= 126:  # Printable ASCII characters
            self.editor.insert_char(chr(key))
        
        # Arrow key navigation in insert mode
        elif key == curses.KEY_LEFT:
            self.editor.move_cursor(-1, 0)
        elif key == curses.KEY_RIGHT:
            self.editor.move_cursor(1, 0)
        elif key == curses.KEY_UP:
            self.editor.move_cursor(0, -1)
        elif key == curses.KEY_DOWN:
            self.editor.move_cursor(0, 1)
    
    def _handle_visual_mode(self, key: int) -> None:
        """
        Handle keys in visual mode.

        Args:
            key: The key code
        """
        if key == self.KEY_ESC:
            # Exit visual mode
            self.editor.mode = self.editor.NORMAL_MODE
            self.editor.set_status_message("")
        
        # Cursor movement - prioritize arrow keys but keep hjkl as alternatives
        elif key == curses.KEY_LEFT or key == ord('h'):
            self.editor.move_cursor(-1, 0)
        
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.editor.move_cursor(0, 1)
        
        elif key == curses.KEY_UP or key == ord('k'):
            self.editor.move_cursor(0, -1)
        
        elif key == curses.KEY_RIGHT or key == ord('l'):
            self.editor.move_cursor(1, 0)
        
        # Line navigation
        elif key == ord('0'):
            # Beginning of line
            self.editor.cursor_x = 0
        
        elif key == ord('$'):
            # End of line
            if self.editor.cursor_y < len(self.editor.buffer.lines):
                self.editor.cursor_x = max(0, len(self.editor.buffer.lines[self.editor.cursor_y]) - 1)
        
        elif key == ord(':'):
            # Enter command mode, with range pre-filled
            self.editor.mode = self.editor.COMMAND_MODE
            
            # Determine the visual selection range
            start_y = min(self.editor.visual_start_y, self.editor.cursor_y)
            end_y = max(self.editor.visual_start_y, self.editor.cursor_y)
            
            # Pre-fill command with range (convert to 1-based for user)
            self.editor.command_line = f"{start_y + 1},{end_y + 1}"
            self.editor.command_cursor = len(self.editor.command_line)
    
    def _handle_command_mode(self, key: int) -> None:
        """
        Handle keys in command mode.

        Args:
            key: The key code
        """
        if key == self.KEY_ESC:
            # Exit command mode
            self.editor.mode = self.editor.NORMAL_MODE
            self.editor.command_line = ""
        
        elif key == self.KEY_ENTER:
            # Execute command
            self.editor.execute_command(self.editor.command_line)
            self.editor.command_line = ""
        
        elif key == self.KEY_BACKSPACE:
            # Handle backspace
            if self.editor.command_cursor > 0:
                self.editor.command_line = (
                    self.editor.command_line[:self.editor.command_cursor - 1] +
                    self.editor.command_line[self.editor.command_cursor:]
                )
                self.editor.command_cursor -= 1
        
        elif key == curses.KEY_LEFT:
            # Move cursor left
            if self.editor.command_cursor > 0:
                self.editor.command_cursor -= 1
        
        elif key == curses.KEY_RIGHT:
            # Move cursor right
            if self.editor.command_cursor < len(self.editor.command_line):
                self.editor.command_cursor += 1
        
        elif 32 <= key <= 126:  # Printable ASCII characters
            # Insert character at cursor position
            self.editor.command_line = (
                self.editor.command_line[:self.editor.command_cursor] +
                chr(key) +
                self.editor.command_line[self.editor.command_cursor:]
            )
            self.editor.command_cursor += 1
