#!/usr/bin/env python3
"""
Script to run AIVim editor directly
"""
import sys
import curses
from aivim.editor import Editor


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    editor = Editor(filename)
    editor.start(stdscr)


def main():
    """Main entry point for AIVim"""
    # Get filename from command line argument if provided
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Start editor
    print(f"Starting AIVim with file: {filename}")
    curses.wrapper(start_editor, filename)


if __name__ == "__main__":
    main()