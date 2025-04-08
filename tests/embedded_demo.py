#!/usr/bin/env python3
"""
Demo of embedding AIVim in another application.
"""
import sys
import os

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import embed_editor

def run_demo():
    """Run the embedded AIVim demo"""
    print("Welcome to the AIVim Embedded Demo!")
    print("Opening a sample file for editing...")
    print("Press any key to continue...")
    input()
    
    # Get path to example.py in the same directory
    example_path = os.path.join(os.path.dirname(__file__), 'example.py')
    
    # Start embedded editor with the example file
    embed_editor(example_path)
    
    print("Editing complete!")
    print("Thank you for trying AIVim!")

if __name__ == "__main__":
    run_demo()