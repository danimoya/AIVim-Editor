#!/usr/bin/env python3
"""
Test script for AI model info display functionality
"""
import os
import sys
import curses
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor
from aivim.ai_service import AIService


def create_test_file():
    """Create a temporary test file with content to improve"""
    with open('test_model_display.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file for AI model info display functionality
This file contains some code to be improved by the AI
'''

def calculate_factorial(n):
    '''Calculate factorial using inefficient recursive approach'''
    if n <= 1:
        return 1
    else:
        return n * calculate_factorial(n - 1)

def main():
    '''Main function that performs factorial calculations'''
    print("Calculating factorials...")
    for i in range(1, 6):
        print(f"{i}! = {calculate_factorial(i)}")

if __name__ == '__main__':
    main()
""")


def mock_ai_response():
    """Create a mock AI improved code response"""
    return """#!/usr/bin/env python3
'''
Test file for AI model info display functionality
This file contains improved code with better factorial calculation
'''

def calculate_factorial(n):
    '''Calculate factorial using efficient iterative approach'''
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def main():
    '''Main function that performs factorial calculations'''
    print("Calculating factorials...")
    for i in range(1, 6):
        print(f"{i}! = {calculate_factorial(i)}")

if __name__ == '__main__':
    main()
"""


def test_model_info_display(editor):
    """Test the AI model info display functionality"""
    # First, make sure we're in normal mode
    editor.mode = "NORMAL"
    editor._update_display()
    curses.napms(500)
    
    # Move cursor to the calculate_factorial function
    editor.cursor_y = 8
    editor.cursor_x = 0
    editor._update_display()
    curses.napms(500)
    
    # Display status message for what we're about to do
    editor.set_status_message("About to test AI model info display in status bar")
    editor._update_display()
    curses.napms(1000)
    
    # Simulate AI improve action
    start_line = 7  # Line "def calculate_factorial(n):"
    end_line = 10   # Line "        return n * calculate_factorial(n - 1)"
    
    # Create a mock pending AI action
    editor.pending_ai_action = {
        "type": "improve",
        "start_line": start_line,
        "end_line": end_line,
        "new_code": mock_ai_response(),
        "metadata": {
            "timestamp": time.time(),
            "model": "test-model"
        }
    }
    
    # Set a specific AI model and make sure it's visible in the UI
    if hasattr(editor, 'ai_service'):
        editor.ai_service.current_model = "openai"
        
        # First check model info display in normal operations
        model_info = editor.ai_service.get_current_model_info()
        editor.set_status_message(f"Testing model info display: {model_info}")
        editor._update_display()
        curses.napms(2000)
        
        # Now test model info in new tab creation
        editor.confirm_ai_action(True, create_new_tab=True)
        editor._update_display()
        curses.napms(2000)
        
        # Switch back to the original tab
        editor.prev_tab()
        editor._update_display()
        curses.napms(1000)
        
        # Now test model info in current buffer improvement
        # Create another pending action
        editor.pending_ai_action = {
            "type": "improve",
            "start_line": start_line,
            "end_line": end_line,
            "new_code": mock_ai_response(),
            "metadata": {
                "timestamp": time.time(),
                "model": "test-model"
            }
        }
        
        # Apply to current buffer
        editor.confirm_ai_action(True, create_new_tab=False)
        editor._update_display()
        curses.napms(2000)
    else:
        editor.set_status_message("AI service not available for testing")
        editor._update_display()
        curses.napms(2000)
    
    # Save the file
    editor.command_buffer = "w"
    editor._process_command()
    editor._update_display()
    curses.napms(1000)


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    # Create the test file
    create_test_file()
    
    # Open the test file in the editor
    editor = Editor('test_model_display.py')
    
    # Initialize editor with the stdscr
    editor._initialize_editor(stdscr)
    
    # Initialize AI service if not already present
    if not hasattr(editor, 'ai_service') or editor.ai_service is None:
        editor.ai_service = AIService()
    
    # Run the test for model info display
    test_model_info_display(editor)
    
    # Display completion message
    editor.set_status_message("Model info display test completed. Press any key to exit.")
    editor._update_display()
    
    # Wait for user input
    stdscr.getch()


def main():
    """Main entry point for testing"""
    curses.wrapper(start_editor)


if __name__ == "__main__":
    main()