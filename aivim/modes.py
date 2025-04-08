"""
Mode definitions for AIVim
"""
from enum import Enum, auto


class Mode(Enum):
    """
    Editor modes, similar to standard Vim modes
    """
    NORMAL = auto()   # Default mode for navigation and commands
    INSERT = auto()   # Mode for inserting text
    VISUAL = auto()   # Mode for selecting text
    COMMAND = auto()  # Mode for entering commands
