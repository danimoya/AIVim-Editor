"""
Example script showing how to embed AIVim in other Python applications
"""
import os
import sys

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the embed_editor function from aivim.run_editor
from aivim.run_editor import embed_editor


def demonstrate_embedded_editor():
    """
    Show how to use AIVim as an embedded editor within another Python application
    """
    print("AIVim Embedded Editor Demonstration")
    print("===================================")
    print()
    print("The editor will be launched within this application.")
    print("You can use all AIVim features including AI assistance.")
    print()
    print("Press any key to launch the editor...")
    input()
    
    # Path to our example file
    example_file = os.path.join(os.path.dirname(__file__), 'example.py')
    
    # Launch the embedded editor
    print(f"Opening {example_file}...")
    embed_editor(example_file)
    
    # Editor has closed, continue with the application
    print()
    print("Editor session completed.")
    print("Continuing with the main application...")
    print()
    print("This demonstrates how AIVim can be integrated into other Python applications")
    print("as a text editor component with AI capabilities.")


if __name__ == "__main__":
    demonstrate_embedded_editor()