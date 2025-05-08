#!/usr/bin/env python
"""
Test script to verify NLP mode error handling fixes

This script will:
1. Create a test file with NLP comment blocks
2. Launch AIVim in NLP mode
3. Simulate network timeout/errors with a mock
4. Verify errors are shown in popups, not in file content
"""
import os
import sys
import curses
import logging
import tempfile
from unittest.mock import patch

logging.basicConfig(level=logging.DEBUG, filename="aivim.log", 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add current directory to path to import AIVim modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_file():
    """Create a temporary test file with NLP sections"""
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
        f.write(b"""#!/usr/bin/env python
"""
# NLP section that should trigger API call when we hit Shift+Enter or Ctrl+Enter
# This is a multi-line comment block that will be identified by the NLP mode
# as natural language to convert to code.
# 
# Implement a simple function that calculates the factorial of a number
# using a recursive approach.
"""

# Some existing code
def existing_function():
    print("This is an existing function")

#nlp Create a function that calculates the nth Fibonacci number

# Another existing function
def another_function():
    return "Another function"
""")
        return f.name

def simulate_network_timeout(*args, **kwargs):
    """Simulate network timeout by raising an exception"""
    raise TimeoutError("Connection to API timed out after 10 seconds")

def simulate_api_key_error(*args, **kwargs):
    """Simulate API key error by raising an exception"""
    raise ValueError("Invalid API key provided: 'None'")

def start_editor(stdscr, filename, mock_type="timeout"):
    """Initialize and start the editor with mocked AI service"""
    from aivim.editor import Editor
    
    # Create editor instance
    editor = Editor(filename)
    
    # Set up mocking based on the type of error we want to simulate
    if mock_type == "timeout":
        mock_function = simulate_network_timeout
    elif mock_type == "api_key":
        mock_function = simulate_api_key_error
    else:
        raise ValueError(f"Unknown mock type: {mock_type}")
    
    # Patch the AI service's _create_completion method to simulate errors
    with patch('aivim.ai_service.AIService._create_completion', side_effect=mock_function):
        try:
            # Start the editor - will run until user quits
            editor.start(stdscr)
        except Exception as e:
            logging.error(f"Error in editor: {str(e)}")
            raise

def main():
    """Main entry point for testing"""
    # Create test file
    filename = create_test_file()
    logging.info(f"Created test file: {filename}")
    
    # Start editor with the test file
    print(f"Opening test file {filename} in AIVim...")
    print("When the editor opens:")
    print("1. Press 'i' to enter Insert mode first")
    print("2. Then press Escape to get back to Normal mode")
    print("3. Press 'n' to enter NLP mode")
    print("4. Move cursor to a comment block and press Shift+Enter")
    print("5. You should see an error dialog popup (not text in the file)")
    print("6. Press 'q' to quit when done")
    
    try:
        # Run with curses
        curses.wrapper(lambda stdscr: start_editor(stdscr, filename))
    except Exception as e:
        logging.error(f"Error running test: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        # Clean up test file
        try:
            os.unlink(filename)
            logging.info(f"Removed test file: {filename}")
        except:
            pass

if __name__ == "__main__":
    main()