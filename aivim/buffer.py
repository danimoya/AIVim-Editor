"""
Buffer implementation for AIVim
"""
from typing import List, Optional, Tuple


class Buffer:
    """
    Represents an editing buffer that holds text content
    """
    def __init__(self):
        """Initialize an empty buffer"""
        self.lines = [""]
        self.modified = False
        
        # Selection state
        self.selection_start = None  # (y, x)
        self.selection_end = None  # (y, x)
    
    def get_lines(self) -> List[str]:
        """Get all lines in the buffer"""
        return self.lines
    
    def get_line(self, index: int) -> str:
        """Get a specific line by index"""
        if 0 <= index < len(self.lines):
            return self.lines[index]
        return ""
    
    def set_line(self, index: int, content: str) -> None:
        """Set the content of a specific line"""
        if 0 <= index < len(self.lines):
            if self.lines[index] != content:
                self.lines[index] = content
                self.modified = True
    
    def insert_line(self, index: int, content: str) -> None:
        """Insert a new line at the specified index"""
        if 0 <= index <= len(self.lines):
            self.lines.insert(index, content)
            self.modified = True
    
    def delete_line(self, index: int) -> None:
        """Delete the line at the specified index"""
        if 0 <= index < len(self.lines):
            del self.lines[index]
            # Ensure buffer always has at least one line
            if not self.lines:
                self.lines = [""]
            self.modified = True
    
    def get_content(self) -> str:
        """Get the entire buffer content as a string"""
        return "\n".join(self.lines)
    
    def set_content(self, content: str) -> None:
        """Set the entire buffer content"""
        if content:
            self.lines = content.split("\n")
        else:
            self.lines = [""]
        self.modified = True
    
    def set_lines(self, lines: List[str]) -> None:
        """Set all lines in the buffer"""
        if lines:
            self.lines = lines.copy()
        else:
            self.lines = [""]
        self.modified = True
    
    def is_modified(self) -> bool:
        """Check if the buffer has been modified"""
        return self.modified
    
    def mark_as_saved(self) -> None:
        """Mark the buffer as saved (not modified)"""
        self.modified = False
    
    def start_selection(self, y: int, x: int) -> None:
        """Start a selection at the specified position"""
        self.selection_start = (y, x)
        self.selection_end = (y, x)
    
    def update_selection(self, y: int, x: int) -> None:
        """Update the end point of the current selection"""
        self.selection_end = (y, x)
    
    def end_selection(self) -> None:
        """End the current selection"""
        self.selection_start = None
        self.selection_end = None
    
    def get_selection(self) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Get the current selection start and end points"""
        return (self.selection_start, self.selection_end)
    
    def get_selection_text(self) -> str:
        """Get the text in the current selection"""
        if not self.selection_start or not self.selection_end:
            return ""
        
        start_y, start_x = self.selection_start
        end_y, end_x = self.selection_end
        
        # Ensure start is before end
        if (start_y > end_y) or (start_y == end_y and start_x > end_x):
            start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
        
        if start_y == end_y:
            # Single line selection
            return self.lines[start_y][start_x:end_x]
        
        # Multi-line selection
        result = [self.lines[start_y][start_x:]]
        for i in range(start_y + 1, end_y):
            result.append(self.lines[i])
        result.append(self.lines[end_y][:end_x])
        
        return "\n".join(result)
        
    def clear(self) -> None:
        """Clear the buffer contents"""
        self.lines = [""]
        self.modified = True
        self.selection_start = None
        self.selection_end = None