#!/usr/bin/env python3
"""
Test script for multi-line paste functionality in insert mode
"""
import os
import sys
import curses

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor


def create_test_file():
    """Create a temporary test file with content"""
    with open('test_paste_file.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file for multi-line paste functionality testing
'''

def main():
    '''Main function with space for pasting'''
    # Paste multi-line content below:
    
    
    print("End of file")

if __name__ == '__main__':
    main()
""")


def test_multiline_paste(editor):
    """Test the multi-line paste functionality in insert mode"""
    # First, make sure we're in normal mode
    editor.mode = "NORMAL"
    editor._update_display()
    curses.napms(500)
    
    # Move cursor to the line after the comment
    editor.cursor_y = 8
    editor.cursor_x = 4
    editor._update_display()
    curses.napms(500)
    
    # Enter insert mode
    editor.mode = "INSERT"
    editor._update_display()
    curses.napms(500)
    
    # Display status message for what we're about to do
    editor.set_status_message("About to test multi-line paste in insert mode")
    editor._update_display()
    curses.napms(1000)
    
    # Simulate multi-line paste by calling the paste handler directly
    # This simulates what happens when a user pastes content via terminal
    multi_line_content = """def pasted_function():
    '''A function pasted from clipboard'''
    print("Line 1 of pasted content")
    print("Line 2 of pasted content")
    print("Line 3 of pasted content")
    
    return "Paste successful"
"""
    
    # Simulate pasting each character
    for char in multi_line_content:
        # For newlines, we handle specially to test multi-line paste
        if char == '\n':
            editor._handle_insert_mode(10)  # Simulate Enter key (ASCII 10)
        else:
            editor._handle_insert_mode(ord(char))
        editor._update_display()
        curses.napms(10)  # Small delay for visibility
    
    # Return to normal mode
    editor.handle_input(27)  # ESC key
    editor._update_display()
    curses.napms(500)
    
    # Save the file to see our changes
    editor.command_buffer = "w"
    editor._process_command()
    editor._update_display()
    curses.napms(1000)
    
    # Verify the results by showing the full file
    editor.set_status_message("Multi-line paste test completed. Content has been inserted.")
    editor._update_display()
    curses.napms(2000)


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    # Create the test file
    create_test_file()
    
    # Open the test file in the editor
    editor = Editor('test_paste_file.py')
    
    # Initialize editor with the stdscr
    editor._initialize_editor(stdscr)
    
    # Run the test for multi-line paste
    test_multiline_paste(editor)
    
    # Display completion message
    editor.set_status_message("Multi-line paste test completed. Press any key to exit.")
    editor._update_display()
    
    # Wait for user input
    stdscr.getch()


def main():
    """Main entry point for testing"""
    curses.wrapper(start_editor)


if __name__ == "__main__":
    main()