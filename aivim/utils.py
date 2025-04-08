"""
Utility functions for AIVim
"""
import os
import sys
import curses
from typing import Optional, Callable, Any


def safe_exit(stdscr: Optional[Any] = None) -> None:
    """
    Safely exit the application, restoring terminal state
    
    Args:
        stdscr: The curses standard screen object, if available
    """
    if stdscr:
        # End curses
        stdscr.keypad(False)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
    
    # Exit the program
    sys.exit(0)


def get_file_type(filename: str) -> str:
    """
    Determine the type of file based on extension
    
    Args:
        filename: The name of the file
        
    Returns:
        A string representing the file type
    """
    if not filename:
        return "unknown"
    
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    file_types = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.txt': 'text',
    }
    
    return file_types.get(ext, "unknown")


def run_with_curses(func: Callable) -> None:
    """
    Run a function with properly initialized curses environment
    
    Args:
        func: The function to run with curses
    """
    try:
        # Initialize curses
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        
        # Run the function
        func(stdscr)
    except Exception as e:
        # Make sure to restore terminal state on error
        safe_exit(stdscr)
        raise e
    finally:
        # Clean up curses
        safe_exit(stdscr)


def is_executable(filename: str) -> bool:
    """
    Check if a file is executable
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file is executable, False otherwise
    """
    if not os.path.isfile(filename):
        return False
    
    return os.access(filename, os.X_OK)
