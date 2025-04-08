#!/usr/bin/env python3
"""
Test script to demonstrate AIVim performance optimizations:
- Display debouncing (limits screen refreshes to 20 fps)
- Input throttling (filters out too rapid keypresses)
- Asynchronous AI operations

This creates a temporary file with 300 lines of sample code to test scrolling
and editing performance with the optimization features.
"""
import os
import sys
import curses
import tempfile
import time
import random
import string

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from aivim.editor import Editor


def create_test_file():
    """Create a large temporary test file with sample content"""
    # Generate a Python-like file with many lines to test scrolling performance
    content = """#!/usr/bin/env python3
\"\"\"
Performance testing file for AIVim editor.
This file contains 300+ lines of mock content to test scrolling and editing performance.
\"\"\"
import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Callable

"""
    
    # Generate 300 lines of pseudo-code
    function_templates = [
        "def function_{0}(x: int, y: int) -> int:\n    \"\"\"Function {0} documentation.\"\"\"\n    return x + y * {0}\n",
        "def process_data_{0}(data: List[Dict[str, Any]]) -> Dict[str, Any]:\n    \"\"\"Process data in function {0}.\"\"\"\n    result = {{}}\n    for item in data:\n        result[item['id']] = item['value'] * {0}\n    return result\n",
        "def calculate_metric_{0}(values: List[float]) -> float:\n    \"\"\"Calculate metric {0} from values.\"\"\"\n    if not values:\n        return 0.0\n    return sum(values) / len(values) * {0}\n",
        "class TestClass{0}:\n    \"\"\"Test class {0} for performance testing.\"\"\"\n    \n    def __init__(self, name: str, value: int = {0}):\n        self.name = name\n        self.value = value\n        self.items = []\n    \n    def add_item(self, item: Any) -> None:\n        \"\"\"Add item to the collection.\"\"\"\n        self.items.append(item)\n        self.value += 1\n    \n    def get_stats(self) -> Dict[str, Any]:\n        \"\"\"Get statistics about this object.\"\"\"\n        return {{\n            'name': self.name,\n            'value': self.value,\n            'items_count': len(self.items)\n        }}\n"
    ]
    
    for i in range(1, 51):
        # Add a variety of function templates with random variations
        template = random.choice(function_templates)
        content += template.format(i)
        
        # Add some empty lines and comments occasionally
        if random.random() < 0.3:
            content += "\n# " + "".join(random.choices(string.ascii_letters, k=random.randint(20, 50))) + "\n\n"
    
    # Add main function at the end
    content += """
def main():
    \"\"\"Main function for performance testing.\"\"\"
    print("Running performance test...")
    
    # Generate test data
    test_data = [{'id': i, 'value': i * 10} for i in range(100)]
    
    # Process with multiple functions
    results = {}
    start_time = time.time()
    
    for i in range(1, 10):
        func_name = f"process_data_{i}"
        if func_name in globals():
            results[func_name] = globals()[func_name](test_data)
    
    elapsed = time.time() - start_time
    print(f"Processed data in {elapsed:.6f} seconds")
    
    # Create test classes
    classes = []
    for i in range(1, 5):
        class_name = f"TestClass{i}"
        if class_name in globals():
            cls = globals()[class_name]
            instance = cls(f"Instance {i}")
            for j in range(20):
                instance.add_item(f"Item {j}")
            classes.append(instance)
    
    # Print statistics
    for instance in classes:
        stats = instance.get_stats()
        print(f"Class {stats['name']}: {stats['items_count']} items, value={stats['value']}")

if __name__ == "__main__":
    main()
"""
    
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp:
        temp.write(content.encode('utf-8'))
    
    return temp.name


def display_instructions(stdscr):
    """Display quick instructions before starting the editor"""
    stdscr.clear()
    stdscr.addstr(0, 0, "AIVim Performance Optimization Test")
    stdscr.addstr(2, 0, "This test demonstrates three performance optimizations:")
    stdscr.addstr(4, 2, "1. Display debouncing - limits screen refresh to 20 fps")
    stdscr.addstr(5, 2, "2. Input throttling - reduces keyboard repeat flicker")
    stdscr.addstr(6, 2, "3. Async operations - background threading for AI features")
    
    stdscr.addstr(8, 0, "How to test:")
    stdscr.addstr(10, 2, "• Hold down arrow keys to rapidly scroll - notice smoother scrolling")
    stdscr.addstr(11, 2, "• Type rapidly in insert mode - reduced screen flashing")
    stdscr.addstr(12, 2, "• Try `:ai Tell me about this file` - editor stays responsive")
    
    stdscr.addstr(14, 0, "Press any key to start testing...")
    stdscr.refresh()
    stdscr.getch()


def start_test(stdscr):
    """Run the performance optimization test"""
    # First display instructions
    display_instructions(stdscr)
    
    # Create test file
    filename = create_test_file()
    
    try:
        # Initialize and start the editor
        editor = Editor(filename)
        editor.start(stdscr)
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.unlink(filename)


def main():
    """Main function for the performance test"""
    curses.wrapper(start_test)


if __name__ == "__main__":
    main()