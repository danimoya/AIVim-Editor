#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
"""
import os
import sys
import curses
import argparse
from typing import Optional
from flask import Flask, render_template, request, jsonify

from aivim.editor import Editor
from aivim.utils import run_with_curses
from aivim.ai_service import AIService

# Create Flask app for web interface
app = Flask(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='AIVim - AI-enhanced Vim clone')
    parser.add_argument('filename', nargs='?', help='File to edit')
    parser.add_argument('--version', action='store_true', help='Show version information')
    return parser.parse_args()


def check_environment():
    """Check if the environment is properly set up"""
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("AI functionality will not work without an API key.")
        print("Please set the OPENAI_API_KEY environment variable.")
        print("Example: export OPENAI_API_KEY=your_api_key_here")
        
        # Ask if user wants to continue anyway
        response = input("Continue without AI functionality? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)


def start_editor(stdscr, filename: Optional[str] = None):
    """Initialize and start the editor"""
    # Create editor instance
    editor = Editor(filename)
    
    # Start the editor
    editor.start(stdscr)


def embed_editor(filename: Optional[str] = None):
    """
    API function for embedding the editor in other applications
    
    Args:
        filename: Optional file to edit
    """
    run_with_curses(lambda stdscr: start_editor(stdscr, filename))


# API routes for web interface
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/explain', methods=['POST'])
def api_explain():
    try:
        data = request.json
        code = data.get('code', '')
        context = data.get('context', '')
        
        service = AIService()
        explanation = service.get_explanation(code, context)
        
        return jsonify({
            'success': True,
            'explanation': explanation
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/improve', methods=['POST'])
def api_improve():
    try:
        data = request.json
        code = data.get('code', '')
        context = data.get('context', '')
        
        service = AIService()
        improved_code = service.get_improvement(code, context)
        
        return jsonify({
            'success': True,
            'improved_code': improved_code
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json
        specification = data.get('specification', '')
        context = data.get('context', '')
        
        service = AIService()
        generated_code = service.generate_code(specification, context)
        
        return jsonify({
            'success': True,
            'generated_code': generated_code
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/query', methods=['POST'])
def api_query():
    try:
        data = request.json
        query = data.get('query', '')
        context = data.get('context', '')
        
        service = AIService()
        response = service.custom_query(query, context)
        
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def main():
    """Main entry point for AIVim"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Show version if requested
    if args.version:
        from aivim import __version__
        print(f"AIVim version {__version__}")
        sys.exit(0)
    
    # Check environment
    check_environment()
    
    # Start the editor
    run_with_curses(lambda stdscr: start_editor(stdscr, args.filename))


if __name__ == "__main__":
    main()
