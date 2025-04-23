#!/usr/bin/env python3
"""
Test the model selector functionality
"""
import unittest
from unittest.mock import MagicMock, patch
import curses
import sys
import os

# Add parent directory to path to import aivim modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor
from aivim.display import Display


class TestModelSelector(unittest.TestCase):
    """Test cases for model selector functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock curses
        self.curses_mock = MagicMock()
        sys.modules['curses'] = self.curses_mock
        
        # Create editor instance with mocked curses
        self.editor = Editor()
        self.editor.display = MagicMock()
        self.editor.ai_service = MagicMock()
        
        # Set up key codes
        self.curses_mock.KEY_UP = 259
        self.curses_mock.KEY_DOWN = 258
        self.curses_mock.KEY_ENTER = 10
        self.ESC = 27
        
    def test_model_selector_display(self):
        """Test that the model selector is displayed correctly"""
        # Call show_model_selector
        self.editor.show_model_selector()
        
        # Verify display.show_model_selector was called with correct arguments
        self.editor.display.show_model_selector.assert_called_once()
        args = self.editor.display.show_model_selector.call_args[0]
        self.assertEqual(len(args), 2)
        self.assertIsNotNone(args[1])  # Callback function
        
    def test_model_selector_key_handling(self):
        """Test that key presses in the model selector are handled correctly"""
        # Mock display.process_model_selector_keypress to return a model on ENTER
        self.editor.display.process_model_selector_keypress.side_effect = [
            None,  # UP key
            None,  # DOWN key
            "claude"  # ENTER key
        ]
        
        # Test UP key
        result = self.editor.handle_model_selector_keypress(self.curses_mock.KEY_UP)
        self.assertFalse(result)
        self.editor.display.process_model_selector_keypress.assert_called_with(self.curses_mock.KEY_UP)
        
        # Test DOWN key
        result = self.editor.handle_model_selector_keypress(self.curses_mock.KEY_DOWN)
        self.assertFalse(result)
        self.editor.display.process_model_selector_keypress.assert_called_with(self.curses_mock.KEY_DOWN)
        
        # Test ENTER key
        result = self.editor.handle_model_selector_keypress(self.curses_mock.KEY_ENTER)
        self.assertTrue(result)
        self.editor.display.process_model_selector_keypress.assert_called_with(self.curses_mock.KEY_ENTER)
        
        # Verify model was set
        self.editor.ai_service.set_model.assert_called_with("claude")
        
    def test_model_selector_esc_key(self):
        """Test that ESC key closes the model selector"""
        # Mock display.process_model_selector_keypress to return None on ESC
        self.editor.display.process_model_selector_keypress.return_value = None
        
        # Test ESC key
        result = self.editor.handle_model_selector_keypress(self.ESC)
        self.assertFalse(result)
        self.editor.display.process_model_selector_keypress.assert_called_with(self.ESC)
        
    def test_command_handler_model_command(self):
        """Test that the :model command opens the model selector"""
        # Mock the editor's command handler
        self.editor.command_handler = MagicMock()
        
        # Create a method that calls the original _cmd_model_selector method
        def call_cmd_model_selector():
            # Import command handler
            from aivim.command_handler import CommandHandler
            
            # Create a command handler with our mocked editor
            handler = CommandHandler(self.editor)
            
            # Call the method
            result = handler._cmd_model_selector()
            
            # Return the result
            return result
            
        # Replace the command handler's _cmd_model_selector with our method
        self.editor.command_handler._cmd_model_selector = call_cmd_model_selector
        
        # Call the model command
        result = self.editor.command_handler._cmd_model_selector()
        
        # Verify show_model_selector was called
        self.editor.display.show_model_selector.assert_called_once()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()