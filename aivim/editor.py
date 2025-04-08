"""
Core editor implementation for AIVim
"""
import curses
import logging
import os
import threading
import time
from typing import List, Optional, Dict, Any, Tuple

from .buffer import Buffer
from .display import Display
from .command_handler import CommandHandler
from .ai_service import AIService
from .history import History


class Editor:
    """
    Main editor class that coordinates all AIVim components
    """
    def __init__(self, filename: Optional[str] = None):
        """
        Initialize the editor
        
        Args:
            filename: Optional file to edit
        """
        self.buffer = Buffer()
        self.display = None  # Will be initialized in start()
        self.command_handler = None  # Will be initialized in start()
        self.ai_service = AIService()
        self.history = History()
        
        # Editor state
        self.filename = filename
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0
        self.preferred_x = 0  # For maintaining horizontal position when moving vertically
        self.status_message = ""
        self.command_buffer = ""
        self.command_cursor = 0
        self.clipboard = []
        self.should_quit = False
        
        # Mode (NORMAL, INSERT, VISUAL, COMMAND)
        self.mode = "NORMAL"
        
        # For handling terminal resize events
        self.resize_timer = None
        
        # For AI operations
        self.ai_processing = False
        self.ai_thread = None
        self.thread_lock = threading.RLock()
        
        # Load file if specified
        if filename:
            self.load_file(filename)
    
    def load_file(self, filename: str) -> None:
        """Load content from a file into the buffer"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                    self.buffer.set_content(content)
                    self.buffer.mark_as_saved()
                    self.filename = filename
                    logging.info(f"Loaded file: {filename}")
                    if self.display:
                        self.set_status_message(f"Loaded: {filename}")
            else:
                # New file
                self.buffer = Buffer()
                self.filename = filename
                logging.info(f"New file: {filename}")
                if self.display:
                    self.set_status_message(f"New file: {filename}")
        except Exception as e:
            logging.error(f"Error loading file: {str(e)}")
            if self.display:
                self.set_status_message(f"Error loading file: {str(e)}")
    
    def save_file(self, filename: Optional[str] = None) -> None:
        """Save buffer content to a file"""
        save_filename = filename or self.filename
        
        if not save_filename:
            self.set_status_message("No filename specified (use :w filename)")
            return
        
        try:
            content = self.buffer.get_content()
            with open(save_filename, 'w') as f:
                f.write(content)
            
            self.buffer.mark_as_saved()
            self.filename = save_filename
            
            self.set_status_message(f"Saved: {save_filename} ({len(content)} bytes)")
            logging.info(f"Saved file: {save_filename}")
        except Exception as e:
            self.set_status_message(f"Error saving file: {str(e)}")
            logging.error(f"Error saving file: {str(e)}")
    
    def start(self, stdscr) -> None:
        """Initialize and start the editor with curses"""
        # Initialize display
        self.display = Display(stdscr)
        
        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Setup initial screen
        curses.curs_set(1)  # Show cursor
        
        # Set up resize handler
        # curses.signal(curses.SIGWINCH, self._handle_resize)
        
        # Initialize editor components and settings
        self._initialize_editor(stdscr)
        
        # Main editor loop
        while not self.should_quit:
            # Update display
            self._update_display()
            
            # Get input
            try:
                key = stdscr.getch()
                self.handle_input(key)
            except KeyboardInterrupt:
                # Handle Ctrl+C more gracefully
                if self.mode != "NORMAL":
                    self.mode = "NORMAL"
                    self.set_status_message("Switched to NORMAL mode")
                else:
                    # In normal mode, treat as Escape
                    self.set_status_message("")
    
    def handle_input(self, key: int) -> None:
        """Process user input based on current mode"""
        if key == curses.KEY_RESIZE:
            # Terminal was resized
            self._handle_resize()
            return
        
        # Handle input based on current mode
        if self.mode == "NORMAL":
            self._handle_normal_mode(key)
        elif self.mode == "INSERT":
            self._handle_insert_mode(key)
        elif self.mode == "VISUAL":
            self._handle_visual_mode(key)
        elif self.mode == "COMMAND":
            self._handle_command_mode(key)
    
    def _handle_normal_mode(self, key: int) -> None:
        """Handle keypresses in normal mode"""
        if key == ord('i'):
            # Enter insert mode
            self.mode = "INSERT"
            self.set_status_message("-- INSERT --")
        
        elif key == ord(':'):
            # Enter command mode
            self.mode = "COMMAND"
            self.command_buffer = ":"
            self.command_cursor = 1
        
        elif key == ord('v'):
            # Enter visual mode
            self.mode = "VISUAL"
            self.buffer.start_selection(self.cursor_y, self.cursor_x)
            self.set_status_message("-- VISUAL --")
        
        elif key == ord('h') or key == curses.KEY_LEFT:
            # Move cursor left
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
        
        elif key == ord('j') or key == curses.KEY_DOWN:
            # Move cursor down
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
                
                # Scroll if needed
                if self.cursor_y >= self.scroll_y + self.display.max_text_height:
                    self.scroll_y = self.cursor_y - self.display.max_text_height + 1
        
        elif key == ord('k') or key == curses.KEY_UP:
            # Move cursor up
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
                
                # Scroll if needed
                if self.cursor_y < self.scroll_y:
                    self.scroll_y = self.cursor_y
        
        elif key == ord('l') or key == curses.KEY_RIGHT:
            # Move cursor right
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
        
        elif key == ord('d') and self.display.is_dialog_open():
            # Close dialog with 'd' key
            self.display.close_dialog()
        
        elif key == ord('d'):
            # Delete operation - need another 'd' for line delete
            next_key = self.display.stdscr.getch()
            if next_key == ord('d'):
                # Delete current line
                self.buffer.delete_line(self.cursor_y)
                # Adjust cursor position if needed
                if self.cursor_y >= len(self.buffer.get_lines()):
                    self.cursor_y = max(0, len(self.buffer.get_lines()) - 1)
                self._adjust_cursor_x()
                # Add to history
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message("Line deleted")
        
        elif key == ord('u'):
            # Undo
            if self.history.can_undo():
                lines, metadata = self.history.undo()
                if lines:
                    self.buffer.set_lines(lines)
                    self.set_status_message("Undo")
            else:
                self.set_status_message("Nothing to undo")
        
        elif key == ord('r') and (curses.keyname(key).decode("utf-8").startswith("^")):
            # Redo (Ctrl+r)
            if self.history.can_redo():
                lines, metadata = self.history.redo()
                if lines:
                    self.buffer.set_lines(lines)
                    self.set_status_message("Redo")
            else:
                self.set_status_message("Nothing to redo")
        
        elif key == ord('p'):
            # Paste
            if self.clipboard:
                # Store current version in history before paste
                self.history.add_version(self.buffer.get_lines())
                
                # Insert clipboard lines
                for i, line in enumerate(self.clipboard):
                    self.buffer.insert_line(self.cursor_y + i + 1, line)
                
                # Move cursor to the last inserted line
                self.cursor_y += len(self.clipboard)
                self._adjust_cursor_x()
                
                # Store updated version in history
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"Pasted {len(self.clipboard)} lines")
    
    def _handle_insert_mode(self, key: int) -> None:
        """Handle keypresses in insert mode"""
        if key == 27:  # Escape key
            # Return to normal mode
            self.mode = "NORMAL"
            # Add current buffer state to history
            self.history.add_version(self.buffer.get_lines())
            self.set_status_message("")
        
        elif key == curses.KEY_BACKSPACE or key == 127:
            # Backspace
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x > 0:
                # Remove character from current line
                new_line = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.buffer.set_line(self.cursor_y, new_line)
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
            elif self.cursor_y > 0:
                # Merge with previous line
                prev_line = self.buffer.get_line(self.cursor_y - 1)
                new_cursor_x = len(prev_line)
                self.buffer.set_line(self.cursor_y - 1, prev_line + line)
                self.buffer.delete_line(self.cursor_y)
                self.cursor_y -= 1
                self.cursor_x = new_cursor_x
                self.preferred_x = self.cursor_x
                
                # Adjust scroll if needed
                if self.cursor_y < self.scroll_y:
                    self.scroll_y = self.cursor_y
        
        elif key == curses.KEY_DC:
            # Delete key
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                # Remove character after cursor
                new_line = line[:self.cursor_x] + line[self.cursor_x+1:]
                self.buffer.set_line(self.cursor_y, new_line)
            elif self.cursor_y < len(self.buffer.get_lines()) - 1:
                # Merge with next line
                next_line = self.buffer.get_line(self.cursor_y + 1)
                self.buffer.set_line(self.cursor_y, line + next_line)
                self.buffer.delete_line(self.cursor_y + 1)
        
        elif key == curses.KEY_LEFT:
            # Move cursor left
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
        
        elif key == curses.KEY_RIGHT:
            # Move cursor right
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
        
        elif key == curses.KEY_UP:
            # Move cursor up
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
                
                # Scroll if needed
                if self.cursor_y < self.scroll_y:
                    self.scroll_y = self.cursor_y
        
        elif key == curses.KEY_DOWN:
            # Move cursor down
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
                
                # Scroll if needed
                if self.cursor_y >= self.scroll_y + self.display.max_text_height:
                    self.scroll_y = self.cursor_y - self.display.max_text_height + 1
        
        elif key == ord('\n') or key == curses.KEY_ENTER:
            # Enter key - split line
            line = self.buffer.get_line(self.cursor_y)
            self.buffer.set_line(self.cursor_y, line[:self.cursor_x])
            self.buffer.insert_line(self.cursor_y + 1, line[self.cursor_x:])
            self.cursor_y += 1
            self.cursor_x = 0
            self.preferred_x = 0
            
            # Scroll if needed
            if self.cursor_y >= self.scroll_y + self.display.max_text_height:
                self.scroll_y = self.cursor_y - self.display.max_text_height + 1
        
        elif key == curses.KEY_HOME:
            # Move to beginning of line
            self.cursor_x = 0
            self.preferred_x = 0
        
        elif key == curses.KEY_END:
            # Move to end of line
            line = self.buffer.get_line(self.cursor_y)
            self.cursor_x = len(line)
            self.preferred_x = self.cursor_x
        
        elif key == curses.KEY_PPAGE:  # Page Up
            # Move up a page
            self.cursor_y = max(0, self.cursor_y - self.display.max_text_height)
            self.scroll_y = max(0, self.scroll_y - self.display.max_text_height)
            self._adjust_cursor_x()
        
        elif key == curses.KEY_NPAGE:  # Page Down
            # Move down a page
            max_y = len(self.buffer.get_lines()) - 1
            self.cursor_y = min(max_y, self.cursor_y + self.display.max_text_height)
            self.scroll_y = min(max_y - self.display.max_text_height + 1, 
                               self.scroll_y + self.display.max_text_height)
            self.scroll_y = max(0, self.scroll_y)
            self._adjust_cursor_x()
        
        elif key == 9:  # Tab key
            # Insert 4 spaces for tab
            self.buffer.set_line(
                self.cursor_y,
                self.buffer.get_line(self.cursor_y)[:self.cursor_x] + 
                "    " + 
                self.buffer.get_line(self.cursor_y)[self.cursor_x:]
            )
            self.cursor_x += 4
            self.preferred_x = self.cursor_x
        
        elif 32 <= key <= 126:  # Printable ASCII characters
            # Insert character at current position
            line = self.buffer.get_line(self.cursor_y)
            char = chr(key)
            new_line = line[:self.cursor_x] + char + line[self.cursor_x:]
            self.buffer.set_line(self.cursor_y, new_line)
            self.cursor_x += 1
            self.preferred_x = self.cursor_x
    
    def _handle_visual_mode(self, key: int) -> None:
        """Handle keypresses in visual mode"""
        if key == 27:  # Escape key
            # Return to normal mode
            self.mode = "NORMAL"
            self.buffer.end_selection()
            self.set_status_message("")
        
        elif key == ord('h') or key == curses.KEY_LEFT:
            # Move cursor left
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
        
        elif key == ord('j') or key == curses.KEY_DOWN:
            # Move cursor down
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
                
                # Scroll if needed
                if self.cursor_y >= self.scroll_y + self.display.max_text_height:
                    self.scroll_y = self.cursor_y - self.display.max_text_height + 1
        
        elif key == ord('k') or key == curses.KEY_UP:
            # Move cursor up
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
                
                # Scroll if needed
                if self.cursor_y < self.scroll_y:
                    self.scroll_y = self.cursor_y
        
        elif key == ord('l') or key == curses.KEY_RIGHT:
            # Move cursor right
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
        
        elif key == ord('y'):
            # Yank (copy) selection
            selection_text = self.buffer.get_selection_text()
            self.clipboard = selection_text.split('\n')
            
            # Return to normal mode
            self.mode = "NORMAL"
            self.buffer.end_selection()
            self.set_status_message(f"Yanked {len(self.clipboard)} lines")
        
        elif key == ord('d'):
            # Delete selection
            # Store current version in history
            self.history.add_version(self.buffer.get_lines())
            
            # Get selection bounds
            selection = self.buffer.get_selection()
            if selection[0] and selection[1]:
                start_y, start_x = selection[0]
                end_y, end_x = selection[1]
                
                # Ensure start is before end
                if (start_y > end_y) or (start_y == end_y and start_x > end_x):
                    start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
                
                # Delete the selection
                if start_y == end_y:
                    # Single line selection
                    line = self.buffer.get_line(start_y)
                    new_line = line[:start_x] + line[end_x:]
                    self.buffer.set_line(start_y, new_line)
                    self.cursor_y = start_y
                    self.cursor_x = start_x
                else:
                    # Multi-line selection
                    # First line (partial)
                    first_line = self.buffer.get_line(start_y)
                    first_line_start = first_line[:start_x]
                    
                    # Last line (partial)
                    last_line = self.buffer.get_line(end_y)
                    last_line_end = last_line[end_x:]
                    
                    # Delete all lines in between
                    for _ in range(end_y - start_y):
                        self.buffer.delete_line(start_y + 1)
                    
                    # Replace first line
                    self.buffer.set_line(start_y, first_line_start + last_line_end)
                    
                    # Set cursor position
                    self.cursor_y = start_y
                    self.cursor_x = start_x
                
                # Add updated version to history
                self.history.add_version(self.buffer.get_lines())
            
            # Return to normal mode
            self.mode = "NORMAL"
            self.buffer.end_selection()
            self.set_status_message("Selection deleted")
    
    def _handle_command_mode(self, key: int) -> None:
        """Handle keypresses in command mode"""
        if key == 27:  # Escape key
            # Return to normal mode
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.command_cursor = 0
            self.set_status_message("")
        
        elif key == curses.KEY_BACKSPACE or key == 127:
            # Backspace
            if self.command_cursor > 1:  # Keep the initial ':'
                self.command_buffer = (
                    self.command_buffer[:self.command_cursor-1] + 
                    self.command_buffer[self.command_cursor:]
                )
                self.command_cursor -= 1
        
        elif key == curses.KEY_LEFT:
            # Move cursor left
            if self.command_cursor > 1:  # Don't move past the initial ':'
                self.command_cursor -= 1
        
        elif key == curses.KEY_RIGHT:
            # Move cursor right
            if self.command_cursor < len(self.command_buffer):
                self.command_cursor += 1
        
        elif key == curses.KEY_HOME:
            # Move to beginning of command (after :)
            self.command_cursor = 1
        
        elif key == curses.KEY_END:
            # Move to end of command
            self.command_cursor = len(self.command_buffer)
        
        elif key == ord('\n') or key == curses.KEY_ENTER:
            # Execute command
            self._process_command()
        
        elif 32 <= key <= 126:  # Printable ASCII characters
            # Insert character at current position
            char = chr(key)
            self.command_buffer = (
                self.command_buffer[:self.command_cursor] + 
                char + 
                self.command_buffer[self.command_cursor:]
            )
            self.command_cursor += 1
    
    def _process_command(self) -> None:
        """Process entered command"""
        # Execute command
        result = self.command_handler.execute(self.command_buffer)
        
        # Return to normal mode
        self.mode = "NORMAL"
        self.command_buffer = ""
        self.command_cursor = 0
        
        if not result:
            self.set_status_message(f"Invalid command")
    
    def _update_display(self) -> None:
        """Update the display with current buffer content"""
        # Only update if display is initialized
        if not self.display:
            return
        
        # Check if we're in a dialog
        if self.display.is_dialog_open():
            # Only handle dialog close key
            return
        
        # Update status line
        self.display.update_status(
            f"{self.filename or '[No Name]'} "
            f"{'[+]' if self.buffer.is_modified() else ''} "
            f"Line {self.cursor_y+1}/{len(self.buffer.get_lines())} "
            f"Col {self.cursor_x+1} "
            f"{self.status_message}"
        )
        
        # Update mode indicator
        self.display.update_mode(self.mode)
        
        # Update text content
        self.display.update_text(
            self.buffer.get_lines(),
            self.cursor_y,
            self.cursor_x,
            self.scroll_y,
            self.buffer.get_selection()
        )
        
        # Update command line if in command mode
        if self.mode == "COMMAND":
            self.display.update_command_line(
                self.command_buffer,
                self.command_cursor
            )
    
    def _handle_resize(self, *args) -> None:
        """Handle terminal resize event"""
        # Debounce resize events
        if self.resize_timer:
            self.resize_timer.cancel()
        
        self.resize_timer = threading.Timer(0.1, self._do_resize)
        self.resize_timer.start()
    
    def _do_resize(self) -> None:
        """Actually perform the resize operation"""
        with self.thread_lock:
            self.display.resize()
            self._update_display()
    
    def _initialize_editor(self, stdscr) -> None:
        """Initialize the editor components and settings"""
        # Initialize curses color pairs
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs for syntax highlighting and UI
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Status line
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Command line
        curses.init_pair(3, curses.COLOR_RED, -1)                     # Error messages
        curses.init_pair(4, curses.COLOR_GREEN, -1)                   # Success messages
        curses.init_pair(5, curses.COLOR_CYAN, -1)                    # Info messages
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)                 # Selection
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)     # Dialog title
        curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Dialog content
        curses.init_pair(9, curses.COLOR_GREEN, -1)                   # Diff added
        curses.init_pair(10, curses.COLOR_RED, -1)                    # Diff removed
        curses.init_pair(11, curses.COLOR_YELLOW, -1)                 # Diff changed
        
        # No delay for ESC key
        curses.set_escdelay(25)
        
        # Other initialization
        stdscr.keypad(True)       # Enable keypad mode for function keys
        curses.cbreak()           # No line buffering
        curses.noecho()           # Don't echo typed characters
        
        # Initial status message
        if self.filename:
            self.set_status_message(f"Editing: {self.filename}")
        else:
            self.set_status_message("No file opened")
    
    def _adjust_cursor_x(self) -> None:
        """Adjust cursor x position when moving vertically"""
        line = self.buffer.get_line(self.cursor_y)
        self.cursor_x = min(self.preferred_x, len(line))
    
    def set_status_message(self, message: str) -> None:
        """Set the status message"""
        self.status_message = message
        logging.info(f"Status: {message}")
        
    def show_dialog(self, title: str, content: List[str]) -> None:
        """
        Show a dialog box
        
        Args:
            title: Dialog title
            content: Dialog content lines
        """
        if self.display:
            self.display.show_dialog(title, content)
            
    def show_diff_dialog(self, title: str, diff_lines: List[str]) -> None:
        """
        Show a diff dialog box
        
        Args:
            title: Dialog title
            diff_lines: List of formatted diff lines
        """
        if self.display:
            self.display.show_diff_dialog(title, diff_lines)
    
    def run_ai_command(self, command: str, args: List[str]) -> None:
        """Run an AI-related command in a separate thread"""
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        # Select appropriate AI command based on the command name
        if command == "generate" and len(args) >= 2:
            line_num = int(args[0]) - 1  # Convert to 0-based
            description = " ".join(args[1:])
            self.ai_generate(line_num, description)
        elif command == "explain" and len(args) >= 2:
            start_line = int(args[0]) - 1  # Convert to 0-based
            end_line = int(args[1]) - 1  # Convert to 0-based
            self.ai_explain(start_line, end_line)
        elif command == "improve" and len(args) >= 2:
            start_line = int(args[0]) - 1  # Convert to 0-based
            end_line = int(args[1]) - 1  # Convert to 0-based
            self.ai_improve(start_line, end_line)
        elif command == "query":
            query = " ".join(args)
            self.ai_custom_query(query)
        else:
            self.set_status_message(f"Unknown AI command: {command}")
    
    def ai_generate(self, start_line: int, description: str) -> None:
        """
        Generate code at the specified line based on description
        
        Args:
            start_line: Line number where code should be inserted (0-based)
            description: Description of what to generate
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        # Get current buffer content for context
        lines = self.buffer.get_lines()
        context = "\n".join(lines)
        
        # Setup metadata
        metadata = {
            "command": "generate",
            "start_line": start_line,
            "description": description
        }
        
        # Mark as processing
        self.ai_processing = True
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI generating code")
        else:
            self.set_status_message("AI generating code...")
        
        # Run in a separate thread
        self.ai_thread = threading.Thread(
            target=self._ai_generate_thread,
            args=(start_line, description, context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _ai_generate_thread(self, start_line: int, description: str, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI code generation"""
        try:
            generated_code = self.ai_service.generate_code(description, context)
            
            # Apply changes in main thread
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                # Store current version in history
                self.history.add_version(self.buffer.get_lines())
                
                # Add the generated code at the specified line
                lines = generated_code.strip().split("\n")
                for i, line in enumerate(lines):
                    self.buffer.insert_line(start_line + i, line)
                
                # Add the new version to history with metadata
                self.history.add_version(self.buffer.get_lines(), metadata)
                
                # Update status
                self.ai_processing = False
                self.set_status_message(f"Generated {len(lines)} lines of code")
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error generating code: {str(e)}")
            logging.error(f"AI generation error: {str(e)}")
    
    def ai_explain(self, start_line: int, end_line: int) -> None:
        """
        Explain code in the specified line range
        
        Args:
            start_line: Starting line number (0-based)
            end_line: Ending line number (0-based)
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        lines = self.buffer.get_lines()
        
        # Validate range
        if start_line < 0 or end_line >= len(lines) or start_line > end_line:
            self.set_status_message("Invalid line range")
            return
        
        # Get code and context
        code_lines = lines[start_line:end_line+1]
        code = "\n".join(code_lines)
        context = "\n".join(lines)
        
        # Setup metadata
        metadata = {
            "command": "explain",
            "start_line": start_line,
            "end_line": end_line
        }
        
        # Mark as processing
        self.ai_processing = True
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI explaining code")
        else:
            self.set_status_message("AI explaining code...")
        
        # Run in a separate thread
        self.ai_thread = threading.Thread(
            target=self._ai_explain_thread,
            args=(code, context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _ai_explain_thread(self, code: str, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI code explanation"""
        try:
            explanation = self.ai_service.get_explanation(code, context)
            
            # Show the explanation in a dialog
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                # Split into lines of appropriate width
                explanation_lines = explanation.split("\n")
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Explanation ready")
                
                # Show dialog
                self.display.show_dialog("Code Explanation", explanation_lines)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error explaining code: {str(e)}")
            logging.error(f"AI explanation error: {str(e)}")
    
    def ai_improve(self, start_line: int, end_line: int) -> None:
        """
        Improve code in the specified line range
        
        Args:
            start_line: Starting line number (0-based)
            end_line: Ending line number (0-based)
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        lines = self.buffer.get_lines()
        
        # Validate range
        if start_line < 0 or end_line >= len(lines) or start_line > end_line:
            self.set_status_message("Invalid line range")
            return
        
        # Get code and context
        code_lines = lines[start_line:end_line+1]
        code = "\n".join(code_lines)
        context = "\n".join(lines)
        
        # Setup metadata
        metadata = {
            "command": "improve",
            "start_line": start_line,
            "end_line": end_line
        }
        
        # Mark as processing
        self.ai_processing = True
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI improving code")
        else:
            self.set_status_message("AI improving code...")
        
        # Run in a separate thread
        self.ai_thread = threading.Thread(
            target=self._ai_improve_thread,
            args=(start_line, end_line, code, context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _ai_improve_thread(self, start_line: int, end_line: int, code: str, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI code improvement"""
        try:
            improvement = self.ai_service.get_improvement(code, context)
            
            # Find the improved code section
            improved_code = improvement
            
            # Try to extract just the code if there's explanation text
            import re
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', improved_code, re.DOTALL)
            if code_blocks:
                # Use the largest code block
                improved_code = max(code_blocks, key=len)
            
            improved_lines = improved_code.strip().split("\n")
            
            # Create a diff between original and improved code
            from aivim.utils import create_diff, create_backup_file
            diff_lines = create_diff(code, improved_code)
            
            # Deal with the display in the main thread
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Review code improvement")
                
                # If there's an explanation, show it in a separate dialog
                if improvement != improved_code:
                    explanation_lines = [line for line in improvement.split("\n") 
                                       if not line.strip().startswith("```")]
                    if explanation_lines:
                        self.display.show_dialog("Code Improvement Explanation", explanation_lines)
                
                # Show the diff and ask for confirmation
                confirmation_msg = [
                    "The AI has suggested the following improvements:",
                    "",
                    f"- Original: {len(code.splitlines())} lines",
                    f"- Improved: {len(improved_lines)} lines",
                    "",
                    "Would you like to apply these changes? (y/n)",
                    "A backup of the original file will be created."
                ]
                
                # Show diff in a dialog first
                if self.display:
                    self.display.show_diff_dialog("Code Improvement Diff", diff_lines)
                
                # Check if user wants to apply changes
                if self.display and self.display.show_confirmation_dialog("Apply Changes?", confirmation_msg):
                    # Create backup if we have a filename
                    if self.filename:
                        backup_path = create_backup_file(self.filename)
                        if backup_path:
                            self.set_status_message(f"Backup created: {backup_path}")
                    
                    # Store current version in history
                    self.history.add_version(self.buffer.get_lines())
                    
                    # Replace the lines
                    lines = self.buffer.get_lines()
                    del lines[start_line:end_line+1]
                    for i, line in enumerate(improved_lines):
                        lines.insert(start_line + i, line)
                    self.buffer.set_lines(lines)
                    
                    # Add the new version to history with metadata
                    self.history.add_version(self.buffer.get_lines(), metadata)
                    
                    # Update status
                    self.set_status_message(f"Improved {len(improved_lines)} lines of code")
                else:
                    self.set_status_message("Code improvement cancelled")
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error improving code: {str(e)}")
            logging.error(f"AI improvement error: {str(e)}")
    
    def ai_custom_query(self, query: str) -> None:
        """
        Run a custom AI query on the current buffer
        
        Args:
            query: The query string
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        # Get current buffer content for context
        context = self.buffer.get_content()
        
        # Setup metadata
        metadata = {
            "command": "custom_query",
            "query": query
        }
        
        # Mark as processing
        self.ai_processing = True
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI processing query")
        else:
            self.set_status_message("AI processing query...")
        
        # Run in a separate thread
        self.ai_thread = threading.Thread(
            target=self._ai_custom_query_thread,
            args=(query, context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _ai_custom_query_thread(self, query: str, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI custom query"""
        try:
            response = self.ai_service.custom_query(query, context)
            
            # Show the response in a dialog
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                # Split into lines
                response_lines = response.split("\n")
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Query response ready")
                
                # Show dialog
                self.display.show_dialog("Query Response", response_lines)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error processing query: {str(e)}")
            logging.error(f"AI query error: {str(e)}")
    
    def quit(self, force: bool = False) -> None:
        """Quit the editor"""
        if not force and self.buffer.is_modified():
            self.set_status_message("No write since last change (use :q! to override)")
            return
        
        self.should_quit = True