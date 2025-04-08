#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
Command-line interface and embeddable API
"""
import os
from flask import Flask, render_template, jsonify, request, send_from_directory

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
import argparse
import curses
import logging
import os
import sys
from typing import Optional

from aivim.editor import Editor

from aivim.ai_service import AIService


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




# Web application routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ai-assist', methods=['POST'])
def ai_assist():
    data = request.json
    action = data.get('action')
    code = data.get('code', '')
    context = data.get('context', '')
    
    # Create an instance of the AI service
    from aivim.ai_service import AIService
    ai_service = AIService()
    
    if action == 'explain':
        result = ai_service.get_explanation(code, context)
    elif action == 'improve':
        result = ai_service.get_improvement(code, context)
    elif action == 'generate':
        spec = data.get('specification', '')
        result = ai_service.generate_code(spec, context)
    elif action == 'query':
        query = data.get('query', '')
        result = ai_service.custom_query(query, context)
    else:
        return jsonify({"error": "Invalid action"}), 400
        
    return jsonify({"result": result})

if __name__ == "__main__":
    main()