#!/usr/bin/env python3
"""
Test script for AIVim commands
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.command_handler import CommandHandler
from aivim.editor import Editor
from aivim.modes import Mode


class TestCommandHandler(unittest.TestCase):
    """Test cases for CommandHandler"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = MagicMock()
        self.editor.buffer = MagicMock()
        self.editor.buffer.get_lines.return_value = ["Line 1", "Line 2", "Line 3"]
        self.handler = CommandHandler(self.editor)
    
    def test_write_command(self):
        """Test write command"""
        self.handler.execute("w")
        self.editor.save_file.assert_called_once()
    
    def test_write_as_command(self):
        """Test write as command"""
        self.handler.execute("w test.txt")
        self.editor.save_file.assert_called_once_with("test.txt")
    
    def test_quit_command(self):
        """Test quit command"""
        self.handler.execute("q")
        self.assertTrue(self.editor.quit)
    
    def test_force_quit_command(self):
        """Test force quit command"""
        self.handler.execute("q!")
        self.assertTrue(self.editor.quit)
    
    def test_write_quit_command(self):
        """Test write and quit command"""
        self.handler.execute("wq")
        self.editor.save_file.assert_called_once()
        self.assertTrue(self.editor.quit)
    
    def test_explain_command(self):
        """Test explain command"""
        self.handler.execute("explain 1 2")
        self.editor.ai_explain.assert_called_once_with(0, 1, blocking=False)
    
    def test_improve_command(self):
        """Test improve command"""
        self.handler.execute("improve 1 2")
        self.editor.ai_improve.assert_called_once_with(0, 1, blocking=False)
    
    def test_generate_command(self):
        """Test generate command"""
        self.handler.execute("generate 2 Create a function to calculate GCD")
        self.editor.ai_generate.assert_called_once_with(1, "Create a function to calculate GCD", blocking=False)
    
    def test_ai_query_command(self):
        """Test AI query command"""
        self.handler.execute("ai How can I optimize this code?")
        self.editor.ai_custom_query.assert_called_once_with("How can I optimize this code?", blocking=False)


if __name__ == "__main__":
    unittest.main()