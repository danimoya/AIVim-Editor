
#!/usr/bin/env python3
"""
Script to run AIVim editor directly
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
    parser.add_argument(
        "--model", choices=["openai", "claude", "local"], default=None,
        help="Select AI model provider (default: use environment configuration)"
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to custom configuration file"
    )
    return parser.parse_args()


def check_environment():
    """Check if the environment is properly set up"""
    # Check for OPENAI_API_KEY
    if not os.environ.get("OPENAI_API_KEY") and not os.path.exists(os.path.expanduser("~/.config/aivim/config.ini")):
        print("Warning: OPENAI_API_KEY environment variable is not set and no config file found.")
        print("AI features will not work without an OpenAI API key.")
        print("Set the environment variable with: export OPENAI_API_KEY=your_key")
        print("Or create a config file at: ~/.config/aivim/config.ini")
        return False
    return True


def start_editor(stdscr, filename: Optional[str] = None, model: Optional[str] = None, config_path: Optional[str] = None):
    """Initialize and start the editor"""
    # Enable logging
    logging.basicConfig(
        filename="aivim.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    editor = Editor(filename)
    
    # Set model if specified
    if model:
        from aivim.ai_service import AIService
        ai_service = editor.ai_service
        if ai_service:
            ai_service.set_model(model)
    
    # Show config status on startup
    if hasattr(editor, 'ai_service') and editor.ai_service is not None:
        config_status = editor.ai_service.config_status
        if config_status.get("loaded", False):
            config_message = f"Config loaded from: {config_status.get('path', 'unknown')}"
        else:
            config_message = config_status.get("message", "Config not loaded")
        
        editor.set_status_message(config_message)
    
    editor.start(stdscr)


def embed_editor(filename: Optional[str] = None, model: Optional[str] = None, config_path: Optional[str] = None):
    """
    API function for embedding the editor in other applications
    
    Args:
        filename: Optional file to edit
        model: Optional AI model provider to use
        config_path: Optional path to custom configuration file
    """
    curses.wrapper(start_editor, filename, model, config_path)


def main():
    """Main entry point for AIVim"""
    args = parse_arguments()
    check_environment()
    
    print(f"Starting AIVim with file: {args.filename}")
    if args.model:
        print(f"Using AI model provider: {args.model}")
    
    curses.wrapper(start_editor, args.filename, args.model, args.config)


if __name__ == "__main__":
    main()
