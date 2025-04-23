#!/usr/bin/env python3
"""
Test script for automatic tab creation when using Local LLM
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
    with open('test_local_llm.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
'''
Test file for Local LLM automatic tab creation functionality
This file contains some code to be improved by the Local LLM
'''

def bubble_sort(arr):
    '''Inefficient implementation of bubble sort'''
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

def main():
    '''Main function that performs sorting'''
    data = [64, 34, 25, 12, 22, 11, 90]
    print(f"Original array: {data}")
    sorted_data = bubble_sort(data)
    print(f"Sorted array: {sorted_data}")

if __name__ == '__main__':
    main()
""")


def mock_ai_response():
    """Create a mock AI improved code response"""
    return """#!/usr/bin/env python3
'''
Test file for Local LLM automatic tab creation functionality
This file contains improved code with better sorting implementation
'''

def improved_bubble_sort(arr):
    '''Improved implementation of bubble sort with early stopping'''
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        # If no swapping occurred in this pass, array is sorted
        if not swapped:
            break
    return arr

def main():
    '''Main function that performs sorting'''
    data = [64, 34, 25, 12, 22, 11, 90]
    print(f"Original array: {data}")
    sorted_data = improved_bubble_sort(data)
    print(f"Sorted array: {sorted_data}")

if __name__ == '__main__':
    main()
"""


def test_local_llm_tabs(editor):
    """Test the automatic tab creation for Local LLM improvements"""
    # First, make sure we're in normal mode
    editor.mode = "NORMAL"
    editor._update_display()
    curses.napms(500)
    
    # Move cursor to the bubble_sort function
    editor.cursor_y = 7
    editor.cursor_x = 0
    editor._update_display()
    curses.napms(500)
    
    # Display status message for what we're about to do
    editor.set_status_message("About to test automatic tab creation with Local LLM")
    editor._update_display()
    curses.napms(1000)
    
    # Get the current tab count
    initial_tab_count = len(editor.tabs)
    
    # Simulate Local LLM improve action
    start_line = 7   # Line "def bubble_sort(arr):"
    end_line = 12    # Line "    return arr"
    
    # Create a mock pending AI action
    editor.pending_ai_action = {
        "type": "improve",
        "start_line": start_line,
        "end_line": end_line,
        "new_code": mock_ai_response(),
        "metadata": {
            "timestamp": time.time(),
            "model": "local-llm"
        }
    }
    
    # Set the AI model to local to test the auto tab creation
    if hasattr(editor, 'ai_service'):
        # Store original model to restore later
        original_model = editor.ai_service.current_model
        
        # Set to local LLM
        editor.ai_service.current_model = "local"
        
        # Show what we're doing
        editor.set_status_message("Setting AI model to Local LLM and applying improvement")
        editor._update_display()
        curses.napms(1000)
        
        # Apply the improvement (should create a new tab automatically for Local LLM)
        editor.confirm_ai_action(True)
        editor._update_display()
        curses.napms(2000)
        
        # Check if a new tab was created
        new_tab_count = len(editor.tabs)
        if new_tab_count > initial_tab_count:
            editor.set_status_message(f"Success! New tab was created automatically ({initial_tab_count} → {new_tab_count})")
        else:
            editor.set_status_message(f"Test failed! No new tab was created ({initial_tab_count} = {new_tab_count})")
        editor._update_display()
        curses.napms(2000)
        
        # Switch back to the original tab
        editor.switch_to_tab(0)
        editor._update_display()
        curses.napms(1000)
        
        # Restore original model
        editor.ai_service.current_model = original_model
    else:
        editor.set_status_message("AI service not available for testing")
        editor._update_display()
        curses.napms(2000)


def start_editor(stdscr, filename=None):
    """Initialize and start the editor"""
    # Create the test file
    create_test_file()
    
    # Open the test file in the editor
    editor = Editor('test_local_llm.py')
    
    # Initialize editor with the stdscr
    editor._initialize_editor(stdscr)
    
    # Initialize AI service if not already present
    if not hasattr(editor, 'ai_service') or editor.ai_service is None:
        editor.ai_service = AIService()
    
    # Run the test for Local LLM automatic tab creation
    test_local_llm_tabs(editor)
    
    # Display completion message
    editor.set_status_message("Local LLM automatic tab creation test completed. Press any key to exit.")
    editor._update_display()
    
    # Wait for user input
    stdscr.getch()


def main():
    """Main entry point for testing"""
    curses.wrapper(start_editor)


if __name__ == "__main__":
    main()