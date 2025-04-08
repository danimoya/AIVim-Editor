"""
Utility functions for AIVim
"""
import difflib
import os
import re
import datetime
import shutil
from typing import List, Tuple, Optional


def create_diff(old_text: str, new_text: str) -> List[str]:
    """
    Create a diff between old and new text
    
    Args:
        old_text: Original text
        new_text: Modified text
        
    Returns:
        List of formatted diff lines
    """
    # Split into lines
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    # Get diff
    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm='',
        n=2  # Context lines
    ))
    
    # If there's no diff, return a message
    if not diff:
        return ["No differences found."]
    
    # Create colorized diff lines
    colorized_diff = []
    for line in diff:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            # Header lines
            colorized_diff.append(f"HEADER|{line}")
        elif line.startswith('+'):
            # Added lines
            colorized_diff.append(f"ADDED|{line}")
        elif line.startswith('-'):
            # Removed lines
            colorized_diff.append(f"REMOVED|{line}")
        else:
            # Context lines
            colorized_diff.append(f"CONTEXT|{line}")
            
    return colorized_diff


def split_diff_line(line: str) -> Tuple[str, str]:
    """
    Split a colorized diff line into type and content
    
    Args:
        line: Colorized diff line with format "TYPE|content"
        
    Returns:
        Tuple of (type, content)
    """
    parts = line.split('|', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "CONTEXT", line


def tokenize_command(command: str) -> List[str]:
    """
    Tokenize a command string into a list of tokens
    
    Args:
        command: Command string
        
    Returns:
        List of command tokens
    """
    # Match quoted strings or space-separated tokens
    pattern = r'\"([^\"]*)\"|\'([^\']*)\'|(\S+)'
    matches = re.finditer(pattern, command)
    
    tokens = []
    for match in matches:
        # Get the matched group (either quoted or unquoted)
        if match.group(1) is not None:
            # Double-quoted string
            tokens.append(match.group(1))
        elif match.group(2) is not None:
            # Single-quoted string
            tokens.append(match.group(2))
        else:
            # Unquoted token
            tokens.append(match.group(3))
    
    return tokens


def parse_line_range(start_line: str, end_line: str) -> Tuple[int, int]:
    """
    Parse line range from string inputs
    
    Args:
        start_line: Starting line number (1-based)
        end_line: Ending line number (1-based)
        
    Returns:
        Tuple of (start, end) in 0-based indexing, or (-1, -1) if invalid
    """
    try:
        start = int(start_line) - 1  # Convert to 0-based
        end = int(end_line)  # End is exclusive in Python slices
        
        if start < 0:
            return (-1, -1)
            
        return (start, end)
    except ValueError:
        return (-1, -1)


def create_backup_file(filename: str) -> str:
    """
    Create a backup of the given file with timestamp
    
    Args:
        filename: Path to the file to backup
        
    Returns:
        Path to the backup file
    """
    if not os.path.exists(filename):
        return ""
        
    # Get the directory and base name
    directory = os.path.dirname(filename)
    basename = os.path.basename(filename)
    
    # Create timestamp in format YYYYMMDDHHMMSS
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Create backup filename (.filename.timestamp)
    backup_name = f".{basename}.{timestamp}"
    backup_path = os.path.join(directory, backup_name)
    
    # Copy the file
    try:
        shutil.copy2(filename, backup_path)
        return backup_path
    except Exception as e:
        import logging
        logging.error(f"Failed to create backup file: {str(e)}")
        return ""