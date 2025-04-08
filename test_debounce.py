#!/usr/bin/env python3
"""
Test script for the debouncing and throttling improvements.
This will create a test file with some content and launch the AIVim editor.
"""
import os
import sys
import curses
import tempfile

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from aivim.editor import Editor


def create_test_file():
    """Create a temporary test file with content"""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp:
        temp.write(b"""#!/usr/bin/env python3
\"\"\"
This is a test file for AIVim editor.
It contains multiple lines of content to test editing, scrolling,
and the new debouncing and throttling mechanisms.
\"\"\"
import sys
import os
import time
from typing import List, Dict, Optional, Tuple

def fibonacci(n: int) -> int:
    \"\"\"Calculate the nth Fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def quick_sort(arr: List[int]) -> List[int]:
    \"\"\"
    Implementation of the quick sort algorithm.
    
    Args:
        arr: The array to sort
        
    Returns:
        The sorted array
    \"\"\"
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)

class DataProcessor:
    \"\"\"A class for processing data.\"\"\"
    
    def __init__(self, data: List[Dict]):
        \"\"\"Initialize with data.\"\"\"
        self.data = data
        self.processed = False
        
    def process(self) -> None:
        \"\"\"Process the data.\"\"\"
        if self.processed:
            return
        
        # Simulate complex processing
        time.sleep(0.1)
        self.processed = True
        
    def get_result(self) -> Dict:
        \"\"\"Get the processing result.\"\"\"
        if not self.processed:
            self.process()
        
        return {"status": "success", "items": len(self.data)}

def main():
    \"\"\"Main function.\"\"\"
    data = [{"id": i, "value": fibonacci(i)} for i in range(10)]
    processor = DataProcessor(data)
    result = processor.get_result()
    print(f"Processed {result['items']} items")
    
    # Test sorting
    arr = [5, 3, 8, 1, 9, 2, 7, 4, 6]
    sorted_arr = quick_sort(arr)
    print(f"Sorted array: {sorted_arr}")

if __name__ == "__main__":
    main()
""")
    return temp.name


def start_editor(stdscr, filename):
    """Initialize and start the editor"""
    editor = Editor(filename)
    editor.start(stdscr)


def main():
    """Main entry point for testing"""
    # Create test file
    filename = create_test_file()
    
    # Start editor with the test file
    try:
        curses.wrapper(lambda stdscr: start_editor(stdscr, filename))
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.unlink(filename)


if __name__ == "__main__":
    main()