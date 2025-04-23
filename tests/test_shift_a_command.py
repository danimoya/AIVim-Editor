#!/usr/bin/env python3
"""
Test script for the Shift+A functionality in insert mode
"""
import os
import sys
import curses

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor


def create_test_file():
    """Create a temporary test file with multi-line content"""
    with open('test_shift_a_file.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file for Shift+A functionality testing
'''

def test_function():
    '''Test function with multiple lines'''
    first_line = 'This is the first line'
    second_line = 'This is the second line'
    
    # Test moving to end of this line with Shift+A
    
    return first_line + second_line

if __name__ == '__main__':
    test_function()
""")


def test_shift_a_command(editor):
    """Test the Shift+A functionality in insert mode"""
    # First, make sure we're in normal mode
    editor.mode = "NORMAL"
    editor._update_display()
    curses.napms(500)
    
    # Move cursor to the line with the comment
    editor.cursor_y = 12
    editor.cursor_x = 0
    editor._update_display()
    curses.napms(500)
    
    # Enter insert mode
    editor.mode = "INSERT"
    editor._update_display()
    curses.napms(500)
    
    # Display status message for what we're about to do
    editor.set_status_message("About to test Shift+A functionality (end of line in insert mode)")
    editor._update_display()
    curses.napms(1000)
    
    # Simulate Shift+A by calling the key handler directly
    # This should move cursor to end of line while still in insert mode
    # We're using the ASCII value of Shift+A (65)
    editor.handle_input(65)  # ASCII for 'A' (Shift+a)
    editor._update_display()
    curses.napms(1000)
    
    # Add text at the end of line to verify it worked
    test_string = " - Added with Shift+A"
    for char in test_string:
        editor._handle_insert_mode(ord(char))
        editor._update_display()
        curses.napms(100)
    
    # Return to normal mode
    editor.handle_input(27)  # ESC key
    editor._update_display()
    curses.napms(500)
    
    # Save the file to see our changes
    editor.command_buffer = "w"
    editor._process_command()
    editor._update_display()
    curses.napms(1000)


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    # Create the test file
    create_test_file()
    
    # Open the test file in the editor
    editor = Editor('test_shift_a_file.py')
    
    # Initialize editor with the stdscr
    editor._initialize_editor(stdscr)
    
    # Run the test for Shift+A in insert mode
    test_shift_a_command(editor)
    
    # Display completion message
    editor.set_status_message("Shift+A test completed. Press any key to exit.")
    editor._update_display()
    
    # Wait for user input
    stdscr.getch()


def main():
    """Main entry point for testing"""
    curses.wrapper(start_editor)


if __name__ == "__main__":
    main()