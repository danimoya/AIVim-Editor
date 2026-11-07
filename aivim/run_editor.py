
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
from aivim._version import __version__


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AIVim - AI-enhanced Vim editor"
    )
    parser.add_argument("--version", action="version", version=f"AIVim {__version__}")
    parser.add_argument(
        "filename", nargs="?", default=None,
        help="File to edit (if not specified, opens an empty buffer)"
    )
    parser.add_argument(
        "--model", choices=["openai", "claude", "local", "olares", "compatible"], default=None,
        help="Select AI model provider (default: use environment configuration)"
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to custom configuration file"
    )
    parser.add_argument('--classic', action='store_true', help='Use the original curses editor instead of the terminal workspace')
    parser.add_argument('--project', help='Open a project folder for context and reviewed changes')
    parser.add_argument("--connect", action="store_true", help="Open the HTTPS model connection setup")
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
    from aivim.settings import Settings
    from aivim.ai_service import AIService
    settings=Settings(config_path)
    if model: settings.ai.default_model=model
    editor=Editor(filename,settings=settings,ai_service=AIService(settings=settings))
    try:editor.start(stdscr)
    finally:sys.stdout.write("\x1b[?2004l");sys.stdout.flush()


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

    
    if not args.classic:
        from aivim.tui import TerminalWorkspace
        from aivim.settings import Settings
        settings = Settings(args.config)
        if args.model:
            settings.ai.default_model = args.model
        from pathlib import Path
        filename = args.filename
        if args.project and filename and not Path(filename).is_absolute():
            filename = str(Path(args.project).expanduser() / filename)
        TerminalWorkspace(filename, settings=settings, connect_on_start=args.connect, restore_session=True, project=args.project).run()
        return
    print(f"Starting AIVim with file: {args.filename}")
    if args.model:
        print(f"Using AI model provider: {args.model}")
    
    curses.wrapper(start_editor, args.filename, args.model, args.config)


if __name__ == "__main__":
    main()
