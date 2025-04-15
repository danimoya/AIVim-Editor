#!/usr/bin/env python3
"""
Test script for KeyHandler module
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.key_handler import KeyHandler
from aivim.modes import Mode


class TestKeyHandler(unittest.TestCase):
    """Test cases for KeyHandler"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock editor with necessary attributes
        self.editor = MagicMock()
        self.editor.NORMAL_MODE = Mode.NORMAL
        self.editor.INSERT_MODE = Mode.INSERT
        self.editor.VISUAL_MODE = Mode.VISUAL
        self.editor.COMMAND_MODE = Mode.COMMAND
        self.editor.mode = Mode.NORMAL
        
        # Create the key handler
        self.key_handler = KeyHandler(self.editor)
    
    def test_init(self):
        """Test key handler initialization"""
        self.assertEqual(self.key_handler.editor, self.editor)
        self.assertEqual(self.key_handler.KEY_ESC, 27)
        self.assertEqual(self.key_handler.KEY_ENTER, 10)
        self.assertEqual(self.key_handler.KEY_BACKSPACE, 127)
        self.assertEqual(self.key_handler.KEY_TAB, 9)
        
        # All modes should have a handler
        for mode in [Mode.NORMAL, Mode.INSERT, Mode.VISUAL, Mode.COMMAND]:
            self.assertIn(mode, self.key_handler.mode_handlers)
    
    def test_handle_key_delegates_to_mode_handler(self):
        """Test that handle_key delegates to the appropriate mode handler"""
        # Setup mock handlers for each mode
        normal_handler = MagicMock()
        insert_handler = MagicMock()
        visual_handler = MagicMock()
        command_handler = MagicMock()
        
        # Replace the mode_handlers dictionary with our mocks
        self.key_handler.mode_handlers = {
            Mode.NORMAL: normal_handler,
            Mode.INSERT: insert_handler,
            Mode.VISUAL: visual_handler,
            Mode.COMMAND: command_handler
        }
        
        # Mock global keys handler to return False (not handled)
        self.key_handler._handle_global_keys = MagicMock(return_value=False)
        
        # Test normal mode
        self.editor.mode = Mode.NORMAL
        self.key_handler.handle_key(65)  # 'A'
        normal_handler.assert_called_once_with(65)
        
        # Test insert mode
        self.editor.mode = Mode.INSERT
        self.key_handler.handle_key(66)  # 'B'
        insert_handler.assert_called_once_with(66)
        
        # Test visual mode
        self.editor.mode = Mode.VISUAL
        self.key_handler.handle_key(67)  # 'C'
        visual_handler.assert_called_once_with(67)
        
        # Test command mode
        self.editor.mode = Mode.COMMAND
        self.key_handler.handle_key(68)  # 'D'
        command_handler.assert_called_once_with(68)
    
    def test_handle_global_keys(self):
        """Test handling of global keys that work in any mode"""
        with patch('curses.keyname') as mock_keyname:
            # Test Ctrl+Left (undo)
            mock_keyname.return_value = b'^Left'
            result = self.key_handler._handle_global_keys(260)  # KEY_LEFT
            self.assertTrue(result)
            self.editor.undo_ai_modification.assert_called_once()
            
            # Test Ctrl+Right (redo)
            mock_keyname.return_value = b'^Right'
            result = self.key_handler._handle_global_keys(261)  # KEY_RIGHT
            self.assertTrue(result)
            self.editor.redo_ai_modification.assert_called_once()
            
            # Test non-global key
            mock_keyname.return_value = b'a'
            result = self.key_handler._handle_global_keys(97)  # 'a'
            self.assertFalse(result)
    
    def test_handle_normal_mode_mode_changes(self):
        """Test mode changes from normal mode"""
        # Insert mode (i)
        self.key_handler._handle_normal_mode(ord('i'))
        self.assertEqual(self.editor.mode, Mode.INSERT)
        self.editor.set_status_message.assert_called_with("-- INSERT --")
        
        # Visual mode (v)
        self.editor.mode = Mode.NORMAL  # Reset
        self.key_handler._handle_normal_mode(ord('v'))
        self.assertEqual(self.editor.mode, Mode.VISUAL)
        self.assertEqual(self.editor.visual_start_x, self.editor.cursor_x)
        self.assertEqual(self.editor.visual_start_y, self.editor.cursor_y)
        self.editor.set_status_message.assert_called_with("-- VISUAL --")
        
        # Command mode (:)
        self.editor.mode = Mode.NORMAL  # Reset
        self.key_handler._handle_normal_mode(ord(':'))
        self.assertEqual(self.editor.mode, Mode.COMMAND)
        self.assertEqual(self.editor.command_line, "")
        self.assertEqual(self.editor.command_cursor, 0)
    
    def test_handle_normal_mode_movement(self):
        """Test cursor movement in normal mode"""
        # Left
        self.key_handler._handle_normal_mode(ord('h'))
        self.editor.move_cursor.assert_called_with(-1, 0)
        
        # Down
        self.key_handler._handle_normal_mode(ord('j'))
        self.editor.move_cursor.assert_called_with(0, 1)
        
        # Up
        self.key_handler._handle_normal_mode(ord('k'))
        self.editor.move_cursor.assert_called_with(0, -1)
        
        # Right
        self.key_handler._handle_normal_mode(ord('l'))
        self.editor.move_cursor.assert_called_with(1, 0)
        
        # Beginning of line (0)
        self.key_handler._handle_normal_mode(ord('0'))
        self.assertEqual(self.editor.cursor_x, 0)
    
    def test_handle_s_key_in_normal_mode(self):
        """Test 's' key (delete character and enter insert) in normal mode"""
        # Setup mock buffer with a line
        self.editor.buffer.get_line.return_value = "test"
        self.editor.cursor_x = 1
        self.editor.cursor_y = 0
        
        # Test 's' key
        self.key_handler._handle_normal_mode(ord('s'))
        
        # Should delete character at index 1 ('e')
        self.editor.buffer.set_line.assert_called_once_with(0, "tst")
        
        # Should enter insert mode
        self.assertEqual(self.editor.mode, Mode.INSERT)
        self.editor.set_status_message.assert_called_with("-- INSERT --")
    
    def test_handle_insert_mode_exit(self):
        """Test exiting insert mode with Escape"""
        self.editor.mode = Mode.INSERT
        self.key_handler._handle_insert_mode(self.key_handler.KEY_ESC)
        self.assertEqual(self.editor.mode, Mode.NORMAL)
        self.editor.set_status_message.assert_called_with("")
    
    def test_handle_insert_mode_character_insertion(self):
        """Test character insertion in insert mode"""
        # Mock required methods
        self.editor.insert_char = MagicMock()
        
        # Test inserting 'A'
        self.key_handler._handle_insert_mode(ord('A'))
        self.editor.insert_char.assert_called_once_with('A')
        
        # Test inserting tab (should insert 4 spaces)
        self.editor.insert_char.reset_mock()
        self.key_handler._handle_insert_mode(self.key_handler.KEY_TAB)
        self.assertEqual(self.editor.insert_char.call_count, 4)
        self.editor.insert_char.assert_called_with(' ')
    
    def test_handle_insert_mode_enter_key(self):
        """Test Enter key in insert mode (split line)"""
        # Setup mocks
        self.editor.buffer.get_line.return_value = "test line"
        self.editor.cursor_x = 5
        self.editor.cursor_y = 0
        
        # Test Enter key
        self.key_handler._handle_insert_mode(self.key_handler.KEY_ENTER)
        
        # Should split the line at cursor position
        self.editor.buffer.replace_line.assert_called_once_with(0, "test ")
        self.editor.buffer.insert_line.assert_called_once_with(1, "line")
        
        # Cursor should move to start of new line
        self.assertEqual(self.editor.cursor_y, 1)
        self.assertEqual(self.editor.cursor_x, 0)
    
    def test_handle_visual_mode_exit(self):
        """Test exiting visual mode with Escape"""
        self.editor.mode = Mode.VISUAL
        self.key_handler._handle_visual_mode(self.key_handler.KEY_ESC)
        self.assertEqual(self.editor.mode, Mode.NORMAL)
        self.editor.set_status_message.assert_called_with("")
    
    def test_handle_visual_mode_command_entry(self):
        """Test entering command mode from visual with range"""
        # Setup visual selection
        self.editor.visual_start_y = 1
        self.editor.cursor_y = 3
        
        # Test entering command mode with :
        self.key_handler._handle_visual_mode(ord(':'))
        
        # Should enter command mode with range prefilled
        self.assertEqual(self.editor.mode, Mode.COMMAND)
        self.assertEqual(self.editor.command_line, "2,4")  # 1-based for user
        self.assertEqual(self.editor.command_cursor, 3)  # Cursor at end of string
    
    def test_handle_command_mode_exit(self):
        """Test exiting command mode with Escape"""
        self.editor.mode = Mode.COMMAND
        self.editor.command_line = "test"
        
        self.key_handler._handle_command_mode(self.key_handler.KEY_ESC)
        
        self.assertEqual(self.editor.mode, Mode.NORMAL)
        self.assertEqual(self.editor.command_line, "")
    
    def test_handle_command_mode_execute(self):
        """Test executing a command with Enter"""
        self.editor.mode = Mode.COMMAND
        self.editor.command_line = "test"
        
        self.key_handler._handle_command_mode(self.key_handler.KEY_ENTER)
        
        self.editor.execute_command.assert_called_once_with("test")
        self.assertEqual(self.editor.command_line, "")
    
    def test_handle_command_mode_typing(self):
        """Test typing in command mode"""
        self.editor.mode = Mode.COMMAND
        self.editor.command_line = ""
        self.editor.command_cursor = 0
        
        # Type "test"
        for char in "test":
            self.key_handler._handle_command_mode(ord(char))
        
        self.assertEqual(self.editor.command_line, "test")
        self.assertEqual(self.editor.command_cursor, 4)
        
        # Test backspace
        self.key_handler._handle_command_mode(self.key_handler.KEY_BACKSPACE)
        self.assertEqual(self.editor.command_line, "tes")
        self.assertEqual(self.editor.command_cursor, 3)
        
        # Test cursor movement
        self.key_handler._handle_command_mode(260)  # KEY_LEFT
        self.assertEqual(self.editor.command_cursor, 2)
        
        self.key_handler._handle_command_mode(261)  # KEY_RIGHT
        self.assertEqual(self.editor.command_cursor, 3)


if __name__ == "__main__":
    unittest.main()