"""
File browser module for AIVim
Provides a file explorer interface for browsing and opening files
"""
import os
import curses
import logging
from datetime import datetime
from typing import Optional, List, Tuple


class FileBrowserItem:
    """Represents an item in the file browser"""
    def __init__(self, path: str, is_dir: bool = False):
        self.path = path
        self.name = os.path.basename(path) or path
        self.is_dir = is_dir
        self.size = 0
        self.modified_time = None
        
        try:
            stat = os.stat(path)
            self.size = stat.st_size
            self.modified_time = datetime.fromtimestamp(stat.st_mtime)
        except:
            pass
    
    def get_display_string(self, width: int) -> str:
        """Get formatted string for display"""
        if self.is_dir:
            name_str = f"[{self.name}]"
        else:
            name_str = self.name
        
        # Format size
        size_str = self._format_size(self.size) if not self.is_dir else ""
        
        # Format time
        if self.modified_time:
            time_str = self.modified_time.strftime("%Y-%m-%d %H:%M")
        else:
            time_str = ""
        
        # Calculate available space for name
        extra_len = len(size_str) + len(time_str) + 4  # 4 for spacing
        available = max(20, width - extra_len)
        
        # Truncate name if necessary
        if len(name_str) > available:
            name_str = name_str[:available-3] + "..."
        
        # Build final string
        if self.is_dir:
            return f"{name_str:<{available}}  {time_str}"
        else:
            return f"{name_str:<{available}}  {size_str:>10}  {time_str}"
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'K', 'M', 'G']:
            if size < 1024.0 or unit == 'G':
                if unit == 'B':
                    return f"{int(size)}{unit}"
                else:
                    return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}G"


class FileBrowser:
    """File browser/explorer for AIVim"""
    
    def __init__(self, editor):
        """
        Initialize the file browser
        
        Args:
            editor: Reference to the editor
        """
        self.editor = editor
        self.current_path = os.getcwd()
        self.selected_index = 0
        self.scroll_offset = 0
        self.items = []
        self.filter_text = ""
        self.show_hidden = False
    
    def browse(self) -> Optional[str]:
        """
        Open the file browser and let user select a file
        
        Returns:
            Path to selected file, or None if cancelled
        """
        # Save current display state
        stdscr = self.editor.display.stdscr
        
        # Initialize browser window
        curses.curs_set(0)  # Hide cursor
        
        # Load initial directory
        self._load_directory()
        
        while True:
            # Render the browser
            self._render(stdscr)
            
            # Get input
            key = stdscr.getch()
            
            # Handle key press
            result = self._handle_key(key)
            if result is not None:
                # Restore cursor
                curses.curs_set(1)
                return result
    
    def _load_directory(self) -> None:
        """Load the contents of the current directory"""
        self.items = []
        
        try:
            # Add parent directory option (except for root)
            if self.current_path != '/':
                parent_item = FileBrowserItem(os.path.dirname(self.current_path), True)
                parent_item.name = ".."
                self.items.append(parent_item)
            
            # Get directory contents
            entries = os.listdir(self.current_path)
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_path, x)), x.lower()))
            
            for entry in entries:
                # Skip hidden files unless enabled
                if not self.show_hidden and entry.startswith('.'):
                    continue
                
                # Apply filter
                if self.filter_text and self.filter_text.lower() not in entry.lower():
                    continue
                
                full_path = os.path.join(self.current_path, entry)
                
                try:
                    is_dir = os.path.isdir(full_path)
                    item = FileBrowserItem(full_path, is_dir)
                    self.items.append(item)
                except:
                    # Skip items we can't access
                    pass
            
            # Reset selection if needed
            if self.selected_index >= len(self.items):
                self.selected_index = 0
                
        except Exception as e:
            logging.error(f"Error loading directory: {str(e)}")
            self.editor.set_status_message(f"Error loading directory: {str(e)}")
    
    def _render(self, stdscr) -> None:
        """Render the file browser interface"""
        height, width = stdscr.getmaxyx()
        
        # Clear screen
        stdscr.clear()
        
        # Draw header
        header = f" File Browser - {self.current_path} "
        if self.filter_text:
            header += f" [Filter: {self.filter_text}]"
        header = header[:width-1]
        stdscr.addstr(0, 0, header, curses.A_REVERSE)
        
        # Draw help line
        help_text = " Enter:Open  Backspace:Parent  h:Toggle hidden  /:Filter  q:Quit "
        help_text = help_text[:width-1]
        stdscr.addstr(height-1, 0, help_text, curses.A_REVERSE)
        
        # Calculate visible area
        visible_height = height - 2  # Minus header and help line
        
        # Adjust scroll offset
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_height:
            self.scroll_offset = self.selected_index - visible_height + 1
        
        # Draw items
        for i in range(visible_height):
            item_index = self.scroll_offset + i
            if item_index >= len(self.items):
                break
            
            item = self.items[item_index]
            line_num = i + 1
            
            # Get display string
            display_str = item.get_display_string(width - 2)
            
            # Highlight selected item
            if item_index == self.selected_index:
                stdscr.addstr(line_num, 1, display_str[:width-2], curses.A_REVERSE)
            else:
                # Color directories differently
                if item.is_dir:
                    try:
                        stdscr.addstr(line_num, 1, display_str[:width-2], curses.color_pair(4))  # Blue
                    except:
                        stdscr.addstr(line_num, 1, display_str[:width-2], curses.A_BOLD)
                else:
                    stdscr.addstr(line_num, 1, display_str[:width-2])
        
        # Draw scrollbar if needed
        if len(self.items) > visible_height:
            self._draw_scrollbar(stdscr, 1, width-1, visible_height, 
                               len(self.items), self.scroll_offset)
        
        stdscr.refresh()
    
    def _draw_scrollbar(self, stdscr, start_y: int, x: int, height: int, 
                       total_items: int, offset: int) -> None:
        """Draw a scrollbar"""
        if total_items == 0:
            return
        
        # Calculate scrollbar position and size
        bar_height = max(1, int(height * height / total_items))
        bar_pos = int(offset * (height - bar_height) / (total_items - height))
        
        # Draw scrollbar track
        for y in range(height):
            if y >= bar_pos and y < bar_pos + bar_height:
                try:
                    stdscr.addstr(start_y + y, x, "█")
                except:
                    pass
            else:
                try:
                    stdscr.addstr(start_y + y, x, "│")
                except:
                    pass
    
    def _handle_key(self, key: int) -> Optional[str]:
        """
        Handle key press in the browser
        
        Args:
            key: Key code
            
        Returns:
            Selected file path if a file is chosen, None otherwise
        """
        # Navigation keys
        if key == curses.KEY_UP or key == ord('k'):
            if self.selected_index > 0:
                self.selected_index -= 1
        
        elif key == curses.KEY_DOWN or key == ord('j'):
            if self.selected_index < len(self.items) - 1:
                self.selected_index += 1
        
        elif key == curses.KEY_PPAGE:  # Page Up
            self.selected_index = max(0, self.selected_index - 10)
        
        elif key == curses.KEY_NPAGE:  # Page Down
            self.selected_index = min(len(self.items) - 1, self.selected_index + 10)
        
        elif key == curses.KEY_HOME or key == ord('g'):
            self.selected_index = 0
        
        elif key == curses.KEY_END or key == ord('G'):
            self.selected_index = len(self.items) - 1 if self.items else 0
        
        # Enter - open file/directory
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            if self.items and self.selected_index < len(self.items):
                item = self.items[self.selected_index]
                
                if item.is_dir:
                    # Navigate to directory
                    if item.name == "..":
                        self.current_path = os.path.dirname(self.current_path)
                    else:
                        self.current_path = item.path
                    self.selected_index = 0
                    self._load_directory()
                else:
                    # Return selected file
                    return item.path
        
        # Backspace - go to parent directory
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.current_path != '/':
                self.current_path = os.path.dirname(self.current_path)
                self.selected_index = 0
                self._load_directory()
        
        # h - toggle hidden files
        elif key == ord('h'):
            self.show_hidden = not self.show_hidden
            self._load_directory()
        
        # / - start filtering
        elif key == ord('/'):
            self.filter_text = self._get_filter_input()
            self._load_directory()
        
        # Clear filter
        elif key == 27:  # ESC
            if self.filter_text:
                self.filter_text = ""
                self._load_directory()
            else:
                # Cancel browser
                return None
        
        # q - quit browser
        elif key == ord('q') or key == ord('Q'):
            return None
        
        return None  # Continue browsing
    
    def _get_filter_input(self) -> str:
        """Get filter text from user"""
        stdscr = self.editor.display.stdscr
        height, width = stdscr.getmaxyx()
        
        # Show prompt
        prompt = "Filter: "
        stdscr.addstr(height-1, 0, " " * (width-1))
        stdscr.addstr(height-1, 0, prompt)
        
        # Get input
        curses.echo()
        curses.curs_set(1)
        
        input_str = ""
        while True:
            key = stdscr.getch()
            
            if key == curses.KEY_ENTER or key == 10 or key == 13:
                break
            elif key == 27:  # ESC
                input_str = self.filter_text  # Keep existing filter
                break
            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                if input_str:
                    input_str = input_str[:-1]
                    stdscr.addstr(height-1, len(prompt) + len(input_str), " ")
                    stdscr.move(height-1, len(prompt) + len(input_str))
            elif 32 <= key <= 126:  # Printable characters
                if len(input_str) < width - len(prompt) - 2:
                    input_str += chr(key)
                    stdscr.addch(key)
        
        curses.noecho()
        curses.curs_set(0)
        
        return input_str