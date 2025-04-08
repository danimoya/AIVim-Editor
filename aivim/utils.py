"""
Utility functions for AIVim
"""
import curses
from typing import List, Dict, Any, Optional


def clamp(value: int, min_val: int, max_val: int) -> int:
    """
    Clamp a value between a minimum and maximum
    
    Args:
        value: The value to clamp
        min_val: The minimum allowed value
        max_val: The maximum allowed value
        
    Returns:
        The clamped value
    """
    return max(min_val, min(value, max_val))


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries with dict2 taking precedence
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (will override dict1 values)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    result.update(dict2)
    return result


def get_color_pair(fg_color: int, bg_color: int) -> int:
    """
    Get or create a curses color pair
    
    Args:
        fg_color: Foreground color
        bg_color: Background color
        
    Returns:
        Color pair number
    """
    # Use a hash of the color combination to create a unique identifier
    pair_id = (fg_color * 10 + bg_color) % curses.COLOR_PAIRS
    
    # Initialize the color pair
    try:
        curses.init_pair(pair_id, fg_color, bg_color)
    except Exception:
        pass  # Color already defined or terminal doesn't support color
    
    return pair_id


def tokenize_command(command: str) -> List[str]:
    """
    Tokenize a command string, respecting quoted strings
    
    Args:
        command: The command string
        
    Returns:
        List of command tokens
    """
    tokens = []
    current_token = ""
    in_quotes = False
    quote_char = None
    
    for char in command:
        if char in ['"', "'"]:
            if not in_quotes:
                # Start of quoted string
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                # End of quoted string
                in_quotes = False
                quote_char = None
            else:
                # Different quote character within quoted string
                current_token += char
        elif char.isspace() and not in_quotes:
            # Space outside quotes - end of token
            if current_token:
                tokens.append(current_token)
                current_token = ""
        else:
            # Regular character
            current_token += char
    
    # Add final token if any
    if current_token:
        tokens.append(current_token)
    
    return tokens


def parse_line_range(start_str: str, end_str: Optional[str] = None) -> tuple[int, int]:
    """
    Parse a line range specification
    
    Args:
        start_str: Start line number as string (1-based)
        end_str: End line number as string (1-based)
        
    Returns:
        Tuple of (start, end) line numbers (0-based)
    """
    try:
        start = int(start_str) - 1  # Convert to 0-based
        if end_str:
            end = int(end_str) - 1  # Convert to 0-based
        else:
            end = start
        return start, end
    except ValueError:
        return -1, -1  # Invalid input