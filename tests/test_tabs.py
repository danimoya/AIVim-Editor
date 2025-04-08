#!/usr/bin/env python3
"""
Test script for AIVim tab functionality
"""
import os
import sys
import curses

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor


def create_test_files():
    """Create temporary test files with content"""
    # Create test file 1
    with open('test_file1.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file 1 for tab functionality testing
'''

def hello_world():
    '''Print a greeting'''
    print('Hello from test file 1!')

if __name__ == '__main__':
    hello_world()
""")

    # Create test file 2
    with open('test_file2.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file 2 for tab functionality testing
'''

def goodbye_world():
    '''Print a farewell message'''
    print('Goodbye from test file 2!')

if __name__ == '__main__':
    goodbye_world()
""")


def test_tab_commands(editor):
    """Test the tab commands"""
    # Enter command mode and execute tab commands
    editor.mode = "COMMAND"
    
    # Open test_file1.py in a new tab
    editor.command_buffer = "tabnew test_file1.py"
    editor._process_command()
    
    # Open test_file2.py in a new tab
    editor.command_buffer = "tabnew test_file2.py"
    editor._process_command()
    
    # Switch between tabs a few times
    for _ in range(3):
        # Next tab
        editor.command_buffer = "n"
        editor._process_command()
        
        # Let the user see the tab change
        editor.set_status_message("Switched to next tab")
        editor._update_display()
        curses.napms(1000)  # Pause for 1 second
    
    # Switch back using previous tab command
    for _ in range(3):
        # Previous tab
        editor.command_buffer = "N"
        editor._process_command()
        
        # Let the user see the tab change
        editor.set_status_message("Switched to previous tab")
        editor._update_display()
        curses.napms(1000)  # Pause for 1 second
    
    # Close the current tab
    editor.command_buffer = "tabclose"
    editor._process_command()
    curses.napms(1000)  # Pause for 1 second


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    editor = Editor(filename)
    editor.start(stdscr)
    
    # Test tab functionality
    create_test_files()
    test_tab_commands(editor)


def main():
    """Main entry point for testing"""
    curses.wrapper(start_editor)


if __name__ == "__main__":
    main()