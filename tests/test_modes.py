#!/usr/bin/env python3
"""
Test script for Modes module
"""
import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.modes import Mode


class TestModes(unittest.TestCase):
    """Test cases for Mode enum"""
    
    def test_mode_values(self):
        """Test mode enum values"""
        self.assertEqual(Mode.NORMAL.value, 1)
        self.assertEqual(Mode.INSERT.value, 2)
        self.assertEqual(Mode.VISUAL.value, 3)
        self.assertEqual(Mode.COMMAND.value, 4)
    
    def test_mode_uniqueness(self):
        """Test that all mode values are unique"""
        values = [mode.value for mode in Mode]
        self.assertEqual(len(values), len(set(values)))
    
    def test_mode_names(self):
        """Test mode enum names"""
        self.assertEqual(Mode.NORMAL.name, "NORMAL")
        self.assertEqual(Mode.INSERT.name, "INSERT")
        self.assertEqual(Mode.VISUAL.name, "VISUAL")
        self.assertEqual(Mode.COMMAND.name, "COMMAND")
    
    def test_mode_comparison(self):
        """Test mode comparison"""
        self.assertNotEqual(Mode.NORMAL, Mode.INSERT)
        self.assertNotEqual(Mode.NORMAL, Mode.VISUAL)
        self.assertNotEqual(Mode.NORMAL, Mode.COMMAND)
        
        self.assertEqual(Mode.NORMAL, Mode.NORMAL)
        self.assertEqual(Mode.INSERT, Mode.INSERT)
        self.assertEqual(Mode.VISUAL, Mode.VISUAL)
        self.assertEqual(Mode.COMMAND, Mode.COMMAND)


if __name__ == "__main__":
    unittest.main()