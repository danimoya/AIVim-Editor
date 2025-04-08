"""
Version history management for AIVim
"""
from typing import List, Dict, Any, Tuple, Optional
import copy
import time


class History:
    """
    Manages version history for the editor
    """
    def __init__(self, max_history: int = 100):
        """
        Initialize the history manager
        
        Args:
            max_history: Maximum number of versions to keep
        """
        self.versions = []
        self.metadata = []
        self.current_index = -1
        self.max_history = max_history
    
    def add_version(self, lines: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new version to the history
        
        Args:
            lines: The buffer lines for this version
            metadata: Optional metadata about the changes
        """
        # Deep copy to ensure we don't have references to mutable objects
        lines_copy = copy.deepcopy(lines)
        metadata_copy = copy.deepcopy(metadata) if metadata else {}
        
        # Add timestamp to metadata
        metadata_copy["timestamp"] = time.time()
        
        # If we're in the middle of the history, discard anything after current_index
        if self.current_index < len(self.versions) - 1:
            self.versions = self.versions[:self.current_index + 1]
            self.metadata = self.metadata[:self.current_index + 1]
        
        # Add new version
        self.versions.append(lines_copy)
        self.metadata.append(metadata_copy)
        self.current_index = len(self.versions) - 1
        
        # Prune history if needed
        self._prune_history()
    
    def _prune_history(self) -> None:
        """Remove oldest history items if we exceed the maximum"""
        if len(self.versions) > self.max_history:
            # Keep the most recent max_history versions
            excess = len(self.versions) - self.max_history
            self.versions = self.versions[excess:]
            self.metadata = self.metadata[excess:]
            self.current_index -= excess
    
    def can_undo(self) -> bool:
        """Check if we can undo"""
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """Check if we can redo"""
        return self.current_index < len(self.versions) - 1
    
    def undo(self) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
        """
        Undo to the previous version
        
        Returns:
            Tuple of (lines, metadata) for the previous version,
            or (None, None) if there's no previous version
        """
        if not self.can_undo():
            return None, None
        
        self.current_index -= 1
        return (
            copy.deepcopy(self.versions[self.current_index]),
            copy.deepcopy(self.metadata[self.current_index])
        )
    
    def redo(self) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
        """
        Redo to the next version
        
        Returns:
            Tuple of (lines, metadata) for the next version,
            or (None, None) if there's no next version
        """
        if not self.can_redo():
            return None, None
        
        self.current_index += 1
        return (
            copy.deepcopy(self.versions[self.current_index]),
            copy.deepcopy(self.metadata[self.current_index])
        )
    
    def get_current_version(self) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
        """
        Get the current version
        
        Returns:
            Tuple of (lines, metadata) for the current version,
            or (None, None) if there's no history
        """
        if self.current_index < 0 or not self.versions:
            return None, None
        
        return (
            copy.deepcopy(self.versions[self.current_index]),
            copy.deepcopy(self.metadata[self.current_index])
        )
    
    def get_version_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all versions in the history
        
        Returns:
            List of version metadata dictionaries
        """
        result = []
        for i, meta in enumerate(self.metadata):
            info = copy.deepcopy(meta)
            info["index"] = i
            info["is_current"] = (i == self.current_index)
            result.append(info)
        return result
    
    def clear(self) -> None:
        """Clear all history"""
        self.versions = []
        self.metadata = []
        self.current_index = -1