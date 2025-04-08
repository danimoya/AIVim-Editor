"""
Core editor implementation for AIVim
"""
import curses
import os
import threading
import time
from typing import Optional, List, Dict, Any, Tuple

from aivim.buffer import Buffer
from aivim.ai_service import AIService
from aivim.commands import CommandProcessor
from aivim.display import Display
from aivim.history import VersionHistory
from aivim.modes import Mode


class Editor:
    """
    Main editor class that coordinates all AIVim components
    """
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.buffer = Buffer()
        self.history = VersionHistory()
        self.ai_service = AIService()
        self.display = None
        self.command_processor = None
        self.mode = Mode.NORMAL
        self.running = False
        self.cursor_x = 0
        self.cursor_y = 0
        self.command_line = ""
        self.status_message = ""
        self.ai_processing = False
        self.ai_thread = None
        
        # Load file if specified
        if filename and os.path.exists(filename):
            self.load_file(filename)
    
    def load_file(self, filename: str) -> None:
        """Load content from a file into the buffer"""
        try:
            with open(filename, 'r') as f:
                content = f.read()
            self.buffer.set_content(content)
            self.filename = filename
            self.history.add_version(self.buffer.get_lines())
            self.status_message = f"Loaded: {filename}"
        except Exception as e:
            self.status_message = f"Error loading file: {str(e)}"
    
    def save_file(self, filename: Optional[str] = None) -> None:
        """Save buffer content to a file"""
        target_filename = filename or self.filename
        if not target_filename:
            self.status_message = "No filename specified"
            return
        
        try:
            with open(target_filename, 'w') as f:
                f.write(self.buffer.get_content())
            self.filename = target_filename
            self.status_message = f"Saved: {target_filename}"
        except Exception as e:
            self.status_message = f"Error saving file: {str(e)}"
    
    def start(self, stdscr) -> None:
        """Initialize and start the editor with curses"""
        self.display = Display(stdscr)
        self.command_processor = CommandProcessor(self)
        self.running = True
        
        # Hide cursor during setup
        curses.curs_set(0)
        
        # Initialize display
        self.display.setup()
        
        # Main event loop
        while self.running:
            # Update display
            self.display.refresh(
                self.buffer.get_lines(),
                self.cursor_y,
                self.cursor_x,
                self.mode,
                self.command_line,
                self.status_message,
                self.ai_processing
            )
            
            # Get user input
            try:
                key = self.display.stdscr.getch()
                self.handle_input(key)
            except KeyboardInterrupt:
                self.running = False
    
    def handle_input(self, key: int) -> None:
        """Process user input based on current mode"""
        if self.mode == Mode.NORMAL:
            self._handle_normal_mode(key)
        elif self.mode == Mode.INSERT:
            self._handle_insert_mode(key)
        elif self.mode == Mode.VISUAL:
            self._handle_visual_mode(key)
        elif self.mode == Mode.COMMAND:
            self._handle_command_mode(key)
    
    def _handle_normal_mode(self, key: int) -> None:
        """Handle keypresses in normal mode"""
        if key == ord('i'):  # Enter insert mode
            self.mode = Mode.INSERT
            self.status_message = "-- INSERT --"
        elif key == ord('v'):  # Enter visual mode
            self.mode = Mode.VISUAL
            self.status_message = "-- VISUAL --"
            self.buffer.start_selection(self.cursor_y, self.cursor_x)
        elif key == ord(':'):  # Enter command mode
            self.mode = Mode.COMMAND
            self.command_line = ":"
        elif key == ord('h') and self.cursor_x > 0:  # Move left
            self.cursor_x -= 1
        elif key == ord('j'):  # Move down
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
        elif key == ord('k'):  # Move up
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
        elif key == ord('l'):  # Move right
            line = self.buffer.get_lines()[self.cursor_y]
            if self.cursor_x < len(line) - 1:
                self.cursor_x += 1
        elif key == curses.KEY_LEFT and self.cursor_x > 0:
            self.cursor_x -= 1
        elif key == curses.KEY_DOWN and self.cursor_y < len(self.buffer.get_lines()) - 1:
            self.cursor_y += 1
            self._adjust_cursor_x()
        elif key == curses.KEY_UP and self.cursor_y > 0:
            self.cursor_y -= 1
            self._adjust_cursor_x()
        elif key == curses.KEY_RIGHT:
            line = self.buffer.get_lines()[self.cursor_y]
            if self.cursor_x < len(line) - 1:
                self.cursor_x += 1
        elif key == 5:  # Ctrl+E for version navigation (forward)
            self.history.next_version()
            self.buffer.set_lines(self.history.get_current_version())
            self.status_message = f"Version: {self.history.current_index + 1}/{len(self.history.versions)}"
        elif key == 23:  # Ctrl+W for version navigation (backward)
            self.history.previous_version()
            self.buffer.set_lines(self.history.get_current_version())
            self.status_message = f"Version: {self.history.current_index + 1}/{len(self.history.versions)}"
    
    def _handle_insert_mode(self, key: int) -> None:
        """Handle keypresses in insert mode"""
        if key == 27:  # ESC key to return to normal mode
            self.mode = Mode.NORMAL
            self.status_message = "-- NORMAL --"
        elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            if self.cursor_x > 0:
                line = self.buffer.get_lines()[self.cursor_y]
                new_line = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.buffer.set_line(self.cursor_y, new_line)
                self.cursor_x -= 1
            elif self.cursor_y > 0:  # Join with previous line
                current_line = self.buffer.get_lines()[self.cursor_y]
                prev_line = self.buffer.get_lines()[self.cursor_y-1]
                self.cursor_x = len(prev_line)
                self.buffer.set_line(self.cursor_y-1, prev_line + current_line)
                self.buffer.delete_line(self.cursor_y)
                self.cursor_y -= 1
        elif key == curses.KEY_ENTER or key == 10 or key == 13:  # Enter key
            current_line = self.buffer.get_lines()[self.cursor_y]
            self.buffer.set_line(self.cursor_y, current_line[:self.cursor_x])
            self.buffer.insert_line(self.cursor_y + 1, current_line[self.cursor_x:])
            self.cursor_y += 1
            self.cursor_x = 0
        else:  # Regular character input
            try:
                char = chr(key)
                line = self.buffer.get_lines()[self.cursor_y]
                new_line = line[:self.cursor_x] + char + line[self.cursor_x:]
                self.buffer.set_line(self.cursor_y, new_line)
                self.cursor_x += 1
            except:
                pass  # Ignore non-character keys
    
    def _handle_visual_mode(self, key: int) -> None:
        """Handle keypresses in visual mode"""
        if key == 27:  # ESC key to return to normal mode
            self.mode = Mode.NORMAL
            self.status_message = "-- NORMAL --"
            self.buffer.end_selection()
        elif key == ord('h') and self.cursor_x > 0:
            self.cursor_x -= 1
            self.buffer.update_selection(self.cursor_y, self.cursor_x)
        elif key == ord('j') and self.cursor_y < len(self.buffer.get_lines()) - 1:
            self.cursor_y += 1
            self._adjust_cursor_x()
            self.buffer.update_selection(self.cursor_y, self.cursor_x)
        elif key == ord('k') and self.cursor_y > 0:
            self.cursor_y -= 1
            self._adjust_cursor_x()
            self.buffer.update_selection(self.cursor_y, self.cursor_x)
        elif key == ord('l'):
            line = self.buffer.get_lines()[self.cursor_y]
            if self.cursor_x < len(line) - 1:
                self.cursor_x += 1
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
    
    def _handle_command_mode(self, key: int) -> None:
        """Handle keypresses in command mode"""
        if key == 27:  # ESC key to cancel
            self.mode = Mode.NORMAL
            self.command_line = ""
            self.status_message = "-- NORMAL --"
        elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            if len(self.command_line) > 1:  # Preserve the initial ':'
                self.command_line = self.command_line[:-1]
        elif key == curses.KEY_ENTER or key == 10 or key == 13:  # Execute command
            self._process_command()
            self.mode = Mode.NORMAL
            self.command_line = ""
        else:
            try:
                char = chr(key)
                self.command_line += char
            except:
                pass  # Ignore non-character keys
    
    def _process_command(self) -> None:
        """Process entered command"""
        command = self.command_line[1:].strip()
        self.command_processor.process(command)
    
    def _adjust_cursor_x(self) -> None:
        """Adjust cursor x position when moving vertically"""
        if self.cursor_y < len(self.buffer.get_lines()):
            line_length = len(self.buffer.get_lines()[self.cursor_y])
            if self.cursor_x > line_length - 1:
                self.cursor_x = max(0, line_length - 1)
    
    def run_ai_command(self, command: str, args: List[str]) -> None:
        """Run an AI-related command in a separate thread"""
        if self.ai_processing:
            self.status_message = "AI is already processing a request"
            return
        
        self.ai_processing = True
        self.status_message = "Processing AI request..."
        
        # Start AI processing in a separate thread
        self.ai_thread = threading.Thread(
            target=self._execute_ai_command,
            args=(command, args)
        )
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def _execute_ai_command(self, command: str, args: List[str]) -> None:
        """Execute an AI command in a separate thread"""
        try:
            start_line, end_line = 0, 0
            if len(args) >= 2:
                try:
                    start_line = int(args[0]) - 1  # Convert to 0-based indexing
                    end_line = int(args[1]) - 1
                except ValueError:
                    self.status_message = "Invalid line numbers"
                    self.ai_processing = False
                    return
            
            # Validate line numbers
            if start_line < 0 or end_line >= len(self.buffer.get_lines()) or start_line > end_line:
                self.status_message = "Invalid line range"
                self.ai_processing = False
                return
            
            # Get the code context
            code_lines = self.buffer.get_lines()[start_line:end_line+1]
            code_context = "\n".join(code_lines)
            
            # Get additional context (surrounding code)
            context_start = max(0, start_line - 5)
            context_end = min(len(self.buffer.get_lines()) - 1, end_line + 5)
            full_context = "\n".join(self.buffer.get_lines()[context_start:context_end+1])
            
            result = None
            if command == "explain":
                result = self.ai_service.get_explanation(code_context, full_context)
            elif command == "improve":
                result = self.ai_service.get_improvement(code_context, full_context)
            elif command == "generate":
                result = self.ai_service.generate_code(code_context, full_context)
            elif command == "ai":
                query = " ".join(args)
                result = self.ai_service.custom_query(query, full_context)
            
            if result:
                # Create a new version with the AI result
                new_lines = self.buffer.get_lines().copy()
                result_lines = result.strip().split('\n')
                
                if command == "explain" or command == "ai":
                    # Insert explanation as comments above the selected code
                    comment_lines = []
                    for line in result_lines:
                        comment_lines.append(f"# {line}")
                    new_lines[start_line:start_line] = comment_lines
                else:  # improve or generate
                    # Replace the selected code with the improved version
                    new_lines[start_line:end_line+1] = result_lines
                
                # Add the new version to history
                self.history.add_version(new_lines)
                
                # Set the buffer to the new version
                self.buffer.set_lines(new_lines)
                
                self.status_message = f"AI processing complete. Use Ctrl+E/Ctrl+W to navigate versions."
            else:
                self.status_message = "AI processing failed or returned empty result"
        
        except Exception as e:
            self.status_message = f"AI processing error: {str(e)}"
        
        finally:
            self.ai_processing = False
    
    def quit(self, force: bool = False) -> None:
        """Quit the editor"""
        if not force and self.buffer.is_modified():
            self.status_message = "Unsaved changes. Use :q! to force quit."
            return
        self.running = False
