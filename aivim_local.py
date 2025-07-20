#!/usr/bin/env python3
"""
Wrapper script to run the local fixed version of aivim
Usage: python aivim_local.py [filename]
"""

import sys
import os

# Add current directory to Python path to use local version instead of installed one
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function from the local version
from aivim.run_editor import main

if __name__ == "__main__":
    main()