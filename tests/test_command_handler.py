#!/usr/bin/env python3
"""
Test script for CommandHandler module
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.command_handler import CommandHandler


class TestCommandHandler(unittest.TestCase):
    """Test cases for CommandHandler"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a mock editor
        self.editor = MagicMock()
        
        # Create the command handler with the mock editor
        self.command_handler = CommandHandler(self.editor)
    
    def test_init(self):
        """Test command handler initialization"""
        self.assertEqual(self.command_handler.editor, self.editor)
        self.assertIsNotNone(self.command_handler.commands)
        self.assertGreater(len(self.command_handler.commands), 0)
    
    def test_execute_with_colon(self):
        """Test execute method with leading colon"""
        # Test that the colon is properly stripped
        self.command_handler.execute(":q")
        self.editor.quit.assert_called_once()
    
    def test_execute_unknown_command(self):
        """Test execute method with unknown command"""
        result = self.command_handler.execute("unknown")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_once()
        self.assertIn("Unknown command", self.editor.set_status_message.call_args[0][0])
    
    def test_cmd_write(self):
        """Test write command"""
        # Test successful write
        self.command_handler.execute("w")
        self.editor.save_file.assert_called_once()
        
        # Test with error
        self.editor.save_file.side_effect = Exception("Save error")
        result = self.command_handler.execute("w")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error saving file: Save error")
    
    def test_cmd_write_as(self):
        """Test write as command"""
        # Test successful write as
        self.command_handler.execute("w test.txt")
        self.editor.save_file.assert_called_once_with("test.txt")
        
        # Test with error
        self.editor.save_file.side_effect = Exception("Save error")
        result = self.command_handler.execute("w test.txt")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error saving file: Save error")
    
    def test_cmd_quit(self):
        """Test quit command"""
        self.command_handler.execute("q")
        self.editor.quit.assert_called_once_with()
    
    def test_cmd_write_quit(self):
        """Test write and quit command"""
        # Test successful write and quit
        self.command_handler.execute("wq")
        self.editor.save_file.assert_called_once()
        self.editor.quit.assert_called_once()
        
        # Test with save error
        self.editor.save_file.side_effect = Exception("Save error")
        result = self.command_handler.execute("wq")
        self.assertFalse(result)
        self.editor.quit.assert_called_once()  # Not called again
    
    def test_cmd_force_quit(self):
        """Test force quit command"""
        self.command_handler.execute("q!")
        self.editor.quit.assert_called_once_with(force=True)
    
    def test_cmd_explain(self):
        """Test explain command"""
        # Test successful explain
        self.command_handler.execute("explain 1 5")
        self.editor.ai_explain.assert_called_once_with(0, 4)  # Convert 1-based to 0-based
        
        # Test with error
        self.editor.ai_explain.side_effect = Exception("Explain error")
        result = self.command_handler.execute("explain 1 5")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error executing explain command: Explain error")
    
    def test_cmd_improve(self):
        """Test improve command"""
        # Test successful improve
        self.command_handler.execute("improve 1 5")
        self.editor.ai_improve.assert_called_once_with(0, 4)  # Convert 1-based to 0-based
        
        # Test with error
        self.editor.ai_improve.side_effect = Exception("Improve error")
        result = self.command_handler.execute("improve 1 5")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error executing improve command: Improve error")
    
    def test_cmd_analyze(self):
        """Test analyze command"""
        # Test successful analyze
        self.command_handler.execute("analyze 1 5")
        self.editor.ai_analyze_code.assert_called_once_with(0, 4)  # Convert 1-based to 0-based
        
        # Test with error
        self.editor.ai_analyze_code.side_effect = Exception("Analyze error")
        result = self.command_handler.execute("analyze 1 5")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error executing analyze command: Analyze error")
    
    def test_cmd_generate(self):
        """Test generate command"""
        # Test successful generate
        self.command_handler.execute("generate 1 Test function")
        self.editor.ai_generate.assert_called_once_with(0, "Test function")  # Convert 1-based to 0-based
        
        # Test with error
        self.editor.ai_generate.side_effect = Exception("Generate error")
        result = self.command_handler.execute("generate 1 Test function")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error executing generate command: Generate error")
    
    def test_cmd_ai_query(self):
        """Test AI query command"""
        # Test successful AI query
        self.command_handler.execute("ai How does this code work?")
        self.editor.ai_custom_query.assert_called_once_with("How does this code work?")
        
        # Test with error
        self.editor.ai_custom_query.side_effect = Exception("Query error")
        result = self.command_handler.execute("ai How does this code work?")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error executing AI query: Query error")
    
    def test_cmd_set_option(self):
        """Test set option command"""
        # Test setting AI model
        for model in ["openai", "claude", "local"]:
            self.editor.set_ai_model.reset_mock()
            self.editor.set_status_message.reset_mock()
            
            self.command_handler.execute(f"set {model}")
            self.editor.set_ai_model.assert_called_once_with(model)
            self.editor.set_status_message.assert_called_with(f"AI model set to: {model}")
        
        # Test invalid option
        self.editor.set_status_message.reset_mock()
        result = self.command_handler.execute("set invalid")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Unknown option: invalid")
        
        # Test with error
        self.editor.set_ai_model.side_effect = Exception("Model error")
        result = self.command_handler.execute("set openai")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error setting AI model: Model error")
    
    def test_cmd_confirm_yes(self):
        """Test confirm yes command"""
        # Test successful confirmation
        self.command_handler.execute("y")
        self.editor.confirm_ai_action.assert_called_once_with(True, create_new_tab=True)
        
        # Test with error
        self.editor.confirm_ai_action.side_effect = Exception("Confirmation error")
        result = self.command_handler.execute("y")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error handling confirmation: Confirmation error")
    
    def test_cmd_next_prev_tab(self):
        """Test next and previous tab commands"""
        # Test next tab
        self.command_handler.execute("n")
        self.editor.next_tab.assert_called_once()
        
        # Test previous tab
        self.command_handler.execute("N")
        self.editor.prev_tab.assert_called_once()
        
        # Test with errors
        self.editor.next_tab.side_effect = Exception("Next tab error")
        result = self.command_handler.execute("n")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error switching to next tab: Next tab error")
        
        self.editor.prev_tab.side_effect = Exception("Previous tab error")
        result = self.command_handler.execute("N")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error switching to previous tab: Previous tab error")
    
    def test_cmd_tab_new(self):
        """Test tab new command"""
        # Test successful tab creation
        self.editor.create_tab.return_value = 1
        self.command_handler.execute("tabnew")
        self.editor.create_tab.assert_called_once_with("Untitled")
        self.editor.switch_to_tab.assert_called_once_with(1)
        self.editor.set_status_message.assert_called_with("Created new tab")
        
        # Test with error
        self.editor.create_tab.side_effect = Exception("Tab creation error")
        result = self.command_handler.execute("tabnew")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error creating new tab: Tab creation error")
    
    def test_cmd_tab_new_file(self):
        """Test tab new file command"""
        # Test successful file opening in new tab
        self.editor.create_tab.return_value = 1
        self.command_handler.execute("tabnew test.txt")
        self.editor.create_tab.assert_called_once_with("test.txt", filename="test.txt")
        self.editor.switch_to_tab.assert_called_once_with(1)
        self.editor.load_file.assert_called_once_with("test.txt")
        
        # Test with error
        self.editor.create_tab.side_effect = Exception("Tab creation error")
        result = self.command_handler.execute("tabnew test.txt")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error opening file in new tab: Tab creation error")
    
    def test_cmd_tab_close(self):
        """Test tab close command"""
        # Test successful tab closing
        self.editor.close_current_tab.return_value = True
        self.command_handler.execute("tabclose")
        self.editor.close_current_tab.assert_called_once()
        self.editor.set_status_message.assert_called_with("Closed tab")
        
        # Test when tab can't be closed
        self.editor.close_current_tab.return_value = False
        result = self.command_handler.execute("tabclose")
        self.assertFalse(result)
        
        # Test with error
        self.editor.close_current_tab.side_effect = Exception("Tab close error")
        result = self.command_handler.execute("tabclose")
        self.assertFalse(result)
        self.editor.set_status_message.assert_called_with("Error closing tab: Tab close error")
    
    def test_cmd_help(self):
        """Test help command"""
        self.command_handler.execute("help")
        self.editor.display.show_dialog.assert_called_once()
        # Verify first argument is 'Help'
        self.assertEqual(self.editor.display.show_dialog.call_args[0][0], "Help")
        # Verify second argument is a list of help text
        self.assertIsInstance(self.editor.display.show_dialog.call_args[0][1], list)
        self.assertGreater(len(self.editor.display.show_dialog.call_args[0][1]), 0)


if __name__ == "__main__":
    unittest.main()