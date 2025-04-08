"""
Buffer implementation for AIVim
"""
from typing import List, Tuple, Optional


class Buffer:
    """
    Represents an editing buffer that holds text content
    """
    def __init__(self):
        self._lines: List[str] = [""]
        self._modified: bool = False
        self._selection_start: Optional[Tuple[int, int]] = None
        self._selection_end: Optional[Tuple[int, int]] = None
    
    def get_lines(self) -> List[str]:
        """Get all lines in the buffer"""
        return self._lines
    
    def get_line(self, index: int) -> str:
        """Get a specific line by index"""
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return ""
    
    def set_line(self, index: int, content: str) -> None:
        """Set the content of a specific line"""
        if 0 <= index < len(self._lines):
            self._lines[index] = content
            self._modified = True
    
    def insert_line(self, index: int, content: str) -> None:
        """Insert a new line at the specified index"""
        if 0 <= index <= len(self._lines):
            self._lines.insert(index, content)
            self._modified = True
    
    def delete_line(self, index: int) -> None:
        """Delete the line at the specified index"""
        if 0 <= index < len(self._lines):
            self._lines.pop(index)
            self._modified = True
            # Ensure there's always at least one line
            if not self._lines:
                self._lines = [""]
    
    def get_content(self) -> str:
        """Get the entire buffer content as a string"""
        return "\n".join(self._lines)
    
    def set_content(self, content: str) -> None:
        """Set the entire buffer content"""
        self._lines = content.split("\n")
        if not self._lines:
            self._lines = [""]
        self._modified = False
    
    def set_lines(self, lines: List[str]) -> None:
        """Set all lines in the buffer"""
        self._lines = lines.copy()
        if not self._lines:
            self._lines = [""]
        self._modified = True
    
    def is_modified(self) -> bool:
        """Check if the buffer has been modified"""
        return self._modified
    
    def mark_as_saved(self) -> None:
        """Mark the buffer as saved (not modified)"""
        self._modified = False
    
    def start_selection(self, y: int, x: int) -> None:
        """Start a selection at the specified position"""
        self._selection_start = (y, x)
        self._selection_end = (y, x)
    
    def update_selection(self, y: int, x: int) -> None:
        """Update the end point of the current selection"""
        if self._selection_start:
            self._selection_end = (y, x)
    
    def end_selection(self) -> None:
        """End the current selection"""
        self._selection_start = None
        self._selection_end = None
    
    def get_selection(self) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Get the current selection start and end points"""
        return (self._selection_start, self._selection_end)
    
    def get_selection_text(self) -> str:
        """Get the text in the current selection"""
        if not self._selection_start or not self._selection_end:
            return ""
        
        start_y, start_x = self._selection_start
        end_y, end_x = self._selection_end
        
        # Ensure start is before end
        if start_y > end_y or (start_y == end_y and start_x > end_x):
            start_y, start_x, end_y, end_x = end_y, end_x, start_y, start_x
        
        if start_y == end_y:
            # Selection is within a single line
            return self._lines[start_y][start_x:end_x+1]
        else:
            # Selection spans multiple lines
            result = [self._lines[start_y][start_x:]]  # First line
            for y in range(start_y + 1, end_y):  # Middle lines
                result.append(self._lines[y])
            result.append(self._lines[end_y][:end_x+1])  # Last line
            return "\n".join(result)
