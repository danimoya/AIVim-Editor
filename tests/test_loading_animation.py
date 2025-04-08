"""
Test script for the loading animation feature in AIVim
This demonstrates the spinning animation during AI operations
"""
import os
import sys
import time
import curses

# Add parent directory to path so we can import the aivim package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aivim.editor import Editor


def simulate_ai_processing(stdscr):
    """Simulate AI processing with loading animation"""
    # Initialize the editor
    editor = Editor()
    editor.start(stdscr)
    
    # Create a simple file with example content
    editor.buffer.set_lines([
        "# Example Python script to demonstrate loading animation",
        "",
        "def calculate_fibonacci(n):",
        "    # Base cases",
        "    if n <= 0:",
        "        return 0",
        "    if n == 1:",
        "        return 1",
        "    ",
        "    # Recursive calculation",
        "    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
        "",
        "# Calculate Fibonacci numbers",
        "for i in range(10):",
        "    print(f\"Fibonacci({i}) = {calculate_fibonacci(i)}\")",
        ""
    ])
    
    # Initial display update
    editor._update_display()
    
    # Position cursor for the AI operations
    editor.cursor_y = 5
    editor.cursor_x = 0
    
    # Simulate AI explain operation
    stdscr.clear()
    editor.set_status_message("Press any key to see the loading animation for AI explain...")
    editor._update_display()
    stdscr.getch()  # Wait for user input
    
    # Trigger AI explain with loading animation
    editor.ai_explain(2, 10)  # Explain the fibonacci function
    
    # Since we're not actually running the AI, simulate processing time
    stdscr.clear()
    editor.set_status_message("Simulating AI processing (loading animation should be visible)...")
    editor._update_display()
    
    # Wait to show the animation
    time.sleep(5)
    
    # Manually stop the animation (normally the thread would do this)
    with editor.thread_lock:
        if editor.display:
            editor.display.stop_loading_animation()
        editor.ai_processing = False
        editor.set_status_message("Loading animation demonstration complete")
    
    # Update display one more time
    editor._update_display()
    
    # Wait for user to press a key before exiting
    stdscr.clear()
    editor.set_status_message("Press any key to exit the demo...")
    editor._update_display()
    stdscr.getch()  # Wait for user input


def main():
    """Main entry point"""
    curses.wrapper(simulate_ai_processing)


if __name__ == "__main__":
    main()