#!/usr/bin/env python3
"""
Test script for the ':y' command in AIVim
This script will:
1. Create a test file with some sample code
2. Open it in AIVim
3. Use the :improve command to get AI suggestions
4. Use the :y command to create a new tab with the improved code
"""
import os
import sys
import time
import curses

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor


def create_test_file():
    """Create a temporary test file with code to improve"""
    with open('test_improve.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
A simple script with code that could be improved by AI
'''

def calculate_factorial(n):
    '''Calculate the factorial of a number using a recursive approach'''
    # Base case
    if n == 0 or n == 1:
        return 1
    # Recursive case
    else:
        return n * calculate_factorial(n - 1)

def main():
    '''Main function'''
    # Calculate factorial of 5
    result = calculate_factorial(5)
    print("Factorial of 5 is:", result)
    
    # Calculate factorial of 10
    result = calculate_factorial(10)
    print("Factorial of 10 is:", result)
    
    # Calculate factorial of 20 - this might cause issues
    result = calculate_factorial(20)
    print("Factorial of 20 is:", result)

if __name__ == '__main__':
    main()
""")


def test_y_command(editor):
    """Test the :y command functionality"""
    # Demonstrate the process with some delays for viewing
    curses.napms(1000)  # Pause for user to see initial state
    
    # Select a range of lines for improvement (the factorial function)
    start_line = 8  # Line with def calculate_factorial
    end_line = 15   # Line with return statement
    
    # Enter command mode
    editor.mode = "COMMAND"
    
    # Request AI to improve the selected code
    editor.command_buffer = f"improve {start_line} {end_line}"
    editor._process_command()
    
    # Wait for AI to process (in a real test this would need proper synchronization)
    editor.set_status_message("Waiting for AI to process improvement...")
    
    # In a real test, we'd need to properly wait for the AI response
    # For this demo, we'll just pause to simulate waiting
    for i in range(10):
        curses.napms(500)  # Half-second intervals
        editor.set_status_message(f"Waiting for AI... {i+1}/10")
        editor._update_display()
        
        # Break if AI is done (in case it finishes early)
        if not editor.ai_processing:
            break
    
    # Check if we have a pending AI action
    if editor.pending_ai_action:
        editor.set_status_message("AI improvement ready. Press :y to create a new tab with improved code")
        editor._update_display()
        curses.napms(2000)  # Pause to let user see the results
        
        # Use :y command to create a new tab with improved code
        editor.command_buffer = "y"
        editor._process_command()
        
        # See the new tab
        editor.set_status_message("Created new tab with improved code!")
        editor._update_display()
        curses.napms(3000)  # Pause to let user see the new tab
        
        # Switch back to the original tab using :N
        editor.command_buffer = "N"
        editor._process_command()
        editor.set_status_message("Switched back to original tab")
        editor._update_display()
        curses.napms(2000)  # Pause
        
        # Switch to the improved tab again using :n
        editor.command_buffer = "n"
        editor._process_command()
        editor.set_status_message("Switched to improved tab")
        editor._update_display()
        curses.napms(2000)  # Pause
    else:
        editor.set_status_message("No pending AI action. Try again.")
        editor._update_display()
        curses.napms(2000)  # Pause


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    editor = Editor(filename)
    editor.start(stdscr)
    
    # Test the :y command functionality
    test_y_command(editor)


def main():
    """Main entry point for testing"""
    # Create test files
    create_test_file()
    
    # Start the editor with curses
    curses.wrapper(start_editor, 'test_improve.py')


if __name__ == "__main__":
    main()