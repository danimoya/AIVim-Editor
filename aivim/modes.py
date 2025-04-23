"""
Mode definitions for AIVim
"""
from enum import Enum


class Mode(Enum):
    """Editor operating modes"""
    NORMAL = 1  # Default mode for navigation and commands
    INSERT = 2  # Mode for inserting text
    VISUAL = 3  # Mode for selecting text
    COMMAND = 4  # Mode for entering commands in the command line
    NLP = 5     # Natural Language Programming mode