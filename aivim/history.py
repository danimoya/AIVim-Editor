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
        self.versions: List[List[str]] = []
        self.current_index: int = -1
        self.metadata: List[Dict[str, Any]] = []
    
    def add_version(self, lines: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new version to the history
        
        Args:
            lines: The lines of content for this version
            metadata: Optional metadata about this version (e.g., AI command used)
        """
        # If we're not at the latest version, truncate history
        if self.current_index < len(self.versions) - 1:
            self.versions = self.versions[:self.current_index + 1]
            self.metadata = self.metadata[:self.current_index + 1]
        
        # Add the new version
        self.versions.append(lines.copy())
        self.metadata.append(metadata or {})
        self.current_index = len(self.versions) - 1
    
    def get_current_version(self) -> List[str]:
        """Get the current version's content"""
        if not self.versions:
            return [""]
        
        return self.versions[self.current_index]
    
    def get_current_metadata(self) -> Dict[str, Any]:
        """Get metadata for the current version"""
        if not self.metadata or self.current_index < 0:
            return {}
        
        return self.metadata[self.current_index]
    
    def next_version(self) -> bool:
        """
        Move to the next version if available
        
        Returns:
            True if successfully moved, False if already at newest version
        """
        if self.current_index < len(self.versions) - 1:
            self.current_index += 1
            return True
        return False
    
    def previous_version(self) -> bool:
        """
        Move to the previous version if available
        
        Returns:
            True if successfully moved, False if already at oldest version
        """
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def has_next(self) -> bool:
        """Check if there is a next version available"""
        return self.current_index < len(self.versions) - 1
    
    def has_previous(self) -> bool:
        """Check if there is a previous version available"""
        return self.current_index > 0
    
    def get_version_count(self) -> int:
        """Get the total number of versions in history"""
        return len(self.versions)
