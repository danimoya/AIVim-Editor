"""
Core editor implementation for AIVim
"""
import uuid
from .file_store import FileStore, SaveResult
from .ai_jobs import AIJob, AIJobs
from .input_decoder import InputDecoder, Paste
from .ai_service import AIError
from .proposals import parse_proposal
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
        self.document_id = uuid.uuid4().hex
        self.file_identity = None
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
    def __init__(self, filename: Optional[str] = None, *, ai_service=None, settings=None, file_store=None):
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
        self.command_handler = CommandHandler(self)  # Will be initialized in start()
        self.settings = settings if settings is not None else Settings()
        self.ai_service = ai_service if ai_service is not None else AIService(settings=self.settings)
        self.file_store = file_store if file_store is not None else FileStore()
        self._pending_key = None
        self._numeric_prefix = 0
        self._insert_base = None  # Initialize settings
        
        # Create initial tab
        initial_tab = Tab("Untitled", filename=filename)
        initial_tab.history.max_history=self.settings.file.undolevels
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
        self.jobs = AIJobs(self.ai_service)
        self.current_job_id = None
        self.current_ai_model = self.ai_service.current_model  # Default AI model
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
        new_tab.history.max_history=self.settings.file.undolevels
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
            
    def close_current_tab(self, decision=None):
        if len(self.tabs) <= 1:
            self.set_status_message('Cannot close the last tab'); return False
        if self.buffer.is_modified():
            if decision == 'save':
                if not self.save_file(): return False
            elif decision != 'discard':
                self.set_status_message('Unsaved tab: :tabclose save, :tabclose discard, or continue editing to cancel'); return False
        if hasattr(self, 'jobs'):
            active=self.jobs.active.get(self.current_job_id)
            if active and active.document_id==self.current_tab.document_id:self._cancel_ai_processing()
            self.jobs.cancel_document(self.current_tab.document_id)
        if self.pending_ai_action and self.pending_ai_action.document_id==self.current_tab.document_id:self.pending_ai_action=None
        del self.tabs[self.current_tab_index]
        self.current_tab_index = min(self.current_tab_index, len(self.tabs)-1)
        return True
      
    def load_file(self, filename, force=False):
        if not force and self.buffer.is_modified():
            self.set_status_message('Unsaved document: save, open a new tab, or force reload'); return False
        result = self.file_store.load(filename, self.settings.file.encoding, {'unix':'\n','dos':'\r\n','mac':'\r'}[self.settings.file.fileformat])
        if not result:
            self.set_status_message(result.message); return False
        self.buffer.set_content(result.content); self.buffer.mark_as_saved()
        self.current_tab.file_identity = result.identity; self.filename = filename
        self.history.clear(); self.history.add_version(self.buffer.get_lines())
        self.cursor_x = self.cursor_y = self.scroll_y = 0
        self.set_status_message('Loaded document'); return True
    
    def save_file(self, filename=None, create_backup=True, force=False):
        target = filename or self.filename
        if not target:
            result = SaveResult(False, code='NO_FILENAME', message='No filename specified (use :w filename)')
        else:
            identity = self.current_tab.file_identity
            if identity and str(__import__('pathlib').Path(target).expanduser().absolute()) != str(__import__('pathlib').Path(self.filename).expanduser().absolute()): identity = None
            result = self.file_store.save(target, self.buffer.get_content(), identity, force=force,
                backup_dir=self.settings.file.backup_dir if create_backup and self.settings.file.auto_backup else None,
                encoding=self.settings.file.encoding, newline={'unix':'\n','dos':'\r\n','mac':'\r'}[self.settings.file.fileformat])
        if result:
            self.current_tab.file_identity = result.identity; self.filename = target; self.buffer.mark_as_saved()
            self.set_status_message('Saved document')
        else: self.set_status_message(result.message)
        return result
    
    def reload_file(self, force=False):
        if not self.filename: raise ValueError('No file to reload')
        if not force and self.buffer.is_modified(): raise ValueError('Unsaved changes; use :e! to discard')
        return self.load_file(self.filename, force=force)
    
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
            logging.error("editor operation failed")
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
            if not self.load_file(filename,force=force):
                raise ValueError(self.status_message)
            
            # Update tab name
            if hasattr(self, 'current_tab'):
                self.current_tab.name = os.path.basename(filename)
                
        except Exception as e:
            logging.error("editor operation failed")
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
            logging.error("editor operation failed")
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
        
        decoder=InputDecoder()
        # Main editor loop
        while not self.should_quit:
            self.poll_ai_events()
            self._update_display()
            
            # Get input
            try:
                key = stdscr.get_wch()
                for event in decoder.feed(key):self.handle_input(event)
            except curses.error:
                for event in decoder.flush():self.handle_input(event)
                self.poll_ai_events()
            except KeyboardInterrupt:
                # Handle Ctrl+C more gracefully
                if self.mode != "NORMAL":
                    self.mode = "NORMAL"
                    self.set_status_message("Switched to NORMAL mode")
                else:
                    # In normal mode, treat as Escape
                    self.set_status_message("")
    
    def _dispatch_input(self, key: int) -> None:
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
    
    def _handle_normal_mode(self, key):
        ch = chr(key) if 0 <= key < 256 else ''
        if ch.isdigit() and (ch != '0' or self._numeric_prefix):
            self._numeric_prefix = min(100000, self._numeric_prefix * 10 + int(ch)); return
        count = self._numeric_prefix or 1
        if self._pending_key:
            pending=self._pending_key; self._pending_key=None; self._numeric_prefix=0
            if pending == ch and ch in 'dy':
                self.clipboard=list(self.buffer.get_lines()[self.cursor_y:self.cursor_y+count]); self._clipboard_linewise=True
                if ch == 'd':
                    for _ in self.clipboard: self.buffer.delete_line(self.cursor_y)
                    self.cursor_y=min(self.cursor_y,len(self.buffer.get_lines())-1); self._adjust_cursor_x()
                return
            if pending == ch == 'g': self.cursor_y=self.cursor_x=self.scroll_y=0; return
            # Unrecognized second keys are dispatched normally rather than consumed.
        if ch in 'dyg': self._pending_key=ch; return
        self._numeric_prefix=0
        if ch in 'iaAIsoO':
            self.history.add_version(self.buffer.get_lines()); self._insert_base=self.buffer.get_content()
            if ch == 'a': self.cursor_x=min(len(self.buffer.get_line(self.cursor_y)),self.cursor_x+1)
            elif ch == 'A': self.cursor_x=len(self.buffer.get_line(self.cursor_y))
            elif ch == 'I': self.cursor_x=len(self.buffer.get_line(self.cursor_y))-len(self.buffer.get_line(self.cursor_y).lstrip())
            elif ch == 's':
                line=self.buffer.get_line(self.cursor_y); self.buffer.set_line(self.cursor_y,line[:self.cursor_x]+line[self.cursor_x+1:])
            elif ch == 'o': self._open_line_below()
            elif ch == 'O': self._open_line_above()
            self.mode='INSERT'; self.set_status_message('-- INSERT --')
        elif ch == 'u' or key == 18:
            for _ in range(count):
                lines,_=self.history.undo() if ch == 'u' else self.history.redo()
                if lines is not None: self.buffer.set_lines(lines)
            self.cursor_y=min(self.cursor_y,len(self.buffer.get_lines())-1); self._adjust_cursor_x()
        elif ch == 'x':
            line=self.buffer.get_line(self.cursor_y); self.buffer.set_line(self.cursor_y,line[:self.cursor_x]+line[self.cursor_x+count:])
        elif ch in 'pP':
            if self.clipboard:
                if getattr(self,'_clipboard_linewise',False):
                    start=self.cursor_y+(ch=='p')
                    for i,line in enumerate(self.clipboard*count): self.buffer.insert_line(start+i,line)
                    self.cursor_y=start; self.cursor_x=0
                else: self.insert_text('\n'.join(self.clipboard)*count)
        elif ch == ':': self.mode='COMMAND'; self.command_buffer=':'; self.command_cursor=1
        elif ch == 'v': self.mode='VISUAL'; self.buffer.start_selection(self.cursor_y,self.cursor_x)
        elif ch in '/?': self.enter_search_mode('forward' if ch=='/' else 'backward')
        elif ch in 'nN' and self.search_pattern: self._find_next_search_match(opposite_direction=ch=='N')
        elif ch in '*#': self.search_word_under_cursor(backward=ch=='#')
        elif ch == 'G': self.cursor_y=len(self.buffer.get_lines())-1; self.cursor_x=0
        elif ch == '0': self.cursor_x=0
        elif ch == '$': self.cursor_x=len(self.buffer.get_line(self.cursor_y))
        elif ch == '^': self.cursor_x=len(self.buffer.get_line(self.cursor_y))-len(self.buffer.get_line(self.cursor_y).lstrip())
        elif ch in 'wbe':
            text=self.buffer.get_content(); pos=sum(len(x)+1 for x in self.buffer.get_lines()[:self.cursor_y])+self.cursor_x
            import re
            starts=[m.start() for m in re.finditer(r'\w+|[^\w\s]+',text)]
            ends=[m.end()-1 for m in re.finditer(r'\w+|[^\w\s]+',text)]
            for _ in range(count):
                choices=[p for p in (ends if ch=='e' else starts) if p<pos] if ch=='b' else [p for p in (ends if ch=='e' else starts) if p>pos]
                pos=(max(choices) if ch=='b' else min(choices)) if choices else (0 if ch=='b' else len(text))
            prefix=text[:pos]; self.cursor_y=prefix.count('\n'); self.cursor_x=len(prefix.rsplit('\n',1)[-1])
        elif ch == 'h' or key == curses.KEY_LEFT: self.cursor_x=max(0,self.cursor_x-count)
        elif ch == 'l' or key == curses.KEY_RIGHT: self.cursor_x=min(len(self.buffer.get_line(self.cursor_y)),self.cursor_x+count)
        elif ch == 'j' or key == curses.KEY_DOWN: self.cursor_y=min(len(self.buffer.get_lines())-1,self.cursor_y+count); self._adjust_cursor_x()
        elif ch == 'k' or key == curses.KEY_UP: self.cursor_y=max(0,self.cursor_y-count); self._adjust_cursor_x()
        self.preferred_x=self.cursor_x
                
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
        else:
            # Smart case: case insensitive unless pattern has uppercase
            self.search_case_sensitive = not self.settings.search.ignorecase or (self.settings.search.smartcase and any(c.isupper() for c in actual_pattern))
        
        self.search_very_magic = 'v' in flags
        
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
                if not self.settings.search.wrapscan:self.set_status_message('Search reached end');return
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
                if not self.settings.search.wrapscan:self.set_status_message('Search reached start');return
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
            if self.search_input_buffer and self.settings.search.incsearch:
                self._start_search(self.search_input_buffer, incremental=True)
    
    def _update_search_display(self) -> None:
        """Update the search prompt display"""
        prompt = "/" if self.search_direction == "forward" else "?"
        self.set_status_message(f"{prompt}{self.search_input_buffer}")
    
    def substitute(self, pattern, replacement, line_range=None, global_flag=False, confirm=False, flags=''):
        start,end=line_range or (self.cursor_y,self.cursor_y)
        lines=self.buffer.get_lines()
        if not pattern or not 0 <= start <= end < len(lines): raise ValueError('Invalid substitution pattern or range')
        regex=re.compile(pattern,re.IGNORECASE if 'i' in flags else 0)
        self.history.add_version(lines);text=self.buffer.get_content();matches=[];offset=sum(len(x)+1 for x in lines[:start])
        for line in lines[start:end+1]:
            for i,m in enumerate(regex.finditer(line)):
                if i and not global_flag: break
                matches.append((offset+m.start(),offset+m.end(),m.expand(replacement)))
            offset+=len(line)+1
        if not matches: self.set_status_message('Pattern not found');return 0
        if confirm:
            self._substitution_review={'text':text,'matches':matches,'accepted':[],'index':0};self.set_status_message('Replace next match? y/n/a/q');return 0
        for a,b,value in reversed(matches): text=text[:a]+value+text[b:]
        self.buffer.set_content(text);self.history.add_version(self.buffer.get_lines());self.set_status_message(f'{len(matches)} substitutions');return len(matches)
    
    def _handle_insert_mode(self, key):
        if key == 27:
            self.mode='NORMAL'; self.history.add_version(self.buffer.get_lines()); self._insert_base=None; self.set_status_message(''); return
        if key == 22:
            self.insert_text('\n'.join(self.clipboard)); return
        if key in (curses.KEY_BACKSPACE,127,8):
            line=self.buffer.get_line(self.cursor_y)
            if self.cursor_x:
                self.buffer.set_line(self.cursor_y,line[:self.cursor_x-1]+line[self.cursor_x:]);self.cursor_x-=1
            elif self.cursor_y:
                previous=self.buffer.get_line(self.cursor_y-1);self.buffer.set_line(self.cursor_y-1,previous+line);self.buffer.delete_line(self.cursor_y);self.cursor_y-=1;self.cursor_x=len(previous)
        elif key == curses.KEY_DC:
            line=self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line): self.buffer.set_line(self.cursor_y,line[:self.cursor_x]+line[self.cursor_x+1:])
            elif self.cursor_y < len(self.buffer.get_lines())-1:
                self.buffer.set_line(self.cursor_y,line+self.buffer.get_line(self.cursor_y+1));self.buffer.delete_line(self.cursor_y+1)
        elif key in (10,13,curses.KEY_ENTER):
            line=self.buffer.get_line(self.cursor_y); indent=''
            if self.settings.editor.autoindent: indent=line[:len(line)-len(line.lstrip())]
            self.buffer.set_line(self.cursor_y,line[:self.cursor_x]);self.buffer.insert_line(self.cursor_y+1,indent+line[self.cursor_x:]);self.cursor_y+=1;self.cursor_x=len(indent)
        elif key in (20,4):
            line=self.buffer.get_line(self.cursor_y);width=self.settings.editor.shiftwidth
            if key==20:self.buffer.set_line(self.cursor_y,' '*width+line);self.cursor_x+=width
            else:
                remove=min(width,len(line)-len(line.lstrip(' ')));self.buffer.set_line(self.cursor_y,line[remove:]);self.cursor_x=max(0,self.cursor_x-remove)
        elif key == 9:
            text=' '*(self.settings.editor.tabstop-self.cursor_x%self.settings.editor.tabstop) if self.settings.editor.expandtab else '\t';self.insert_text(text)
        elif key == curses.KEY_LEFT: self.cursor_x=max(0,self.cursor_x-1)
        elif key == curses.KEY_RIGHT: self.cursor_x=min(len(self.buffer.get_line(self.cursor_y)),self.cursor_x+1)
        elif key in (curses.KEY_UP,curses.KEY_DOWN,curses.KEY_PPAGE,curses.KEY_NPAGE):
            delta={curses.KEY_UP:-1,curses.KEY_DOWN:1,curses.KEY_PPAGE:-20,curses.KEY_NPAGE:20}[key];self.cursor_y=max(0,min(len(self.buffer.get_lines())-1,self.cursor_y+delta));self._adjust_cursor_x()
        elif key == curses.KEY_HOME: self.cursor_x=0
        elif key == curses.KEY_END: self.cursor_x=len(self.buffer.get_line(self.cursor_y))
        elif 32 <= key <= 126: self.insert_text(chr(key))
        self.preferred_x=self.cursor_x
    
    def _handle_visual_mode(self, key: int) -> None:
        """Handle keypresses in visual mode"""
        if key == ord(':'):
            self.mode='COMMAND';self.command_buffer=":'<,'>";self.command_cursor=len(self.command_buffer);return
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
            self._clipboard_linewise = False
            
            # Ensure the clipboard isn't empty (can happen with empty selections)
            if not self.clipboard:
                self.clipboard = [""]
                
            # Log the clipboard contents for debugging
            logging.info("Selection copied")
            
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
    
    def _process_command(self):
        command=self.command_buffer
        self.mode='NORMAL'; self.command_buffer='';self.command_cursor=0
        if re.fullmatch(r':\d+',command): self._navigate_to_line(int(command[1:])-1);return
        if command==':$': self._navigate_to_line(len(self.buffer.get_lines())-1);return
        if command.startswith(('/', '?')):
            self.search_direction='backward' if command[0]=='?' else 'forward';self._start_search(command[1:]);return
        self.command_handler.execute(command)
                
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
        
        height=max(1,self.display.max_text_height)
        margin=min(self.settings.editor.scrolloff,height//2)
        if self.cursor_y<self.scroll_y+margin:self.scroll_y=max(0,self.cursor_y-margin)
        elif self.cursor_y>=self.scroll_y+height-margin:self.scroll_y=max(0,self.cursor_y-height+margin+1)
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
                self.mode, self.current_tab.document_id, self.buffer.revision, self.status_message, self.command_buffer, len(self.buffer.get_lines()),
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
                self.mode, self.current_tab.document_id, self.buffer.revision, self.status_message, self.command_buffer, len(self.buffer.get_lines()),
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
    
    def _handle_resize(self, *args):
        self._do_resize()
    
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
        import sys
        sys.stdout.write("\x1b[?2004h");sys.stdout.flush()
        
        # Other initialization
        stdscr.timeout(30)
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
        logging.debug("Editor status updated")
        
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
    
    def ai_generate(self,start_line,description,blocking=False):
        if not 0<=start_line<=len(self.buffer.get_lines()):self.set_status_message('Invalid insertion line');return False
        offset=sum(len(x)+1 for x in self.buffer.get_lines()[:start_line]);offset=min(offset,len(self.buffer.get_content()))
        return self.submit_ai('generate',((offset,offset),),f'Insert before zero-based character offset {offset}: {description}')
    
    
    def ai_explain(self,start_line,end_line,blocking=False):
        return self.submit_ai('explain',self.line_offsets(start_line,end_line),context=self.line_context(start_line,end_line))
    
    
    def ai_improve(self,start_line,end_line,blocking=False):
        return self.submit_ai('improve',self.line_offsets(start_line,end_line),context=self.line_context(start_line,end_line))
    
    
    def ai_analyze_code(self,start_line,end_line,blocking=False):
        return self.submit_ai('analyze',self.line_offsets(start_line,end_line),context=self.line_context(start_line,end_line))
    
    
    def ai_custom_query(self,query,blocking=False):
        return self.submit_ai('query',((0,len(self.buffer.get_content())),),query)
    
    
    def _cancel_ai_processing(self):
        if self.current_job_id:self.jobs.cancel(self.current_job_id)
        self.current_job_id=None;self.ai_processing=False;self.ai_blocking=False
        self.set_status_message('AI request cancelled; document preserved')
    
    def quit(self, force=False):
        if not force and any(t.buffer.is_modified() for t in self.tabs):
            self.set_status_message('Unsaved documents: save each tab or use :q! to discard all'); return False
        if hasattr(self, 'jobs'): self.jobs.close()
        self.should_quit = True; return True
        
    def start_ai_chat(self):
        self.show_dialog('AI Chat',[f'{role}: {text}' for role,text in self.chat_history]+['Use :ai <message> to submit; each response stays outside the document.'])
        
            
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
            
    def confirm_ai_action(self,confirmed,create_new_tab=False,copy=None):
        proposal=self.pending_ai_action
        if not proposal:self.set_status_message('No pending proposal');return False
        if not confirmed:
            self.pending_ai_action=None
            if self.display:self.display.close_dialog()
            self.set_status_message('Proposal rejected');return True
        if copy is None:copy=create_new_tab
        tab=next((t for t in self.tabs if t.document_id==proposal.document_id),None)
        try:proposal.validate_document(tab)
        except AIError as exc:self.set_status_message(str(exc));return False
        content=proposal.content()
        if copy:
            buffer=Buffer();buffer.set_content(content)
            index=self.create_tab('AI proposal copy',buffer=buffer);self.switch_to_tab(index)
        else:
            tab.history.add_version(tab.buffer.get_lines());tab.buffer.set_content(content);tab.history.add_version(tab.buffer.get_lines())
            if tab is self.current_tab:
                self.cursor_y=min(self.cursor_y,len(tab.buffer.get_lines())-1);self._adjust_cursor_x()
        self.pending_ai_action=None
        if self.display:self.display.close_dialog()
        self.set_status_message('Proposal copied' if copy else 'Proposal applied; u undoes it');return True
    def insert_text(self, text):
        line=self.buffer.get_line(self.cursor_y); parts=text.replace('\r\n','\n').replace('\r','\n').split('\n')
        self.buffer.set_line(self.cursor_y,line[:self.cursor_x]+parts[0]+(line[self.cursor_x:] if len(parts)==1 else ''))
        for i,part in enumerate(parts[1:],1): self.buffer.insert_line(self.cursor_y+i,part+(line[self.cursor_x:] if i==len(parts)-1 else ''))
        self.cursor_y+=len(parts)-1;self.cursor_x=(self.cursor_x+len(parts[0])) if len(parts)==1 else len(parts[-1]);self.preferred_x=self.cursor_x

    def _review_substitution(self, key):
        review=self._substitution_review
        if key not in (ord('y'),ord('n'),ord('a'),ord('q')): return
        if key == ord('q'): review['index']=len(review['matches'])
        elif key == ord('a'): review['accepted'].extend(review['matches'][review['index']:]);review['index']=len(review['matches'])
        else:
            if key == ord('y'): review['accepted'].append(review['matches'][review['index']])
            review['index']+=1
        if review['index'] == len(review['matches']):
            text=review['text']
            for start,end,replacement in reversed(review['accepted']): text=text[:start]+replacement+text[end:]
            self.buffer.set_content(text);self.history.add_version(self.buffer.get_lines());self._substitution_review=None;self.set_status_message('Substitution complete')
        else: self.set_status_message('Replace next match? y/n/a/q')

    def handle_input(self, key):
        self.poll_ai_events()
        if isinstance(key,Paste):
            self.history.add_version(self.buffer.get_lines());self.insert_text(key.text)
            if self.mode not in ('INSERT','NLP'):self.history.add_version(self.buffer.get_lines())
            return
        if key == -1: return
        if getattr(self,'_substitution_review',None):
            self._review_substitution(ord(key) if isinstance(key,str) else key); return
        before=self.buffer.revision;tab=self.current_tab; mode=self.mode
        if isinstance(key,str) and len(key)==1:
            if ord(key)>127:
                if self.mode in ('INSERT','NLP'): self.insert_text(key)
                elif self.mode=='COMMAND': self.command_buffer=self.command_buffer[:self.command_cursor]+key+self.command_buffer[self.command_cursor:];self.command_cursor+=1
                elif self.mode=='SEARCH': self.search_input_buffer+=key
                return
            key=ord(key)
        if self.mode=='NORMAL' and key not in (ord('u'),18): self.history.add_version(self.buffer.get_lines())
        self._dispatch_input(key)
        if tab is self.current_tab and before != self.buffer.revision and self.mode not in ('INSERT','NLP') and key not in (ord('u'),18): self.history.add_version(self.buffer.get_lines())

    def line_offsets(self,start,end):
        lines=self.buffer.get_lines()
        if not 0<=start<=end<len(lines): raise ValueError('Invalid line range')
        a=sum(len(x)+1 for x in lines[:start]);b=sum(len(x)+1 for x in lines[:end])+len(lines[end])
        return ((a,b),)

    def submit_ai(self,action,ranges,instruction='',context=''):
        if self.ai_processing:self.set_status_message('AI request is pending; Esc cancels');return False
        tab=self.current_tab;provider=self.ai_service.current_model;model=self.ai_service.models()[provider]
        job=AIJob(tab.document_id,tab.buffer.revision,tab.buffer.get_content(),action,provider,model,tuple(ranges),context,instruction,time.monotonic()+self.settings.ai.timeout)
        try:self.current_job_id=self.jobs.submit(job)
        except AIError as exc:self.set_status_message(str(exc));return False
        self.ai_processing=True;self.ai_blocking=False;self.last_ai_status_update=time.time()
        self.set_status_message(f'AI pending: {provider}/{model}; context only this document unless explicitly selected; Esc cancels')
        return True

    def poll_ai_events(self):
        if not hasattr(self,'jobs'):return
        if self.nlp_handler:self.nlp_handler.tick()
        for event in self.jobs.drain():
            if event.job.request_id!=self.current_job_id:continue
            self.current_job_id=None;self.ai_processing=False;self.ai_blocking=False
            if event.error:self.set_status_message(f'{event.error.code}: {event.error}');continue
            tab=next((t for t in self.tabs if t.document_id==event.job.document_id),None)
            if tab is None or tab.buffer.revision!=event.job.base_revision or tab.buffer.get_content()!=event.job.source_snapshot:
                self.set_status_message('STALE_PROPOSAL: Document changed; result discarded');continue
            if event.job.action in ('improve','generate','nlp'):
                try:proposal=parse_proposal(event.job,event.result)
                except AIError as exc:self.set_status_message(f'{exc.code}: {exc}');continue
                self.pending_ai_action=proposal
                if self.display:self.display.show_multi_view_dialog([{'title':'Original','content':proposal.snapshot.split('\n')},{'title':'Proposal','content':proposal.content().split('\n')},{'title':'Diff','content':proposal.diff()}],explanation=proposal.explanation.split('\n'),default_view=2)
                self.set_status_message('Proposal ready: :apply changes original; :y copies full document; :reject dismisses; :n changes tab')
            else:
                self.chat_history.append(('AI',event.result.text));self.show_dialog('AI '+event.job.action,event.result.text.split('\n'));self.set_status_message('AI response ready; document preserved')

    def line_context(self,start,end):
        return '\n'.join(self.buffer.get_lines()[max(0,start-20):end+21])
