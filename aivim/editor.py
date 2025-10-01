"""
Core editor implementation for AIVim
"""
import curses
import logging
import os
import re
import threading
import time
from typing import List, Optional, Dict, Any, Tuple

from .buffer import Buffer
from .display import Display
from .command_handler import CommandHandler
from .ai_service import AIService
from .history import History
from .settings import Settings


class Tab:
    """
    Represents a single tab in the editor
    """
    def __init__(self, name: str, buffer: Optional[Buffer] = None, filename: Optional[str] = None):
        """
        Initialize a new tab
        
        Args:
            name: The name/title of the tab
            buffer: Optional buffer to use, creates a new one if None
            filename: Optional filename associated with this tab
        """
        self.name = name
        self.buffer = buffer if buffer else Buffer()
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0
        self.preferred_x = 0  # For maintaining horizontal position when moving vertically
        self.filename = filename
        self.is_temporary = False  # Indicates if this is a temporary tab (like AI suggestions)
        self.history = History()  # Each tab has its own history
        
    def set_name(self, name: str) -> None:
        """Set the tab name"""
        self.name = name
        
    def get_name(self) -> str:
        """Get the tab name"""
        return self.name


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
        # Tabs management
        self.tabs = []  # List of all tabs
        self.current_tab_index = 0  # Index of current active tab
        
        # Initialize common components
        self.display = None  # Will be initialized in start()
        self.command_handler = None  # Will be initialized in start()
        self.ai_service = AIService()
        self.settings = Settings()  # Initialize settings
        
        # Create initial tab
        initial_tab = Tab("Untitled", filename=filename)
        self.tabs.append(initial_tab)
        
        # Editor state
        self.status_message = ""
        self.command_buffer = ""
        self.command_cursor = 0
        self.clipboard = []
        self.should_quit = False
        
        # Mode (NORMAL, INSERT, VISUAL, COMMAND, NLP)
        self.mode = "NORMAL"
        
        # For handling terminal resize events
        self.resize_timer = None
        
        # For NLP mode
        self.nlp_handler = None  # Will be initialized on demand
        
        # For AI operations
        self.ai_processing = False        # True if AI is currently processing a request
        self.ai_blocking = False          # True if AI operation should block the UI
        self.ai_thread = None
        self.thread_lock = threading.RLock()
        self.current_ai_model = "openai"  # Default AI model
        self.pending_ai_action = None     # For storing AI suggestions awaiting confirmation
        self.chat_history = []            # For storing chat conversation history
        self.last_ai_status_update = 0    # Timestamp of last AI status update
        
        # For search and replace functionality
        self.search_pattern = ""          # Current search pattern
        self.search_direction = "forward" # Direction of search (forward/backward)
        self.search_results = []          # List of (line, col) positions of search matches
        self.current_search_index = -1    # Index in search_results of current match
        self.search_highlighting = self.settings.search.hlsearch  # Use settings for highlighting
        self.search_case_sensitive = None # None=smart case, True=case sensitive, False=case insensitive
        self.search_regex = False         # Whether to use regex search
        self.search_very_magic = False    # \v flag for very magic mode
        self.search_input_mode = False    # True when entering search pattern
        self.search_input_buffer = ""     # Buffer for search input
        self.search_cursor_pos = 0        # Cursor position in search input
        
        # For display optimization
        self._last_update_time = time.time()
        self._last_input_time = time.time()
        
        # Load file if specified
        if filename:
            self.load_file(filename)
    
    # Property accessors to maintain compatibility with the rest of the code
    @property
    def buffer(self) -> Buffer:
        """Get the buffer from the current tab"""
        return self.tabs[self.current_tab_index].buffer
        
    @buffer.setter
    def buffer(self, value: Buffer) -> None:
        """Set the buffer for the current tab"""
        self.tabs[self.current_tab_index].buffer = value
        
    @property
    def cursor_x(self) -> int:
        """Get cursor X position from the current tab"""
        return self.tabs[self.current_tab_index].cursor_x
        
    @cursor_x.setter
    def cursor_x(self, value: int) -> None:
        """Set cursor X position for the current tab"""
        self.tabs[self.current_tab_index].cursor_x = value
        
    @property
    def cursor_y(self) -> int:
        """Get cursor Y position from the current tab"""
        return self.tabs[self.current_tab_index].cursor_y
        
    @cursor_y.setter
    def cursor_y(self, value: int) -> None:
        """Set cursor Y position for the current tab"""
        self.tabs[self.current_tab_index].cursor_y = value
        
    @property
    def scroll_y(self) -> int:
        """Get scroll Y position from the current tab"""
        return self.tabs[self.current_tab_index].scroll_y
        
    @scroll_y.setter
    def scroll_y(self, value: int) -> None:
        """Set scroll Y position for the current tab"""
        self.tabs[self.current_tab_index].scroll_y = value
        
    @property
    def filename(self) -> Optional[str]:
        """Get filename from the current tab"""
        return self.tabs[self.current_tab_index].filename
        
    @filename.setter
    def filename(self, value: Optional[str]) -> None:
        """Set filename for the current tab and update tab name"""
        self.tabs[self.current_tab_index].filename = value
        if value:
            # Update tab name to match the filename (without path)
            self.tabs[self.current_tab_index].name = os.path.basename(value)
            
    @property
    def history(self) -> History:
        """Get history from the current tab"""
        return self.tabs[self.current_tab_index].history
        
    @property
    def current_tab(self) -> Tab:
        """Get the current active tab"""
        return self.tabs[self.current_tab_index]
    
    @property
    def preferred_x(self) -> int:
        """Get preferred X position for the current tab"""
        return self.tabs[self.current_tab_index].preferred_x
        
    @preferred_x.setter
    def preferred_x(self, value: int) -> None:
        """Set preferred X position for the current tab"""
        self.tabs[self.current_tab_index].preferred_x = value
        
    # Tab management methods
    def create_tab(self, name: str = "Untitled", buffer: Optional[Buffer] = None, 
                  filename: Optional[str] = None, temporary: bool = False) -> int:
        """
        Create a new tab
        
        Args:
            name: Name/title for the tab
            buffer: Optional buffer to use
            filename: Optional filename
            temporary: Whether this is a temporary tab
            
        Returns:
            Index of the new tab
        """
        new_tab = Tab(name, buffer, filename)
        new_tab.is_temporary = temporary
        self.tabs.append(new_tab)
        return len(self.tabs) - 1
        
    def switch_to_tab(self, index: int) -> bool:
        """
        Switch to the specified tab
        
        Args:
            index: Tab index
            
        Returns:
            True if successful, False if index is invalid
        """
        if 0 <= index < len(self.tabs):
            self.current_tab_index = index
            return True
        return False
        
    def next_tab(self) -> None:
        """Switch to the next tab"""
        if len(self.tabs) > 1:
            self.current_tab_index = (self.current_tab_index + 1) % len(self.tabs)
            self.set_status_message(f"Tab: {self.current_tab.name}")
            
    def prev_tab(self) -> None:
        """Switch to the previous tab"""
        if len(self.tabs) > 1:
            self.current_tab_index = (self.current_tab_index - 1) % len(self.tabs)
            self.set_status_message(f"Tab: {self.current_tab.name}")
            
    def close_current_tab(self) -> bool:
        """
        Close the current tab
        
        Returns:
            True if successful, False otherwise (can't close last tab)
        """
        if len(self.tabs) <= 1:
            # Can't close the last tab
            self.set_status_message("Cannot close the last tab")
            return False
            
        # Remove the current tab
        del self.tabs[self.current_tab_index]
        
        # Adjust current index if needed
        if self.current_tab_index >= len(self.tabs):
            self.current_tab_index = len(self.tabs) - 1
            
        return True
      
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
    
    def save_file(self, filename: Optional[str] = None, create_backup: bool = True) -> None:
        """Save buffer content to a file with optional backup"""
        save_filename = filename or self.filename
        
        if not save_filename:
            self.set_status_message("No filename specified (use :w filename)")
            return
        
        try:
            # Check write permissions
            if os.path.exists(save_filename):
                if not os.access(save_filename, os.W_OK):
                    self.set_status_message(f"Permission denied: cannot write to {save_filename}")
                    return
                    
                # Create backup if enabled and file exists
                if create_backup and getattr(self, 'auto_backup', True):
                    from .utils import create_backup_file
                    backup_path = create_backup_file(save_filename)
                    if backup_path:
                        logging.info(f"Created backup: {backup_path}")
            
            content = self.buffer.get_content()
            
            # Write to temporary file first for safety
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(save_filename) or '.')
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    f.write(content)
                # Rename temp file to target
                os.replace(temp_path, save_filename)
            except:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
            
            self.buffer.mark_as_saved()
            self.filename = save_filename
            
            self.set_status_message(f"Saved: {save_filename} ({len(content)} bytes)")
            logging.info(f"Saved file: {save_filename}")
        except OSError as e:
            if e.errno == 28:  # ENOSPC - No space left on device
                self.set_status_message(f"Error: Disk full, cannot save {save_filename}")
            elif e.errno == 13:  # EACCES - Permission denied
                self.set_status_message(f"Permission denied: cannot write to {save_filename}")
            else:
                self.set_status_message(f"Error saving file: {str(e)}")
            logging.error(f"Error saving file: {str(e)}")
        except Exception as e:
            self.set_status_message(f"Error saving file: {str(e)}")
            logging.error(f"Error saving file: {str(e)}")
    
    def reload_file(self, force: bool = False) -> None:
        """Reload the current file from disk"""
        if not self.filename:
            raise ValueError("No file to reload")
            
        if not force and self.buffer.is_modified():
            raise ValueError("File has unsaved changes (use force=True to discard)")
            
        try:
            if not os.path.exists(self.filename):
                raise FileNotFoundError(f"File not found: {self.filename}")
                
            with open(self.filename, 'r') as f:
                content = f.read()
                self.buffer.set_content(content)
                self.buffer.mark_as_saved()
                
            self.set_status_message(f"Reloaded: {self.filename}")
            logging.info(f"Reloaded file: {self.filename}")
        except Exception as e:
            logging.error(f"Error reloading file: {str(e)}")
            raise
    
    def is_binary_file(self, filename: str) -> bool:
        """Check if a file is binary"""
        try:
            # Check if file exists
            if not os.path.exists(filename):
                return False
                
            # Read first 8192 bytes to check for binary content
            with open(filename, 'rb') as f:
                chunk = f.read(8192)
                
            # Check for null bytes (common in binary files)
            if b'\0' in chunk:
                return True
                
            # Check if the content is mostly non-text
            text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
            non_text = 0
            
            for byte in chunk:
                if byte not in text_chars:
                    non_text += 1
                    
            # If more than 30% non-text, consider it binary
            if len(chunk) > 0 and non_text / len(chunk) > 0.3:
                return True
                
            return False
        except Exception as e:
            logging.error(f"Error checking if file is binary: {str(e)}")
            return False
    
    def load_file_with_permissions_check(self, filename: str, force: bool = False) -> None:
        """Load a file with permissions and binary file checking"""
        try:
            # Expand path
            filename = os.path.expanduser(filename)
            
            # Check if switching files and current buffer has unsaved changes
            if not force and self.filename and self.buffer.is_modified():
                raise ValueError("Current buffer has unsaved changes")
            
            # Check if file is binary
            if self.is_binary_file(filename):
                raise ValueError(f"Cannot edit binary file: {filename}")
            
            # Check read permissions
            if os.path.exists(filename):
                if not os.access(filename, os.R_OK):
                    raise PermissionError(f"Permission denied: cannot read {filename}")
                    
                # Check if file is read-only
                if not os.access(filename, os.W_OK):
                    self.set_status_message(f"Warning: {filename} is read-only")
                    
            # Load the file
            self.load_file(filename)
            
            # Update tab name
            if hasattr(self, 'current_tab'):
                self.current_tab.name = os.path.basename(filename)
                
        except Exception as e:
            logging.error(f"Error loading file with permissions check: {str(e)}")
            raise
    
    def open_file_browser(self) -> None:
        """Open the file browser/explorer"""
        # Import here to avoid circular dependency
        from .file_browser import FileBrowser
        
        try:
            # Create and run the file browser
            browser = FileBrowser(self)
            selected_file = browser.browse()
            
            if selected_file:
                # Open the selected file
                self.load_file_with_permissions_check(selected_file)
                
        except ImportError:
            # If file_browser module doesn't exist yet, show a temporary implementation
            self.set_status_message("File browser not yet implemented")
        except Exception as e:
            logging.error(f"Error opening file browser: {str(e)}")
            self.set_status_message(f"Error opening file browser: {str(e)}")
    
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
        # Store current time for input handling throttling
        current_time = time.time()
        
        if key == curses.KEY_RESIZE:
            # Terminal was resized
            self._handle_resize()
            return
            
        # Check if we're in the middle of AI processing
        if self.ai_processing:
            # Allow Escape key to cancel AI processing 
            if key == 27:  # ESC key
                self._cancel_ai_processing()
                return
                
            # If AI processing is set to be blocking, block all other input
            if self.ai_blocking:
                return
                
            # If non-blocking, show status update periodically
            current_time = time.time()
            if (current_time - self.last_ai_status_update) > 2.0:  # Show update every 2 seconds
                elapsed_time = int(current_time - self.last_ai_status_update)
                self.set_status_message(f"AI processing in background... ({elapsed_time}s elapsed, press ESC to cancel)")
                self.last_ai_status_update = current_time
                
            # Continue processing input for non-blocking AI operations
        
        # Check if a model selector dialog is open and process keypress
        if self.display and self.display.is_dialog_open() and hasattr(self.display, 'model_callback'):
            # Process key and check if a model was selected
            model_selected = self.handle_model_selector_keypress(key)
            if model_selected:
                self.set_status_message(f"AI model set to: {model_selected}")
            return
            
        # Check if any regular dialog is open
        if self.display and self.display.is_dialog_open():
            # Handle dialog navigation keys
            if key == ord('d'):
                self.display.close_dialog()
                return
            elif key == curses.KEY_LEFT and curses.keyname(key).decode("utf-8").startswith("^"):
                self.display.prev_dialog_view()
                return
            elif key == curses.KEY_RIGHT and curses.keyname(key).decode("utf-8").startswith("^"):
                self.display.next_dialog_view()
                return
                
        # Skip too frequent key processing (throttle keyboard repeat)
        # Increase the throttle time to reduce screen refreshes
        if hasattr(self, '_last_input_time') and current_time - self._last_input_time < 0.03:
            # Skip if less than 30ms has passed since last input (very rapid typing)
            # This improves performance and reduces screen flickering
            return
        self._last_input_time = current_time
            
        # Handle input based on current mode
        if self.mode == "NORMAL":
            self._handle_normal_mode(key)
        elif self.mode == "INSERT":
            self._handle_insert_mode(key)
        elif self.mode == "VISUAL":
            self._handle_visual_mode(key)
        elif self.mode == "COMMAND":
            self._handle_command_mode(key)
        elif self.mode == "SEARCH":
            self.handle_search_input(key)
        elif self.mode == "NLP":
            # Initialize NLP handler on demand
            if not self.nlp_handler:
                from .nlp_mode import NLPHandler
                self.nlp_handler = NLPHandler(self)
                self.nlp_handler.enter_nlp_mode()
                
            # Let NLP handler process the key first
            if not self.nlp_handler.handle_key(key):
                # If not handled, process as in INSERT mode
                self._handle_insert_mode(key)
    
    def _handle_normal_mode(self, key: int) -> None:
        """Handle keypresses in normal mode"""
        if key == ord('i'):
            # Enter insert mode
            self.mode = "INSERT"
            self.set_status_message("-- INSERT --")
            
        elif key == ord('n'):
            # Check if this is for NLP mode or search
            if self.display and self.display.stdscr:
                self.display.stdscr.nodelay(True)  # Make getch non-blocking
                next_key = self.display.stdscr.getch()
                self.display.stdscr.nodelay(False)  # Restore blocking mode
                
                if next_key == ord('l'):
                    # Enter NLP mode ('nl' command)
                    self.mode = "NLP"
                    # NLP handler will be initialized when handling input
                    self.set_status_message("-- NLP MODE --")
                elif next_key != -1:
                    # Put the key back and treat 'n' as search next
                    curses.ungetch(next_key)
                    # Repeat last search
                    if self.search_pattern:
                        self._find_next_search_match()
                else:
                    # No key pressed quickly, treat as search next
                    if self.search_pattern:
                        self._find_next_search_match()
            
        elif key == ord('s'):
            # Delete current character and enter insert mode
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                # Delete character under cursor
                new_line = line[:self.cursor_x] + line[self.cursor_x+1:]
                self.buffer.set_line(self.cursor_y, new_line)
                
                # Enter insert mode
                self.mode = "INSERT"
                self.set_status_message("-- INSERT --")
        
        elif key == ord('G') or (key == ord('g') and curses.keyname(key).decode("utf-8").startswith("S-")):
            # Go to last line of the file (Shift+G)
            last_line_idx = len(self.buffer.get_lines()) - 1
            self.cursor_y = last_line_idx
            
            # Move cursor to the beginning of the line
            self.cursor_x = 0
            self.preferred_x = self.cursor_x
            
            # Update scroll position if necessary
            if self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
                self.scroll_y = max(0, self.cursor_y - self.display.max_text_height + 1)
                
            self.set_status_message(f"Line {self.cursor_y + 1} of {last_line_idx + 1}")
                
        elif key == ord('A') or (key == ord('a') and (curses.keyname(key).decode("utf-8").startswith("^") or curses.keyname(key).decode("utf-8").startswith("S-"))):
            # Go to end of line and enter insert mode (Shift+A)
            line = self.buffer.get_line(self.cursor_y)
            self.cursor_x = len(line)
            self.preferred_x = self.cursor_x
            self.mode = "INSERT"
            self.set_status_message("-- INSERT --")
        
        elif key == ord('x'):
            # Delete character under cursor
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                # Store current version in history
                self.history.add_version(self.buffer.get_lines())
                
                # Delete the character
                new_line = line[:self.cursor_x] + line[self.cursor_x+1:]
                self.buffer.set_line(self.cursor_y, new_line)
                
                # Store updated version in history
                self.history.add_version(self.buffer.get_lines())
                
                # Adjust cursor if at end of line
                if self.cursor_x >= len(new_line):
                    self.cursor_x = max(0, len(new_line))
                    self.preferred_x = self.cursor_x
        
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
        
        elif key == ord('/'):
            # Enter search mode for forward search
            self.enter_search_mode("forward")
        
        elif key == ord('?'):
            # Enter search mode for backward search
            self.enter_search_mode("backward")
        
                
        elif key == ord('N'):
            # Repeat last search in opposite direction (Shift+N)
            if self.search_pattern:
                self._find_next_search_match(opposite_direction=True)
                
        elif key == ord('*'):
            # Search for word under cursor (forward)
            self.search_word_under_cursor(backward=False)
            
        elif key == ord('#'):
            # Search for word under cursor (backward)
            self.search_word_under_cursor(backward=True)
            
        elif key == ord('o'):
            # Open new line below cursor and enter insert mode
            self._open_line_below()
            
        elif key == ord('O'):
            # Open new line above cursor and enter insert mode
            self._open_line_above()
            
        elif key == ord('p'):
            # Paste clipboard content after cursor
            if self.clipboard:
                # Store current version in history before paste
                self.history.add_version(self.buffer.get_lines())
                
                # Get the current line
                current_line = self.buffer.get_line(self.cursor_y)
                
                if len(self.clipboard) == 1:
                    # Single line paste - insert at cursor position on current line
                    new_line = current_line[:self.cursor_x] + self.clipboard[0] + current_line[self.cursor_x:]
                    self.buffer.set_line(self.cursor_y, new_line)
                    self.cursor_x += len(self.clipboard[0])
                    self.preferred_x = self.cursor_x
                else:
                    # Multi-line paste
                    # First line: combine with first part of current line
                    new_first_line = current_line[:self.cursor_x] + self.clipboard[0]
                    self.buffer.set_line(self.cursor_y, new_first_line)
                    
                    # Middle lines: insert as new lines
                    for i in range(1, len(self.clipboard) - 1):
                        self.buffer.insert_line(self.cursor_y + i, self.clipboard[i])
                    
                    # Last line: combine with second part of current line
                    last_clipboard_line = self.clipboard[-1]
                    new_last_line = last_clipboard_line + current_line[self.cursor_x:]
                    self.buffer.insert_line(self.cursor_y + len(self.clipboard) - 1, new_last_line)
                    
                    # Move cursor to end of pasted content
                    self.cursor_y += len(self.clipboard) - 1
                    self.cursor_x = len(last_clipboard_line)
                    self.preferred_x = self.cursor_x
                
                # Store updated version in history
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"Pasted {len(self.clipboard)} lines")
        
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
                if self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
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
        
        elif key == ord('d') and self.display and self.display.is_dialog_open():
            # Close dialog with 'd' key
            self.display.close_dialog()
            
        elif key == curses.KEY_LEFT and curses.keyname(key).decode("utf-8").startswith("^") and self.display and self.display.is_dialog_open():
            # Navigate to previous dialog view with Ctrl+Left
            self.display.prev_dialog_view()
            
        elif key == curses.KEY_RIGHT and curses.keyname(key).decode("utf-8").startswith("^") and self.display and self.display.is_dialog_open():
            # Navigate to next dialog view with Ctrl+Right
            self.display.next_dialog_view()
        
        elif key == ord('d'):
            # Delete operation - need another 'd' for line delete
            if self.display and self.display.stdscr:
                next_key = self.display.stdscr.getch()
            else:
                return
            if next_key == ord('d'):
                # Delete current line
                # Store line count before deletion
                line_count = 1
                
                # Check if there's a numeric prefix
                if hasattr(self, '_numeric_prefix') and self._numeric_prefix > 0:
                    line_count = self._numeric_prefix
                    self._numeric_prefix = 0
                
                # Delete the specified number of lines
                for _ in range(min(line_count, len(self.buffer.get_lines()))):
                    self.buffer.delete_line(self.cursor_y)
                
                # Adjust cursor position if needed
                if self.cursor_y >= len(self.buffer.get_lines()):
                    self.cursor_y = max(0, len(self.buffer.get_lines()) - 1)
                self._adjust_cursor_x()
                
                # Add to history
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"{line_count} line(s) deleted")
        
        # Handle numeric prefixes for commands like "5dd"
        elif key >= ord('0') and key <= ord('9'):
            digit = key - ord('0')
            if not hasattr(self, '_numeric_prefix'):
                self._numeric_prefix = 0
            
            if self._numeric_prefix == 0 and digit == 0:
                # Special case: '0' by itself means go to beginning of line
                self.cursor_x = 0
                self.preferred_x = 0
            else:
                # Build up the numeric prefix
                self._numeric_prefix = self._numeric_prefix * 10 + digit
                
    def _open_line_below(self) -> None:
        """
        Open a new line below the current line and enter insert mode (o command)
        """
        # Store current version in history first
        self.history.add_version(self.buffer.get_lines())
        
        # Insert a new empty line after the current line
        self.buffer.insert_line(self.cursor_y + 1, "")
        
        # Move cursor to the new line
        self.cursor_y += 1
        self.cursor_x = 0
        self.preferred_x = 0
        
        # Enter insert mode
        self.mode = "INSERT"
        self.set_status_message("-- INSERT --")
        
    def _open_line_above(self) -> None:
        """
        Open a new line above the current line and enter insert mode (O command)
        """
        # Store current version in history first
        self.history.add_version(self.buffer.get_lines())
        
        # Insert a new empty line before the current line
        self.buffer.insert_line(self.cursor_y, "")
        
        # Keep cursor at the same line number (but now on the new empty line)
        self.cursor_x = 0
        self.preferred_x = 0
        
        # Enter insert mode
        self.mode = "INSERT"
        self.set_status_message("-- INSERT --")
        
    def _start_search(self, pattern: str, direction: str = None, incremental: bool = False) -> None:
        """
        Start a search for the given pattern
        
        Args:
            pattern: The search pattern to find
            direction: Search direction ('forward' or 'backward'), uses current if None
            incremental: Whether this is an incremental search (for live preview)
        """
        # Parse search flags from pattern
        actual_pattern, flags = self._parse_search_pattern(pattern)
        
        # Store the search pattern
        self.search_pattern = actual_pattern
        
        # Update search direction if specified
        if direction:
            self.search_direction = direction
        
        # Apply flags
        if 'c' in flags:
            self.search_case_sensitive = False
        elif 'C' in flags:
            self.search_case_sensitive = True
        elif self.search_case_sensitive is None:
            # Smart case: case insensitive unless pattern has uppercase
            self.search_case_sensitive = any(c.isupper() for c in actual_pattern)
        
        if 'v' in flags:
            self.search_very_magic = True
        
        # Find all matches
        self.search_results = []
        self._perform_search(actual_pattern)
        
        # If we found matches, move to the first one (unless incremental)
        if self.search_results:
            if not incremental:
                self._find_next_search_match()
            match_count = len(self.search_results)
            current_idx = self.current_search_index + 1 if self.current_search_index >= 0 else 1
            self.set_status_message(f"[{current_idx}/{match_count}] matches for: {actual_pattern}")
        else:
            self.set_status_message(f"Pattern not found: {actual_pattern}")
    
    def _parse_search_pattern(self, pattern: str) -> Tuple[str, str]:
        """
        Parse search pattern and extract flags
        
        Args:
            pattern: The raw search pattern with possible flags
            
        Returns:
            Tuple of (actual_pattern, flags)
        """
        flags = ""
        actual_pattern = pattern
        
        # Check for flags at the beginning (e.g., \c, \C, \v)
        if pattern.startswith('\\'):
            parts = pattern.split(' ', 1)
            if len(parts) > 0:
                flag_part = parts[0]
                if 'c' in flag_part:
                    flags += 'c'
                if 'C' in flag_part:
                    flags += 'C'
                if 'v' in flag_part:
                    flags += 'v'
                # Remove flag prefix from pattern
                if len(parts) > 1:
                    actual_pattern = parts[1]
                elif len(flag_part) > 2:
                    actual_pattern = pattern[2:]
                else:
                    actual_pattern = ""
        
        return actual_pattern, flags
    
    def _perform_search(self, pattern: str) -> None:
        """
        Perform the actual search for the pattern
        
        Args:
            pattern: The search pattern (without flags)
        """
        if not pattern:
            return
            
        # Prepare regex pattern if needed
        if self.search_regex or self.search_very_magic:
            try:
                if self.search_very_magic:
                    # Very magic mode - most chars are special
                    regex_pattern = pattern
                else:
                    # Regular regex mode
                    regex_pattern = pattern
                    
                # Apply case sensitivity
                flags = 0 if self.search_case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(regex_pattern, flags)
            except re.error:
                # Invalid regex, fall back to literal search
                self.search_regex = False
                self.search_very_magic = False
        
        # Search through the buffer for all occurrences
        for y, line in enumerate(self.buffer.get_lines()):
            if self.search_regex or self.search_very_magic:
                # Regex search
                try:
                    for match in compiled_pattern.finditer(line):
                        self.search_results.append((y, match.start(), len(match.group())))
                except:
                    continue
            else:
                # Literal search
                search_line = line
                search_pat = pattern
                
                if not self.search_case_sensitive:
                    search_line = line.lower()
                    search_pat = pattern.lower()
                
                start_pos = 0
                while True:
                    pos = search_line.find(search_pat, start_pos)
                    if pos == -1:
                        break
                    
                    # Add this match to results (y, start_col, length)
                    self.search_results.append((y, pos, len(pattern)))
                    
                    # Move past this match for the next iteration
                    start_pos = pos + 1
            
    def _find_next_search_match(self, opposite_direction: bool = False) -> None:
        """
        Move to the next search match
        
        Args:
            opposite_direction: If True, search in the opposite direction from the current
        """
        if not self.search_results:
            self.set_status_message(f"No matches for: {self.search_pattern}")
            return
            
        # Determine search direction
        direction = self.search_direction
        if opposite_direction:
            direction = "backward" if direction == "forward" else "forward"
            
        # Find the match closest to cursor position in the appropriate direction
        cursor_pos = (self.cursor_y, self.cursor_x)
        
        if direction == "forward":
            # Find the next match after cursor position
            next_match_idx = None
            for i, match in enumerate(self.search_results):
                match_pos = (match[0], match[1])  # Extract position from match tuple
                if match_pos > cursor_pos:
                    next_match_idx = i
                    break
                    
            # Wrap around if needed
            if next_match_idx is None:
                next_match_idx = 0
                wrapped = True
            else:
                wrapped = False
        else:
            # Find the previous match before cursor position
            prev_match_idx = None
            for i in range(len(self.search_results) - 1, -1, -1):
                match = self.search_results[i]
                match_pos = (match[0], match[1])  # Extract position from match tuple
                if match_pos < cursor_pos:
                    prev_match_idx = i
                    break
                    
            # Wrap around if needed
            if prev_match_idx is None:
                prev_match_idx = len(self.search_results) - 1
                wrapped = True
            else:
                wrapped = False
                
            next_match_idx = prev_match_idx
        
        # Move cursor to the match
        if next_match_idx is not None and next_match_idx < len(self.search_results):
            match = self.search_results[next_match_idx]
            self.cursor_y = match[0]
            self.cursor_x = match[1]
            self.current_search_index = next_match_idx
            self.preferred_x = self.cursor_x
            
            # Update status message
            match_count = len(self.search_results)
            current_idx = self.current_search_index + 1
            status_msg = f"[{current_idx}/{match_count}] matches"
            if wrapped:
                status_msg += " (wrapped)"
            self.set_status_message(status_msg)
            
            # Ensure match is visible
            if self.cursor_y < self.scroll_y:
                self.scroll_y = self.cursor_y
            elif self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
                self.scroll_y = self.cursor_y - self.display.max_text_height + 1
    
    def search_word_under_cursor(self, backward: bool = False) -> None:
        """
        Search for the word under the cursor (* and # commands)
        
        Args:
            backward: Whether to search backward (#) or forward (*)
        """
        # Get the word under cursor
        if self.cursor_y >= len(self.buffer.get_lines()):
            return
            
        line = self.buffer.get_line(self.cursor_y)
        if self.cursor_x >= len(line):
            return
            
        # Find word boundaries
        start = self.cursor_x
        end = self.cursor_x
        
        # Move start to beginning of word
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
            
        # Move end to end of word
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
            
        if start == end:
            self.set_status_message("No word under cursor")
            return
            
        # Get the word and search for it
        word = line[start:end]
        # Add word boundaries to pattern
        pattern = f"\\b{re.escape(word)}\\b"
        
        # Set search direction and start search
        self.search_direction = "backward" if backward else "forward"
        self.search_regex = True
        self._start_search(pattern)
    
    def clear_search_highlights(self) -> None:
        """
        Clear search highlights (:noh command)
        """
        self.search_highlighting = False
        self.search_results = []
        self.current_search_index = -1
        self.set_status_message("Search highlighting cleared")
    
    def enter_search_mode(self, direction: str) -> None:
        """
        Enter search mode (/ or ? commands)
        
        Args:
            direction: 'forward' or 'backward'
        """
        self.search_input_mode = True
        self.search_direction = direction
        self.search_input_buffer = ""
        self.search_cursor_pos = 0
        self.mode = "SEARCH"
        
        # Show search prompt in status line
        prompt = "/" if direction == "forward" else "?"
        self.set_status_message(prompt)
    
    def handle_search_input(self, key: int) -> None:
        """
        Handle input while in search mode
        
        Args:
            key: The key code
        """
        if key == 27:  # Escape - cancel search
            self.search_input_mode = False
            self.mode = "NORMAL"
            self.set_status_message("")
            
        elif key == 10 or key == 13:  # Enter - execute search
            if self.search_input_buffer:
                self._start_search(self.search_input_buffer)
            self.search_input_mode = False
            self.mode = "NORMAL"
            
        elif key == 127 or key == curses.KEY_BACKSPACE:  # Backspace
            if self.search_cursor_pos > 0:
                self.search_input_buffer = (
                    self.search_input_buffer[:self.search_cursor_pos - 1] + 
                    self.search_input_buffer[self.search_cursor_pos:]
                )
                self.search_cursor_pos -= 1
                self._update_search_display()
                # Incremental search
                if self.search_input_buffer:
                    self._start_search(self.search_input_buffer, incremental=True)
                    
        elif key == curses.KEY_LEFT:
            if self.search_cursor_pos > 0:
                self.search_cursor_pos -= 1
                self._update_search_display()
                
        elif key == curses.KEY_RIGHT:
            if self.search_cursor_pos < len(self.search_input_buffer):
                self.search_cursor_pos += 1
                self._update_search_display()
                
        elif 32 <= key <= 126:  # Printable character
            self.search_input_buffer = (
                self.search_input_buffer[:self.search_cursor_pos] +
                chr(key) +
                self.search_input_buffer[self.search_cursor_pos:]
            )
            self.search_cursor_pos += 1
            self._update_search_display()
            # Incremental search
            if self.search_input_buffer:
                self._start_search(self.search_input_buffer, incremental=True)
    
    def _update_search_display(self) -> None:
        """Update the search prompt display"""
        prompt = "/" if self.search_direction == "forward" else "?"
        self.set_status_message(f"{prompt}{self.search_input_buffer}")
    
    def substitute(self, pattern: str, replacement: str, line_range: Tuple[int, int] = None,
                  global_flag: bool = False, confirm: bool = False) -> int:
        """
        Perform substitution/replacement
        
        Args:
            pattern: The pattern to search for
            replacement: The replacement text
            line_range: Tuple of (start_line, end_line) 0-indexed, None for current line
            global_flag: Whether to replace all occurrences in each line
            confirm: Whether to ask for confirmation for each replacement
            
        Returns:
            Number of substitutions made
        """
        # Store current version in history
        self.history.add_version(self.buffer.get_lines())
        
        # Determine line range
        if line_range is None:
            # Current line only
            start_line = self.cursor_y
            end_line = self.cursor_y
        else:
            start_line, end_line = line_range
            
        # Ensure valid range
        lines = self.buffer.get_lines()
        start_line = max(0, min(start_line, len(lines) - 1))
        end_line = max(0, min(end_line, len(lines) - 1))
        
        substitution_count = 0
        
        # Parse search flags from pattern
        actual_pattern, flags = self._parse_search_pattern(pattern)
        
        # Apply flags
        case_sensitive = self.search_case_sensitive
        if 'c' in flags:
            case_sensitive = False
        elif 'C' in flags:
            case_sensitive = True
        elif case_sensitive is None:
            # Smart case
            case_sensitive = any(c.isupper() for c in actual_pattern)
        
        is_regex = self.search_regex or self.search_very_magic or 'v' in flags
        
        # Prepare regex if needed
        if is_regex:
            try:
                regex_flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(actual_pattern, regex_flags)
            except re.error:
                self.set_status_message(f"Invalid regex pattern: {actual_pattern}")
                return 0
        
        # Perform substitution on each line in range
        for line_num in range(start_line, end_line + 1):
            line = self.buffer.get_line(line_num)
            new_line = line
            line_substitutions = 0
            
            if is_regex:
                # Regex substitution
                if global_flag:
                    if confirm:
                        # Confirm each replacement
                        matches = list(compiled_pattern.finditer(line))
                        offset = 0
                        for match in matches:
                            # Show the match and ask for confirmation
                            self.cursor_y = line_num
                            self.cursor_x = match.start() + offset
                            self._update_display()
                            
                            # Ask for confirmation (simplified version)
                            self.set_status_message(f"Replace '{match.group()}' with '{replacement}'? (y/n/a/q)")
                            if self.display:
                                response = self.display.stdscr.getch()
                                if response == ord('y'):
                                    # Replace this occurrence
                                    new_text = compiled_pattern.sub(replacement, match.group())
                                    new_line = new_line[:match.start() + offset] + new_text + new_line[match.end() + offset:]
                                    offset += len(new_text) - len(match.group())
                                    line_substitutions += 1
                                elif response == ord('n'):
                                    # Skip this occurrence
                                    continue
                                elif response == ord('a'):
                                    # Replace all remaining without asking
                                    new_line = compiled_pattern.sub(replacement, new_line)
                                    line_substitutions = len(matches)
                                    break
                                elif response == ord('q'):
                                    # Quit substitution
                                    break
                    else:
                        # Replace all occurrences
                        new_line, count = compiled_pattern.subn(replacement, line)
                        line_substitutions = count
                else:
                    # Replace only first occurrence
                    new_line, count = compiled_pattern.subn(replacement, line, count=1)
                    line_substitutions = count
            else:
                # Literal substitution
                search_pat = actual_pattern
                if not case_sensitive:
                    # Case-insensitive literal search
                    search_line = line.lower()
                    search_pat = actual_pattern.lower()
                    
                    if global_flag:
                        # Replace all occurrences
                        positions = []
                        start_pos = 0
                        while True:
                            pos = search_line.find(search_pat, start_pos)
                            if pos == -1:
                                break
                            positions.append((pos, pos + len(search_pat)))
                            start_pos = pos + 1
                        
                        # Replace from end to start to preserve positions
                        for start, end in reversed(positions):
                            new_line = new_line[:start] + replacement + new_line[end:]
                            line_substitutions += 1
                    else:
                        # Replace first occurrence only
                        pos = search_line.find(search_pat)
                        if pos != -1:
                            new_line = line[:pos] + replacement + line[pos + len(actual_pattern):]
                            line_substitutions = 1
                else:
                    # Case-sensitive literal search
                    if global_flag:
                        new_line = line.replace(actual_pattern, replacement)
                        line_substitutions = line.count(actual_pattern)
                    else:
                        # Replace first occurrence only
                        pos = line.find(actual_pattern)
                        if pos != -1:
                            new_line = line[:pos] + replacement + line[pos + len(actual_pattern):]
                            line_substitutions = 1
            
            # Update the line if changed
            if line_substitutions > 0:
                self.buffer.set_line(line_num, new_line)
                substitution_count += line_substitutions
        
        # Store updated version in history
        if substitution_count > 0:
            self.history.add_version(self.buffer.get_lines())
            
        # Report results
        if substitution_count == 0:
            self.set_status_message(f"Pattern not found: {actual_pattern}")
        else:
            lines_affected = end_line - start_line + 1
            self.set_status_message(f"{substitution_count} substitution(s) on {lines_affected} line(s)")
            
        return substitution_count
    
    def _handle_insert_mode(self, key: int) -> None:
        """Handle keypresses in insert mode"""
        if key == 27:  # Escape key
            # Return to normal mode
            self.mode = "NORMAL"
            # Add current buffer state to history
            self.history.add_version(self.buffer.get_lines())
            self.set_status_message("")
            
        # Ctrl+X + Ctrl+N shortcut removed as requested
                
        elif key == 22:  # Ctrl+V (22 is ASCII for SYN - synchronous idle, typically sent by Ctrl+V)
            # Paste from clipboard in insert mode
            if self.clipboard:
                # Store current version in history before paste
                self.history.add_version(self.buffer.get_lines())
                
                # Get the current line
                current_line = self.buffer.get_line(self.cursor_y)
                
                if len(self.clipboard) == 1:
                    # Single line paste - insert at cursor position on current line
                    new_line = current_line[:self.cursor_x] + self.clipboard[0] + current_line[self.cursor_x:]
                    self.buffer.set_line(self.cursor_y, new_line)
                    self.cursor_x += len(self.clipboard[0])
                    self.preferred_x = self.cursor_x
                else:
                    # Multi-line paste
                    # First line: combine with first part of current line
                    new_first_line = current_line[:self.cursor_x] + self.clipboard[0]
                    self.buffer.set_line(self.cursor_y, new_first_line)
                    
                    # Middle lines: insert as new lines
                    for i in range(1, len(self.clipboard) - 1):
                        self.buffer.insert_line(self.cursor_y + i, self.clipboard[i])
                    
                    # Last line: combine with second part of current line
                    last_clipboard_line = self.clipboard[-1]
                    new_last_line = last_clipboard_line + current_line[self.cursor_x:]
                    self.buffer.insert_line(self.cursor_y + len(self.clipboard) - 1, new_last_line)
                    
                    # Move cursor to end of pasted content
                    self.cursor_y += len(self.clipboard) - 1
                    self.cursor_x = len(last_clipboard_line)
                    self.preferred_x = self.cursor_x
                
                # Store updated version in history
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"Pasted {len(self.clipboard)} lines")
        
        elif key == 65:  # ASCII 'A' (likely Shift+A)
            # Go to end of line and remain in insert mode (Shift+A equivalent)
            line = self.buffer.get_line(self.cursor_y)
            self.cursor_x = len(line)
            self.preferred_x = self.cursor_x
        
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
                if self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
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
            if self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
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
            if self.display:
                self.cursor_y = max(0, self.cursor_y - self.display.max_text_height)
                self.scroll_y = max(0, self.scroll_y - self.display.max_text_height)
            else:
                # Fallback when display is not available
                self.cursor_y = max(0, self.cursor_y - 20)
                self.scroll_y = max(0, self.scroll_y - 20)
            self._adjust_cursor_x()
        
        elif key == curses.KEY_NPAGE:  # Page Down
            # Move down a page
            max_y = len(self.buffer.get_lines()) - 1
            if self.display:
                self.cursor_y = min(max_y, self.cursor_y + self.display.max_text_height)
                self.scroll_y = min(max_y - self.display.max_text_height + 1, 
                                   self.scroll_y + self.display.max_text_height)
            else:
                # Fallback when display is not available
                self.cursor_y = min(max_y, self.cursor_y + 20)
                self.scroll_y = min(max_y - 20 + 1, self.scroll_y + 20)
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
                if self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
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
            
            # Ensure the clipboard isn't empty (can happen with empty selections)
            if not self.clipboard:
                self.clipboard = [""]
                
            # Log the clipboard contents for debugging
            logging.info(f"Clipboard contents: {self.clipboard}")
            
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
        # Ensure the command line is visible
        if self.display:
            self.display.update_command_line(self.command_buffer, self.command_cursor)
        
        if key == 27:  # Escape key
            # Return to normal mode
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.command_cursor = 0
            self.set_status_message("")
        
        elif key == curses.KEY_BACKSPACE or key == 127:
            # Backspace
            if self.command_cursor > 1:  # Keep the initial character (':', '/', or '?')
                self.command_buffer = (
                    self.command_buffer[:self.command_cursor-1] + 
                    self.command_buffer[self.command_cursor:]
                )
                self.command_cursor -= 1
                # Immediately show the change
                if self.display:
                    self.display.update_command_line(self.command_buffer, self.command_cursor)
        
        elif key == curses.KEY_LEFT:
            # Move cursor left
            if self.command_cursor > 1:  # Don't move past the initial character
                self.command_cursor -= 1
                # Immediately show the change
                if self.display:
                    self.display.update_command_line(self.command_buffer, self.command_cursor)
        
        elif key == curses.KEY_RIGHT:
            # Move cursor right
            if self.command_cursor < len(self.command_buffer):
                self.command_cursor += 1
                # Immediately show the change
                if self.display:
                    self.display.update_command_line(self.command_buffer, self.command_cursor)
        
        elif key == curses.KEY_HOME:
            # Move to beginning of command (after the initial character)
            self.command_cursor = 1
            # Immediately show the change
            if self.display:
                self.display.update_command_line(self.command_buffer, self.command_cursor)
        
        elif key == curses.KEY_END:
            # Move to end of command
            self.command_cursor = len(self.command_buffer)
            # Immediately show the change
            if self.display:
                self.display.update_command_line(self.command_buffer, self.command_cursor)
        
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
            # Immediately show the change
            if self.display:
                self.display.update_command_line(self.command_buffer, self.command_cursor)
    
    def _process_command(self) -> None:
        """Process entered command"""
        command = self.command_buffer
        
        # Check if this is a search command
        if command.startswith('/'):
            # Forward search
            pattern = command[1:]
            if pattern:
                self._start_search(pattern)
            # Return to normal mode
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.command_cursor = 0
            return
            
        elif command.startswith('?'):
            # Backward search
            pattern = command[1:]
            if pattern:
                self.search_direction = "backward"
                self._start_search(pattern)
            # Return to normal mode
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.command_cursor = 0
            return
            
        elif command.startswith(':'):
            # Check for substitution command
            if command.startswith(':%s/'):
                # Global substitution: :%s/pattern/replacement/g
                try:
                    # Parse the command
                    parts = command[4:].split('/')
                    if len(parts) >= 3:
                        pattern = parts[0]
                        replacement = parts[1]
                        
                        # Check for flags
                        global_replace = False
                        if len(parts) > 3 and 'g' in parts[2]:
                            global_replace = True
                            
                        # Do the replacement
                        self._replace_text(pattern, replacement, global_replace)
                        
                        # Return to normal mode
                        self.mode = "NORMAL"
                        self.command_buffer = ""
                        self.command_cursor = 0
                        return
                except Exception as e:
                    # Handle any errors
                    self.set_status_message(f"Error in substitution: {str(e)}")
                    self.mode = "NORMAL"
                    self.command_buffer = ""
                    self.command_cursor = 0
                    return
                    
            # Check for line navigation commands: ":123" or ":$"
            line_number_match = re.match(r':(\d+)$', command)
            last_line_match = re.match(r':\$$', command)
            
            if line_number_match:
                # Navigate to specified line number
                try:
                    line_number = int(line_number_match.group(1))
                    self._navigate_to_line(line_number - 1)  # Convert to 0-based index
                    
                    # Return to normal mode
                    self.mode = "NORMAL"
                    self.command_buffer = ""
                    self.command_cursor = 0
                    return
                except Exception as e:
                    # Handle any errors
                    self.set_status_message(f"Error navigating to line: {str(e)}")
                    self.mode = "NORMAL"
                    self.command_buffer = ""
                    self.command_cursor = 0
                    return
                    
            elif last_line_match:
                # Navigate to last line
                self._navigate_to_line(len(self.buffer.get_lines()) - 1)
                
                # Return to normal mode
                self.mode = "NORMAL"
                self.command_buffer = ""
                self.command_cursor = 0
                return
            
            # If not a special command, handle as a normal command
            if self.command_handler:
                result = self.command_handler.execute(command[1:])  # Remove the leading ':'
            else:
                result = False
            
            # Return to normal mode
            self.mode = "NORMAL"
            self.command_buffer = ""
            self.command_cursor = 0
            
            if not result:
                self.set_status_message(f"Invalid command")
                
    def _replace_text(self, pattern: str, replacement: str, global_replace: bool = False) -> None:
        """
        Replace all occurrences of pattern with replacement
        
        Args:
            pattern: The pattern to search for
            replacement: The text to replace it with
            global_replace: If True, replace all occurrences in each line, otherwise just the first
        """
        # Store buffer state in history
        self.history.add_version(self.buffer.get_lines())
        
        # Track the number of replacements
        num_replacements = 0
        
        # Process each line in the buffer
        for y, line in enumerate(self.buffer.get_lines()):
            if global_replace:
                # Replace all occurrences in the line
                new_line = line.replace(pattern, replacement)
                # Count how many replacements were made
                num_replacements += line.count(pattern)
            else:
                # Replace only the first occurrence
                pos = line.find(pattern)
                if pos != -1:
                    new_line = line[:pos] + replacement + line[pos + len(pattern):]
                    num_replacements += 1
                else:
                    new_line = line
                    
            # Update the line in the buffer
            if new_line != line:
                self.buffer.set_line(y, new_line)
        
        # Set status message
        self.set_status_message(f"Replaced {num_replacements} occurrences")
    
    def _update_display(self) -> None:
        """Update the display with current buffer content"""
        # Only update if display is initialized
        if not self.display:
            return
        
        # Check if we're in a dialog
        if self.display.is_dialog_open():
            # Only handle dialog close key
            return
            
        # Prevent too frequent updates (debouncing)
        current_time = time.time()
        if hasattr(self, '_last_update_time') and current_time - self._last_update_time < 0.1:
            # Skip update if less than 100ms has passed since last update
            # This significantly reduces screen flicker during rapid typing
            # A longer delay is acceptable for display updates since they're less critical than input handling
            return
        
        # Check if current state is the same as the last update (content, cursor, scroll position)
        if hasattr(self, '_last_display_state'):
            current_state = (
                self.cursor_y, self.cursor_x, self.scroll_y,
                self.mode, len(self.buffer.get_lines()),
                self.buffer.is_modified()
            )
            if self._last_display_state == current_state:
                # Skip update if nothing significant has changed
                return
            self._last_display_state = current_state
        else:
            # Initialize state tracking
            self._last_display_state = (
                self.cursor_y, self.cursor_x, self.scroll_y,
                self.mode, len(self.buffer.get_lines()),
                self.buffer.is_modified()
            )
            
        self._last_update_time = current_time
        
        # Update status line with tab information
        tab_info = ""
        if len(self.tabs) > 1:
            tab_names = []
            for i, tab in enumerate(self.tabs):
                if i == self.current_tab_index:
                    tab_names.append(f"[{tab.name}]")
                else:
                    tab_names.append(f" {tab.name} ")
            tab_info = " ".join(tab_names) + " | "
                
        self.display.update_status(
            f"{tab_info}{self.filename or '[No Name]'} "
            f"{'[+]' if self.buffer.is_modified() else ''} "
            f"Line {self.cursor_y+1}/{len(self.buffer.get_lines())} "
            f"Col {self.cursor_x+1} "
            f"{self.status_message}"
        )
        
        # Get the current AI model information
        model_info = ""
        if hasattr(self, 'ai_service'):
            model_info = self.ai_service.get_current_model_info() or ""
        
        # Update mode indicator with model info
        if self.mode == "NLP":
            # For NLP mode, add an indicator
            mode_display = f"{self.mode} [NL→CODE]"
            self.display.update_mode(mode_display, model_info)
        else:
            self.display.update_mode(self.mode, model_info)
        
        # Update text content
        if self.display:
            selection = self.buffer.get_selection()
            # Only pass selection if both parts are not None
            if selection and selection[0] is not None and selection[1] is not None:
                # Create a new tuple with the proper type
                validated_selection = (selection[0], selection[1])
                self.display.update_text(
                    self.buffer.get_lines(),
                    self.cursor_y,
                    self.cursor_x,
                    self.scroll_y,
                    validated_selection,
                    self.search_results if self.search_highlighting else None,
                    self.current_search_index,
                    editor=self
                )
            else:
                self.display.update_text(
                    self.buffer.get_lines(),
                    self.cursor_y,
                    self.cursor_x,
                    self.scroll_y,
                    None,
                    self.search_results if self.search_highlighting else None,
                    self.current_search_index,
                    editor=self
                )
        
        # Update command line if in command mode
        if self.mode == "COMMAND" and self.display:
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
            if self.display:
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
        
        # Show config status if available
        if hasattr(self, 'ai_service'):
            config_status = self.ai_service.get_config_status()
            model_info = self.ai_service.get_current_model_info()
            
            if config_status["loaded"]:
                self.set_status_message(f"Config loaded from {config_status['path']}. Using model: {model_info}")
            else:
                self.set_status_message(f"{config_status['message']}. Using model: {model_info}")
        else:
            # Default initial status message if AI service isn't initialized
            if self.filename:
                self.set_status_message(f"Editing: {self.filename}")
            else:
                self.set_status_message("No file opened")
            
        # Performance optimization message has been removed as requested
    
    def _adjust_cursor_x(self) -> None:
        """Adjust cursor x position when moving vertically"""
        line = self.buffer.get_line(self.cursor_y)
        self.cursor_x = min(self.preferred_x, len(line))
        
    def _navigate_to_line(self, line_number: int) -> None:
        """
        Navigate to a specific line number (0-based)
        
        Args:
            line_number: Zero-based line number to navigate to
        """
        # Validate and clamp line number to valid range
        max_line = max(0, len(self.buffer.get_lines()) - 1)
        line_number = max(0, min(line_number, max_line))
        
        # Set cursor position at the start of the specified line
        self.cursor_y = line_number
        self.cursor_x = 0
        self.preferred_x = 0
        
        # Adjust scroll position if needed
        if self.display:
            if self.cursor_y < self.scroll_y:
                self.scroll_y = self.cursor_y
            elif self.display and self.cursor_y >= self.scroll_y + self.display.max_text_height:
                self.scroll_y = self.cursor_y - self.display.max_text_height + 1
                
        # Set status message
        if line_number == max_line:
            self.set_status_message(f"Moved to last line ({line_number + 1})")
        else:
            self.set_status_message(f"Moved to line {line_number + 1}")
    
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
    
    def run_ai_command(self, command: str, args: List[str], blocking: bool = False) -> None:
        """
        Run an AI-related command in a separate thread
        
        Args:
            command: The AI command to run (generate, explain, improve, query)
            args: Arguments for the command
            blocking: If True, AI operations will block UI input until complete
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        # Select appropriate AI command based on the command name
        if command == "generate" and len(args) >= 2:
            line_num = int(args[0]) - 1  # Convert to 0-based
            description = " ".join(args[1:])
            self.ai_generate(line_num, description, blocking=blocking)
        elif command == "explain" and len(args) >= 2:
            start_line = int(args[0]) - 1  # Convert to 0-based
            end_line = int(args[1]) - 1  # Convert to 0-based
            self.ai_explain(start_line, end_line, blocking=blocking)
        elif command == "improve" and len(args) >= 2:
            start_line = int(args[0]) - 1  # Convert to 0-based
            end_line = int(args[1]) - 1  # Convert to 0-based
            self.ai_improve(start_line, end_line, blocking=blocking)
        elif command == "query":
            query = " ".join(args)
            self.ai_custom_query(query, blocking=blocking)
        elif command == "analyze" and len(args) >= 2:
            start_line = int(args[0]) - 1  # Convert to 0-based
            end_line = int(args[1]) - 1  # Convert to 0-based
            self.ai_analyze_code(start_line, end_line, blocking=blocking)
        else:
            self.set_status_message(f"Unknown AI command: {command}")
    
    def ai_generate(self, start_line: int, description: str, blocking: bool = False) -> None:
        """
        Generate code at the specified line based on description
        
        Args:
            start_line: Line number where code should be inserted (0-based)
            description: Description of what to generate
            blocking: If True, block UI until AI completes, otherwise allow editing
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
        self.ai_blocking = blocking
        self.last_ai_status_update = time.time()
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI generating code")
        else:
            status_msg = "AI generating code..." + (" (blocking)" if blocking else " (background)")
            self.set_status_message(status_msg)
        
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
                
                # Create a new tab with the generated code
                lines = generated_code.strip().split("\n")
                
                # Generate a descriptive tab name based on description
                timestamp = time.strftime("%Y%m%d%H%M%S")
                short_desc = description.split()[:3]  # First 3 words of description
                short_desc = "_".join(short_desc)[:20]  # Limit length
                tab_name = f"AI_{short_desc}_{timestamp}"
                
                # Create a new buffer with the generated code
                new_buffer = Buffer()
                new_buffer.set_lines(lines)
                
                # Create a docstring at the top of the file to describe what was generated
                docstring = [
                    f"""Generated by AIVim
                    Description: {description}
                    Date: {time.strftime('%Y-%m-%d %H:%M:%S')}
                    """
                ]
                
                # Add the docstring to the buffer before the code
                for i, line in enumerate(docstring):
                    new_buffer.insert_line(i, line)
                
                # Create the new tab
                tab_index = self.create_tab(tab_name, new_buffer)
                
                # Switch to the new tab
                self.switch_to_tab(tab_index)
                
                # Add model info to status message if available
                model_info = ""
                if hasattr(self, 'ai_service'):
                    model_info = self.ai_service.get_current_model_info()
                    if model_info:
                        model_info = f" using {model_info}"
                
                # Update status
                self.ai_processing = False
                self.set_status_message(f"Generated {len(lines)} lines of code{model_info} in new tab")
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error generating code: {str(e)}")
            logging.error(f"AI generation error: {str(e)}")
    
    def ai_explain(self, start_line: int, end_line: int, blocking: bool = False) -> None:
        """
        Explain code in the specified line range
        
        Args:
            start_line: Starting line number (0-based)
            end_line: Ending line number (0-based)
            blocking: If True, block UI until AI completes, otherwise allow editing
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
        self.ai_blocking = blocking
        self.last_ai_status_update = time.time()
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI explaining code")
        else:
            status_msg = "AI explaining code..." + (" (blocking)" if blocking else " (background)")
            self.set_status_message(status_msg)
        
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
                if self.display:
                    self.display.show_dialog("Code Explanation", explanation_lines)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error explaining code: {str(e)}")
            logging.error(f"AI explanation error: {str(e)}")
    
    def ai_improve(self, start_line: int, end_line: int, blocking: bool = False) -> None:
        """
        Improve code in the specified line range
        
        Args:
            start_line: Starting line number (0-based)
            end_line: Ending line number (0-based)
            blocking: If True, block UI until AI completes, otherwise allow editing
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
        self.ai_blocking = blocking
        self.last_ai_status_update = time.time()
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI improving code")
        else:
            status_msg = "AI improving code..." + (" (blocking)" if blocking else " (background)")
            self.set_status_message(status_msg)
        
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
            # Get the AI improvement with the new structured format
            improvement = self.ai_service.get_improvement(code, context)
            
            # Parse the structured response
            explanation_text = ""
            improved_code = code  # Default to original code if parsing fails
            
            # Check if we have the expected format with separate sections
            if "# EXPLANATION" in improvement and "# IMPROVED_CODE" in improvement:
                # Extract the explanation section
                explanation_start = improvement.find("# EXPLANATION")
                improved_code_start = improvement.find("# IMPROVED_CODE")
                
                if explanation_start >= 0 and improved_code_start > explanation_start:
                    # Get the explanation part
                    explanation_text = improvement[explanation_start + len("# EXPLANATION"):improved_code_start].strip()
                    
                    # Get the improved code part
                    improved_code = improvement[improved_code_start + len("# IMPROVED_CODE"):].strip()
            else:
                # Fallback: try to extract code from markdown code blocks
                import re
                code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', improvement, re.DOTALL)
                if code_blocks:
                    # Use the largest code block
                    improved_code = max(code_blocks, key=len)
                    # Everything else is potentially explanation
                    explanation_text = improvement
            
            # Split into lines
            improved_lines = improved_code.strip().split("\n")
            explanation_lines = explanation_text.split("\n")
            
            # Clean up the explanation lines
            if explanation_lines:
                # Remove empty lines at the beginning and end
                while explanation_lines and not explanation_lines[0].strip():
                    explanation_lines.pop(0)
                while explanation_lines and not explanation_lines[-1].strip():
                    explanation_lines.pop()
                
                # Remove markdown code blocks from explanation
                explanation_lines = [line for line in explanation_lines 
                                   if not line.strip().startswith("```")]
            
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
                
                # Store the improvement for confirmation
                self.pending_ai_action = {
                    "type": "improve",
                    "start_line": start_line,
                    "end_line": end_line,
                    "new_code": improved_code,
                    "metadata": metadata
                }
                
                # Prepare all views needed for the multi-view dialog
                if self.display:
                    # Original code view
                    original_code_lines = code.split("\n")
                    
                    # Improved code view
                    improved_code_lines = improved_code.split("\n")
                    
                    # Build a clean, structured set of views
                    views = [
                        {"title": "Original Code", "content": original_code_lines},
                        {"title": "AI Improved Code", "content": improved_code_lines},
                        {"title": "Code Improvement Diff", "content": diff_lines},
                    ]
                    
                    # Show multi-view dialog with explanation as a separate view
                    self.display.show_multi_view_dialog(
                        views=views,
                        explanation=explanation_lines if explanation_lines else None,
                        default_view=1  # Show the AI Improved Code by default
                    )
                
                # Set status message to prompt user for confirmation
                self.set_status_message(f"Review changes and use :y to accept or :n to reject ({len(improved_lines)} lines)")
                
                # Note: The actual application of changes will happen when the user
                # confirms with :y command, which will call confirm_ai_action(True)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error improving code: {str(e)}")
            logging.error(f"AI improvement error: {str(e)}")
    
    def ai_analyze_code(self, start_line: int, end_line: int, blocking: bool = False) -> None:
        """
        Analyze code complexity and identify potential bugs in the specified line range
        
        Args:
            start_line: Starting line number (0-based)
            end_line: Ending line number (0-based)
            blocking: If True, block UI until AI completes, otherwise allow editing
        """
        if self.ai_processing:
            self.set_status_message("AI is already processing a request")
            return
        
        # Get the code to analyze
        lines = self.buffer.get_lines()
        if not lines or start_line > end_line or end_line >= len(lines):
            self.set_status_message("Invalid line range")
            return
        
        # Extract the selected lines
        code_lines = lines[start_line:end_line+1]
        code = "\n".join(code_lines)
        
        # Get surrounding context (up to 20 lines before and after)
        context_start = max(0, start_line - 20)
        context_end = min(len(lines) - 1, end_line + 20)
        context_lines = lines[context_start:context_end+1]
        context = "\n".join(context_lines)
        
        # Setup metadata
        metadata = {
            "command": "analyze_code",
            "start_line": start_line,
            "end_line": end_line,
        }
        
        # Mark as processing
        self.ai_processing = True
        self.ai_blocking = blocking
        self.last_ai_status_update = time.time()
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI analyzing code complexity and bugs")
        else:
            status_msg = "AI analyzing code..." + (" (blocking)" if blocking else " (background)")
            self.set_status_message(status_msg)
        
        # Run in a separate thread
        self.ai_thread = threading.Thread(
            target=self._ai_analyze_code_thread,
            args=(code, context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _ai_analyze_code_thread(self, code: str, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI code analysis"""
        try:
            analysis = self.ai_service.analyze_code(code, context)
            
            # Show the analysis in a dialog
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                # Split into lines
                analysis_lines = analysis.split("\n")
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Code analysis complete")
                
                # Show dialog
                if self.display:
                    self.display.show_dialog("Code Analysis Results", analysis_lines)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error analyzing code: {str(e)}")
            logging.error(f"AI analysis error: {str(e)}")
    
    def ai_custom_query(self, query: str, blocking: bool = False) -> None:
        """
        Run a custom AI query on the current buffer
        
        Args:
            query: The query string
            blocking: If True, block UI until AI completes, otherwise allow editing
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
        self.ai_blocking = blocking
        self.last_ai_status_update = time.time()
        
        # Start loading animation
        if self.display:
            self.display.start_loading_animation("AI processing query")
        else:
            self.set_status_message("AI processing query..." + (" (blocking)" if blocking else " (background)"))
        
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
                if self.display:
                    self.display.show_dialog("Query Response", response_lines)
        
        except Exception as e:
            with self.thread_lock:
                # Stop loading animation if active
                if self.display:
                    self.display.stop_loading_animation()
                
                self.ai_processing = False
                self.set_status_message(f"Error processing query: {str(e)}")
            logging.error(f"AI query error: {str(e)}")
    
    def _cancel_ai_processing(self) -> None:
        """Cancel current AI processing operation"""
        if self.ai_processing:
            # Stop the loading animation if it's active
            if self.display:
                self.display.stop_loading_animation()
                
            # Set status message
            self.set_status_message("AI operation cancelled")
            
            # Reset AI processing flags
            self.ai_processing = False
            self.ai_blocking = False
            
            # Note: We can't really stop the thread, but we can mark it as cancelled
            # The thread functions will check for this flag and exit early if possible
            logging.info("AI operation cancelled by user")
    
    def quit(self, force: bool = False) -> None:
        """Quit the editor"""
        if not force and self.buffer.is_modified():
            self.set_status_message("No write since last change (use :q! to override)")
            return
        
        self.should_quit = True
        
    def start_ai_chat(self) -> None:
        """Start an interactive chat with the AI"""
        # We need to ensure we're not already processing an AI request
        if self.ai_processing:
            self.set_status_message("Already processing an AI request")
            return
        
        # Create a new thread for the chat
        with self.thread_lock:
            self.ai_processing = True
            
        # Get some context from the current buffer
        context = self.buffer.get_content()
            
        # Start the chat in a new thread
        metadata = {"operation": "chat"}
        self.ai_thread = threading.Thread(
            target=self._ai_chat_thread,
            args=(context, metadata)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
        
    def _ai_chat_thread(self, context: str, metadata: Dict[str, Any]) -> None:
        """Thread function for AI chat"""
        try:
            # Start loading animation if display is available
            if self.display:
                self.display.start_loading_animation("Starting AI chat...")
                
            # Display initial chat interface
            chat_lines = ["Welcome to AIVim Chat", ""]
            if self.chat_history:
                # Add existing chat history
                for i, (role, message) in enumerate(self.chat_history):
                    prefix = "You: " if role == "user" else "AI: "
                    # Split long messages
                    lines = message.split('\n')
                    for line in lines:
                        chat_lines.append(f"{prefix}{line}")
                    chat_lines.append("")  # Empty line between messages
            
            chat_lines.append("(Type your message and press Enter to send, Escape to exit)")
            
            # Stop loading animation and show the chat dialog
            with self.thread_lock:
                if self.display:
                    self.display.stop_loading_animation()
                self.ai_processing = False
                
                # Show the chat dialog
                if self.display:
                    self.display.show_dialog("AI Chat", chat_lines)
            
        except Exception as e:
            logging.error(f"Error in AI chat thread: {str(e)}")
            with self.thread_lock:
                if self.display:
                    self.display.stop_loading_animation()
                self.ai_processing = False
            self.set_status_message(f"Error starting chat: {str(e)}")
            
    def set_ai_model(self, model_name: str) -> None:
        """
        Set the AI model to use
        
        Args:
            model_name: Name of the model ('openai', 'claude', 'local')
        """
        model_name = model_name.lower()
        if model_name in ["openai", "claude", "local"]:
            # Update the AI service to use the selected model
            if self.ai_service.set_model(model_name):
                self.current_ai_model = model_name
                self.set_status_message(f"AI model set to: {model_name}")
            else:
                self.set_status_message(f"Failed to set AI model to {model_name}. Check logs for details.")
        else:
            self.set_status_message(f"Unknown model: {model_name}. Valid options: openai, claude, local")
            
    def show_model_selector(self) -> None:
        """
        Show a dialog for selecting an AI model
        """
        if self.display:
            current_model = self.current_ai_model or "openai"
            # Pass the AI service instance to enable submodel selection
            self.display.show_model_selector(current_model, self.set_ai_model, self.ai_service)
            
    def handle_model_selector_keypress(self, key: int) -> bool:
        """
        Handle key presses in the model selector dialog
        
        Args:
            key: The pressed key code
            
        Returns:
            True if the key was processed, False otherwise
        """
        if self.display:
            result = self.display.process_model_selector_keypress(key)
            # Check if Enter was pressed and a model was selected
            if result is not None and isinstance(result, str):
                self.set_ai_model(result)
                return True
        return False
            
    def confirm_ai_action(self, confirmed: bool, create_new_tab: bool = False) -> None:
        """
        Confirm or reject a pending AI action
        
        Args:
            confirmed: True to confirm, False to reject
            create_new_tab: If True, create a new tab with the improved content
                           instead of modifying the current buffer
        """
        if not self.pending_ai_action:
            self.set_status_message("No pending AI action to confirm")
            return
            
        if confirmed:
            try:
                # Extract the action details
                action_type = self.pending_ai_action.get("type")
                
                if action_type == "improve":
                    # Apply the improved code
                    start_line = self.pending_ai_action.get("start_line")
                    end_line = self.pending_ai_action.get("end_line")
                    new_code = self.pending_ai_action.get("new_code")
                    
                    if start_line is not None and end_line is not None and new_code:
                        # Always create a backup file with timestamp if we have a filename
                        # This helps maintain a history of AI changes
                        backup_path = ""
                        if self.filename:
                            from aivim.utils import create_backup_file
                            backup_path = create_backup_file(self.filename)
                            if backup_path:
                                self.set_status_message(f"Backup created: {backup_path}")
                        
                        # Store metadata about this AI change for future reference
                        timestamp = time.strftime("%Y%m%d%H%M%S")
                        metadata = self.pending_ai_action.get("metadata", {})
                        metadata["timestamp"] = timestamp
                        metadata["backup_path"] = backup_path if backup_path else "None"
                        
                        # Add model info to metadata if available
                        if hasattr(self, 'ai_service'):
                            model_info = self.ai_service.get_current_model_info()
                            metadata["model"] = model_info
                        
                        # Convert new code to lines
                        new_lines = new_code.split("\n")
                        
                        # Check if we need to create a new tab
                        # Always create a new tab for Local LLM results
                        is_local_llm = False
                        if hasattr(self, 'ai_service') and self.ai_service.current_model == "local":
                            is_local_llm = True
                            create_new_tab = True
                            
                        if create_new_tab:
                            # Create a new tab with the improved content
                            # Generate a new filename based on the current filename
                            new_filename = None
                            timestamp = time.strftime("%Y%m%d%H%M%S")
                            
                            if self.filename:
                                # Get the directory and base name
                                directory = os.path.dirname(self.filename)
                                basename = os.path.basename(self.filename)
                                name, ext = os.path.splitext(basename)
                                
                                # Create new filename (name_improved_timestamp.ext)
                                new_basename = f"{name}_improved_{timestamp}{ext}"
                                new_filename = os.path.join(directory, new_basename) if directory else new_basename
                                
                                # Create tab name from the new basename
                                tab_name = new_basename
                            else:
                                # No filename, just use "Improved Code"
                                tab_name = f"Improved_{timestamp}"
                            
                            # Create a new buffer with the improved code
                            new_buffer = Buffer()
                            new_buffer.set_lines(new_lines)
                            
                            # Create the new tab
                            tab_index = self.create_tab(tab_name, new_buffer, new_filename)
                            
                            # Switch to the new tab
                            self.switch_to_tab(tab_index)
                            
                            # Add model info to status message if available
                            model_info = ""
                            if hasattr(self, 'ai_service'):
                                model_info = self.ai_service.get_current_model_info()
                                model_info = f" using {model_info}"
                                
                            self.set_status_message(f"Created new tab with improved code{model_info} ({len(new_lines)} lines)")
                        else:
                            # Apply to current buffer
                            # Save current buffer state to history for undo/redo
                            self.history.add_version(self.buffer.get_lines())
                            
                            # Delete the old lines
                            for _ in range(end_line - start_line + 1):
                                self.buffer.delete_line(start_line)
                                
                            # Insert the new lines
                            for i, line in enumerate(new_lines):
                                self.buffer.insert_line(start_line + i, line)
                                
                            # Save the updated state in history
                            metadata = self.pending_ai_action.get("metadata", {})
                            self.history.add_version(self.buffer.get_lines(), metadata)
                            
                            # Add model info to status message if available
                            model_info = ""
                            if hasattr(self, 'ai_service'):
                                model_info = self.ai_service.get_current_model_info()
                                model_info = f" using {model_info}"
                                
                            self.set_status_message(f"AI improvement applied{model_info} ({len(new_lines)} lines)")
                    else:
                        self.set_status_message("Invalid AI action data")
                else:
                    self.set_status_message(f"Unknown AI action type: {action_type}")
                    
            except Exception as e:
                self.set_status_message(f"Error applying AI action: {str(e)}")
                logging.error(f"Error applying AI action: {str(e)}")
        else:
            # User rejected the action
            self.set_status_message("AI action rejected")
            
        # Clear the pending action
        self.pending_ai_action = None