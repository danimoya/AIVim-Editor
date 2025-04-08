"""
Core editor implementation for AIVim
"""
import curses
import logging
import os
import threading
import time
from typing import List, Optional, Tuple, Dict, Any

from aivim.ai_service import AIService
from aivim.buffer import Buffer
from aivim.commands import CommandProcessor
from aivim.display import Display
from aivim.history import VersionHistory
from aivim.modes import Mode
from aivim.utils import clamp


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
        self.filename = filename
        self.buffer = Buffer()
        self.history = VersionHistory()
        self.ai_service = AIService()
        self.command_processor = CommandProcessor(self)
        
        self.mode = Mode.NORMAL
        self.cursor_y = 0
        self.cursor_x = 0
        self.preferred_x = 0  # For maintaining horizontal position during vertical movement
        self.command_line = ""
        self.status_message = ""
        self.ai_processing = False
        self.should_quit = False
        
        # Threading objects
        self.ai_thread = None
        self.thread_lock = threading.Lock()
        
        # Load file if specified
        if filename:
            self.load_file(filename)
    
    def load_file(self, filename: str) -> None:
        """Load content from a file into the buffer"""
        try:
            self.filename = filename
            if os.path.isfile(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                self.buffer.set_content(content)
                self.buffer.mark_as_saved()
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"Loaded {filename}")
            else:
                self.buffer.set_content("")
                self.buffer.mark_as_saved()
                self.history.add_version(self.buffer.get_lines())
                self.set_status_message(f"New file: {filename}")
        except Exception as e:
            self.set_status_message(f"Error loading file: {str(e)}")
            logging.error(f"Error loading file {filename}: {str(e)}")
    
    def save_file(self, filename: Optional[str] = None) -> None:
        """Save buffer content to a file"""
        if filename:
            self.filename = filename
        
        if not self.filename:
            self.set_status_message("No filename specified")
            return
        
        try:
            with open(self.filename, 'w') as f:
                f.write(self.buffer.get_content())
            self.buffer.mark_as_saved()
            self.set_status_message(f"Saved {self.filename}")
        except Exception as e:
            self.set_status_message(f"Error saving file: {str(e)}")
            logging.error(f"Error saving file {self.filename}: {str(e)}")
    
    def start(self, stdscr) -> None:
        """Initialize and start the editor with curses"""
        self.display = Display(stdscr)
        self.display.setup()
        
        while not self.should_quit:
            # Get selection for display
            start_pos, end_pos = self.buffer.get_selection()
            selection = None
            if start_pos and end_pos:
                selection = (start_pos, end_pos)
            
            # Refresh display
            self.display.refresh(
                self.buffer.get_lines(),
                self.cursor_y,
                self.cursor_x,
                self.mode,
                self.command_line,
                self.status_message,
                self.ai_processing,
                selection
            )
            
            # Handle input
            try:
                key = stdscr.getch()
                self.handle_input(key)
            except Exception as e:
                self.set_status_message(f"Error: {str(e)}")
                logging.error(f"Error handling input: {str(e)}")
    
    def handle_input(self, key: int) -> None:
        """Process user input based on current mode"""
        # Clear status message when user starts typing
        if self.status_message and key != curses.KEY_RESIZE:
            self.status_message = ""
        
        # Handle mode-specific input
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
        lines = self.buffer.get_lines()
        
        # Global shortcuts
        if key == 5:  # Ctrl+E - Next version
            if self.history.next_version():
                self.buffer.set_lines(self.history.get_current_version())
                self.set_status_message("Moved to next version")
            else:
                self.set_status_message("Already at newest version")
            return
        elif key == 23:  # Ctrl+W - Previous version
            if self.history.previous_version():
                self.buffer.set_lines(self.history.get_current_version())
                self.set_status_message("Moved to previous version")
            else:
                self.set_status_message("Already at oldest version")
            return
        
        # Navigation
        if key == ord('h') or key == curses.KEY_LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
            self.preferred_x = self.cursor_x
        elif key == ord('j') or key == curses.KEY_DOWN:
            if self.cursor_y < len(lines) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
        elif key == ord('k') or key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
        elif key == ord('l') or key == curses.KEY_RIGHT:
            if self.cursor_y < len(lines) and self.cursor_x < len(lines[self.cursor_y]):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
        
        # Mode changing
        elif key == ord('i'):
            self.mode = Mode.INSERT
        elif key == ord('v'):
            self.mode = Mode.VISUAL
            self.buffer.start_selection(self.cursor_y, self.cursor_x)
        elif key == ord(':'):
            self.mode = Mode.COMMAND
            self.command_line = ":"
        
        # Line operations
        elif key == ord('o'):
            # Open line below
            self.buffer.insert_line(self.cursor_y + 1, "")
            self.cursor_y += 1
            self.cursor_x = 0
            self.preferred_x = 0
            self.mode = Mode.INSERT
        elif key == ord('O'):
            # Open line above
            self.buffer.insert_line(self.cursor_y, "")
            self.cursor_x = 0
            self.preferred_x = 0
            self.mode = Mode.INSERT
        elif key == ord('d') and self.cursor_y < len(lines):
            # Delete line (dd)
            next_key = self.display.stdscr.getch()
            if next_key == ord('d'):
                self.buffer.delete_line(self.cursor_y)
                if self.cursor_y >= len(self.buffer.get_lines()):
                    self.cursor_y = max(0, len(self.buffer.get_lines()) - 1)
                self._adjust_cursor_x()
    
    def _handle_insert_mode(self, key: int) -> None:
        """Handle keypresses in insert mode"""
        if key == 27:  # ESC
            self.mode = Mode.NORMAL
            # Move cursor back if at end of line
            if self.cursor_x > 0 and self.cursor_y < len(self.buffer.get_lines()):
                line = self.buffer.get_line(self.cursor_y)
                if self.cursor_x >= len(line):
                    self.cursor_x = max(0, len(line) - 1)
        
        elif key == curses.KEY_BACKSPACE:
            # Delete character before cursor
            if self.cursor_x > 0:
                line = self.buffer.get_line(self.cursor_y)
                new_line = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.buffer.set_line(self.cursor_y, new_line)
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
            elif self.cursor_y > 0:
                # At start of line, join with previous line
                prev_line = self.buffer.get_line(self.cursor_y - 1)
                curr_line = self.buffer.get_line(self.cursor_y)
                self.cursor_x = len(prev_line)
                self.preferred_x = self.cursor_x
                self.buffer.set_line(self.cursor_y - 1, prev_line + curr_line)
                self.buffer.delete_line(self.cursor_y)
                self.cursor_y -= 1
        
        elif key == 10:  # Enter
            # Split line at cursor
            line = self.buffer.get_line(self.cursor_y)
            self.buffer.set_line(self.cursor_y, line[:self.cursor_x])
            self.buffer.insert_line(self.cursor_y + 1, line[self.cursor_x:])
            self.cursor_y += 1
            self.cursor_x = 0
            self.preferred_x = 0
        
        elif key == curses.KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.preferred_x = self.cursor_x
        
        elif key == curses.KEY_RIGHT:
            line = self.buffer.get_line(self.cursor_y)
            if self.cursor_x < len(line):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
        
        elif key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
        
        elif key == curses.KEY_DOWN:
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
        
        elif 32 <= key <= 126:  # Printable ASCII
            # Insert character at cursor
            char = chr(key)
            line = self.buffer.get_line(self.cursor_y)
            new_line = line[:self.cursor_x] + char + line[self.cursor_x:]
            self.buffer.set_line(self.cursor_y, new_line)
            self.cursor_x += 1
            self.preferred_x = self.cursor_x
    
    def _handle_visual_mode(self, key: int) -> None:
        """Handle keypresses in visual mode"""
        if key == 27:  # ESC
            self.mode = Mode.NORMAL
            self.buffer.end_selection()
        
        # Navigation (update selection end)
        elif key == ord('h') or key == curses.KEY_LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
            self.preferred_x = self.cursor_x
            self.buffer.update_selection(self.cursor_y, self.cursor_x)
        
        elif key == ord('j') or key == curses.KEY_DOWN:
            if self.cursor_y < len(self.buffer.get_lines()) - 1:
                self.cursor_y += 1
                self._adjust_cursor_x()
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
        
        elif key == ord('k') or key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self._adjust_cursor_x()
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
        
        elif key == ord('l') or key == curses.KEY_RIGHT:
            if self.cursor_y < len(self.buffer.get_lines()) and self.cursor_x < len(self.buffer.get_line(self.cursor_y)):
                self.cursor_x += 1
                self.preferred_x = self.cursor_x
                self.buffer.update_selection(self.cursor_y, self.cursor_x)
    
    def _handle_command_mode(self, key: int) -> None:
        """Handle keypresses in command mode"""
        if key == 27:  # ESC
            self.mode = Mode.NORMAL
            self.command_line = ""
        
        elif key == 10:  # Enter
            self._process_command()
            self.mode = Mode.NORMAL
            self.command_line = ""
        
        elif key == curses.KEY_BACKSPACE:
            if len(self.command_line) > 1:  # Keep the ':'
                self.command_line = self.command_line[:-1]
            else:
                self.mode = Mode.NORMAL
                self.command_line = ""
        
        elif 32 <= key <= 126:  # Printable ASCII
            self.command_line += chr(key)
    
    def _process_command(self) -> None:
        """Process entered command"""
        if not self.command_line or len(self.command_line) <= 1:
            return
        
        command = self.command_line[1:]  # Remove the initial ':'
        self.command_processor.process(command)
    
    def _adjust_cursor_x(self) -> None:
        """Adjust cursor x position when moving vertically"""
        if self.cursor_y < len(self.buffer.get_lines()):
            line_length = len(self.buffer.get_line(self.cursor_y))
            self.cursor_x = min(self.preferred_x, line_length)
        else:
            self.cursor_x = 0
    
    def set_status_message(self, message: str) -> None:
        """Set the status message"""
        self.status_message = message
        logging.info(f"Status: {message}")
    
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
                # Split into lines of appropriate width
                explanation_lines = explanation.split("\n")
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Explanation ready")
                
                # Show dialog
                self.display.show_dialog("Code Explanation", explanation_lines)
        
        except Exception as e:
            with self.thread_lock:
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
            
            # Apply changes in main thread
            with self.thread_lock:
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
                self.ai_processing = False
                self.set_status_message(f"Improved {len(improved_lines)} lines of code")
                
                # Show the explanation in a dialog if there's more than just code
                if improvement != improved_code:
                    explanation_lines = improvement.split("\n")
                    self.display.show_dialog("Code Improvement", explanation_lines)
        
        except Exception as e:
            with self.thread_lock:
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
                # Split into lines
                response_lines = response.split("\n")
                
                # Update status
                self.ai_processing = False
                self.set_status_message("Query response ready")
                
                # Show dialog
                self.display.show_dialog("Query Response", response_lines)
        
        except Exception as e:
            with self.thread_lock:
                self.ai_processing = False
                self.set_status_message(f"Error processing query: {str(e)}")
            logging.error(f"AI query error: {str(e)}")
    
    def quit(self, force: bool = False) -> None:
        """Quit the editor"""
        if not force and self.buffer.is_modified():
            self.set_status_message("No write since last change (use :q! to override)")
            return
        
        self.should_quit = True