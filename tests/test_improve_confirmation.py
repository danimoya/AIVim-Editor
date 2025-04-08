#!/usr/bin/env python3
"""
Test script to demonstrate AIVim's code improvement
with confirmation dialog and file backup features.

This example demonstrates:
1. The AI-powered code improvement feature
2. The diff-style presentation of suggestions
3. Confirmation dialog for accepting changes
4. Automatic backup of original files
"""

import os
import sys
import tempfile
import curses
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import AIVim components
from aivim.editor import Editor


def main():
    """Main entry point for the test"""
    
    # Create a temporary file with code for improvement
    fd, temp_filename = tempfile.mkstemp(suffix='.py', prefix='aivim_test_')
    os.close(fd)
    
    # Write sample code with intentional issues
    with open(temp_filename, 'w') as f:
        f.write("""
# Function to calculate fibonacci numbers inefficiently
def fibonacci(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)

# Function with poor variable names and missing docstring
def p(l):
    r = []
    for i in l:
        if i % 2 == 0:
            r.append(i)
    return r

# Test our functions
if __name__ == "__main__":
    print("Fibonacci of 10:", fibonacci(10))
    
    test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print("Filtered list:", p(test_list))
""")
    
    print(f"Created temporary file: {temp_filename}")
    print("Test file contains code with intentional inefficiencies:")
    print("1. Recursive Fibonacci function (exponential time complexity)")
    print("2. Function with poor naming and no documentation")
    print()
    print("Instructions:")
    print("1. Open the editor")
    print("2. Test the :improve command - e.g., ':improve 3 20'")
    print("3. Review the suggestions in the diff dialog (press 'd' to close)")
    print("4. Confirm application of changes in the confirmation dialog (press 'y' to apply)")
    print("5. Notice the backup file creation message in the status bar")
    print("6. Quit with :wq to save changes")
    print()
    print("Beginning editor session...")
    
    try:
        # Initialize the editor with the test file
        editor = Editor(temp_filename)
        
        # Start the editor
        curses.wrapper(editor.start)
        
        # Check if a backup file was created
        directory = os.path.dirname(temp_filename)
        basename = os.path.basename(temp_filename)
        backup_files = [f for f in os.listdir(directory) if f.startswith(f".{basename}.")]
        
        if backup_files:
            print(f"Success! Backup file was created: {backup_files[0]}")
            print(f"Location: {os.path.join(directory, backup_files[0])}")
        else:
            print("No backup file was created. Did you apply the improvements?")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
    
    # Clean up
    try:
        os.unlink(temp_filename)
        print(f"Removed temporary file: {temp_filename}")
    except Exception as e:
        print(f"Error removing temporary file: {str(e)}")
        
    print("Test complete!")


if __name__ == "__main__":
    main()