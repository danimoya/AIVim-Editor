#!/usr/bin/env python3
"""
Demonstration of using AIVim as an embedded editor in another application
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor


def main():
    """
    Simple demonstration of embedding AIVim in another application
    """
    print("AIVim Embedded Demo")
    print("-------------------")
    
    # Example of programmatically preparing a file
    example_file = "demo_file.py"
    with open(example_file, "w") as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Demo file for embedded AIVim
\"\"\"

def hello_world():
    \"\"\"Print a greeting\"\"\"
    print("Hello, world!")

# TODO: Add a function to calculate the sum of a list
""")
    
    print(f"Created example file: {example_file}")
    print("Opening file in embedded AIVim...")
    print("Use :help for commands. :q to quit.")
    
    # Wait for user confirmation
    input("Press Enter to continue...")
    
    # Start embedded editor
    editor = Editor(example_file)
    try:
        # Use the embed_editor function from main.py for proper curses setup
        from main import embed_editor
        embed_editor(example_file)
    except Exception as e:
        print(f"Error running embedded editor: {str(e)}")
    
    print("Exited editor.")
    
    # Demonstrate reading the file after editing
    print("\nFile content after editing:")
    try:
        with open(example_file, "r") as f:
            print(f.read())
    except Exception as e:
        print(f"Error reading file: {str(e)}")


if __name__ == "__main__":
    main()