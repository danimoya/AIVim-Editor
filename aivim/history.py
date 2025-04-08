"""
Version history management for AIVim
"""
from typing import List, Dict, Any, Optional


class VersionHistory:
    """
    Manages version history for the editor buffer
    Particularly useful for AI modifications
    """
    def __init__(self):
        """Initialize version history"""
        self._versions = []  # List of (lines, metadata) tuples
        self._current_index = -1
    
    def add_version(self, lines: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new version to the history
        
        Args:
            lines: The lines of content for this version
            metadata: Optional metadata about this version (e.g., AI command used)
        """
        # Create a copy of the lines to prevent reference issues
        lines_copy = lines.copy()
        metadata_copy = metadata.copy() if metadata else {}
        
        # If we're not at the end of the history, truncate it
        if self._current_index < len(self._versions) - 1:
            self._versions = self._versions[:self._current_index + 1]
        
        # Add the new version
        self._versions.append((lines_copy, metadata_copy))
        self._current_index = len(self._versions) - 1
    
    def get_current_version(self) -> List[str]:
        """Get the current version's content"""
        if not self._versions:
            return [""]
        return self._versions[self._current_index][0].copy()
    
    def get_current_metadata(self) -> Dict[str, Any]:
        """Get metadata for the current version"""
        if not self._versions:
            return {}
        return self._versions[self._current_index][1].copy()
    
    def next_version(self) -> bool:
        """
        Move to the next version if available
        
        Returns:
            True if successfully moved, False if already at newest version
        """
        if self._current_index < len(self._versions) - 1:
            self._current_index += 1
            return True
        return False
    
    def previous_version(self) -> bool:
        """
        Move to the previous version if available
        
        Returns:
            True if successfully moved, False if already at oldest version
        """
        if self._current_index > 0:
            self._current_index -= 1
            return True
        return False
    
    def has_next(self) -> bool:
        """Check if there is a next version available"""
        return self._current_index < len(self._versions) - 1
    
    def has_previous(self) -> bool:
        """Check if there is a previous version available"""
        return self._current_index > 0
    
    def get_version_count(self) -> int:
        """Get the total number of versions in history"""
        return len(self._versions)