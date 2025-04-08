#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
Web interface for launching the editor from a browser
"""
import argparse
import curses
import logging
import os
import subprocess
import sys
import threading
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from aivim.editor import Editor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "aivim-development-key")


# Routes for web interface
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/launch', methods=['POST'])
def launch():
    """Launch AIVim with a specified file"""
    filename = request.form.get('filename')
    if not filename:
        flash('Please specify a filename', 'error')
        return redirect(url_for('index'))
    
    # Launch AIVim in a terminal window
    try:
        cmd = [sys.executable, 'run_editor.py', filename]
        subprocess.Popen(cmd)
        flash(f'AIVim launched with file: {filename}', 'success')
    except Exception as e:
        flash(f'Error launching AIVim: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/api/check-openai-key')
def check_openai_key():
    """Check if OpenAI API key is configured"""
    api_key_exists = bool(os.environ.get("OPENAI_API_KEY"))
    return jsonify({
        'api_key_exists': api_key_exists
    })


# Command-line interface functions
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


def cli_main():
    """Main entry point for AIVim from command line"""
    args = parse_arguments()
    check_environment()
    curses.wrapper(start_editor, args.filename)


if __name__ == "__main__":
    # Run the web app when executed directly
    app.run(host="0.0.0.0", port=5000, debug=True)