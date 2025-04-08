#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
Command-line interface and embeddable API
"""
import argparse
import curses
import logging
import os
import sys
from typing import Optional

from aivim.editor import Editor


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AIVim - AI-enhanced Vim editor"
    )
    parser.add_argument(
        "filename", nargs="?", default=None,
        help="File to edit (if not specified, opens an empty buffer)"
    )
    return parser.parse_args()


def check_environment():
    """Check if the environment is properly set up"""
    # Check for OPENAI_API_KEY
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable is not set.")
        print("AI features will not work without an OpenAI API key.")
        print("Set the environment variable with: export OPENAI_API_KEY=your_key")
        return False
    return True


def start_editor(stdscr, filename: Optional[str] = None):
    """Initialize and start the editor"""
    # Enable logging
    logging.basicConfig(
        filename="aivim.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    editor = Editor(filename)
    editor.start(stdscr)


def embed_editor(filename: Optional[str] = None):
    """
    API function for embedding the editor in other applications
    
    Args:
        filename: Optional file to edit
    """
    curses.wrapper(start_editor, filename)


def main():
    """Main entry point for AIVim"""
    args = parse_arguments()
    check_environment()
    curses.wrapper(start_editor, args.filename)


if __name__ == "__main__":
    main()