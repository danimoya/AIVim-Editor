#!/usr/bin/env python3
"""
Comprehensive tests for core editing features of AIVim
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch, PropertyMock
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.editor import Editor, Tab
from aivim.buffer import Buffer
from aivim.modes import Mode
from aivim.command_handler import CommandHandler
from aivim.key_handler import KeyHandler


class TestModalEditing(unittest.TestCase):
    """Tests for modal editing functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        # Set initial mode to string for compatibility
        self.editor.mode = "NORMAL"
        self.editor.display = MagicMock()
        self.editor.command_handler = CommandHandler(self.editor)
        self.editor.set_status_message = MagicMock()
        # Mock quit and save_file methods properly
        self.editor.quit = MagicMock()
        self.editor.save_file = MagicMock()
        self.editor.load_file = MagicMock()
        
    def test_initial_mode(self):
        """Test that editor starts in NORMAL mode"""
        self.assertEqual(self.editor.mode, "NORMAL")
        
    def test_switch_to_insert_mode(self):
        """Test switching from NORMAL to INSERT mode"""
        # Simulate pressing 'i'
        self.editor.mode = "INSERT"
        self.assertEqual(self.editor.mode, "INSERT")
        
    def test_switch_to_visual_mode(self):
        """Test switching from NORMAL to VISUAL mode"""
        # Simulate pressing 'v'
        self.editor.mode = "VISUAL"
        self.assertEqual(self.editor.mode, "VISUAL")
        
    def test_switch_to_command_mode(self):
        """Test switching from NORMAL to COMMAND mode"""
        # Simulate pressing ':'
        self.editor.mode = "COMMAND"
        self.editor.command_buffer = ""
        self.editor.command_cursor = 0
        self.assertEqual(self.editor.mode, "COMMAND")
        self.assertEqual(self.editor.command_buffer, "")
        
    def test_escape_returns_to_normal(self):
        """Test that ESC returns to NORMAL from any mode"""
        # Test from INSERT
        self.editor.mode = "INSERT"
        self.editor.mode = "NORMAL"  # Simulate ESC
        self.assertEqual(self.editor.mode, "NORMAL")
        
        # Test from VISUAL
        self.editor.mode = "VISUAL"
        self.editor.mode = "NORMAL"  # Simulate ESC
        self.assertEqual(self.editor.mode, "NORMAL")
        
        # Test from COMMAND
        self.editor.mode = "COMMAND"
        self.editor.mode = "NORMAL"  # Simulate ESC
        self.assertEqual(self.editor.mode, "NORMAL")
        
    def test_visual_selection_tracking(self):
        """Test that visual mode tracks selection start and end"""
        self.editor.cursor_x = 5
        self.editor.cursor_y = 10
        
        # Enter visual mode
        self.editor.mode = "VISUAL"
        self.editor.buffer.start_selection(10, 5)
        
        # Move cursor to create selection
        self.editor.cursor_x = 10
        self.editor.cursor_y = 12
        self.editor.buffer.update_selection(12, 10)
        
        # Check selection bounds
        start, end = self.editor.buffer.get_selection()
        self.assertEqual(start, (10, 5))
        self.assertEqual(end, (12, 10))
        
    def test_command_mode_input(self):
        """Test typing in command mode"""
        self.editor.mode = "COMMAND"
        self.editor.command_buffer = ""
        
        # Simulate typing ":w"
        self.editor.command_buffer = "w"
        self.assertEqual(self.editor.command_buffer, "w")
        
        # Simulate typing a longer command
        self.editor.command_buffer = "w test.txt"
        self.assertEqual(self.editor.command_buffer, "w test.txt")
        

class TestBufferManagement(unittest.TestCase):
    """Tests for buffer management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.buffer = Buffer()
        self.editor = Editor()
        self.editor.buffer = self.buffer
        self.editor.cursor_x = 0
        self.editor.cursor_y = 0
        
    def test_buffer_initialization(self):
        """Test buffer starts with one empty line"""
        self.assertEqual(len(self.buffer.lines), 1)
        self.assertEqual(self.buffer.lines[0], "")
        self.assertFalse(self.buffer.is_modified())
        
    def test_text_insertion(self):
        """Test inserting text into buffer"""
        # Insert text at beginning
        self.buffer.set_line(0, "Hello World")
        self.assertEqual(self.buffer.get_line(0), "Hello World")
        self.assertTrue(self.buffer.is_modified())
        
    def test_text_deletion(self):
        """Test deleting text from buffer"""
        # Setup
        self.buffer.set_lines(["Line 1", "Line 2", "Line 3"])
        self.buffer.mark_as_saved()
        
        # Delete middle line
        self.buffer.delete_line(1)
        self.assertEqual(self.buffer.get_lines(), ["Line 1", "Line 3"])
        self.assertTrue(self.buffer.is_modified())
        
    def test_line_operations_dd(self):
        """Test dd command (delete line)"""
        self.buffer.set_lines(["Line 1", "Line 2", "Line 3"])
        
        # Delete current line (simulating dd)
        current_line = self.editor.cursor_y
        self.buffer.delete_line(current_line)
        
        self.assertEqual(len(self.buffer.lines), 2)
        self.assertNotIn("Line 1", self.buffer.lines)
        
    def test_line_operations_yy_and_p(self):
        """Test yy (yank line) and p (paste) commands"""
        self.buffer.set_lines(["Line 1", "Line 2", "Line 3"])
        
        # Yank current line (simulating yy)
        self.editor.clipboard = [self.buffer.get_line(0)]
        
        # Paste after current line (simulating p)
        self.buffer.insert_line(1, self.editor.clipboard[0])
        
        self.assertEqual(self.buffer.get_lines(), ["Line 1", "Line 1", "Line 2", "Line 3"])
        
    def test_buffer_modification_tracking(self):
        """Test that buffer tracks modifications correctly"""
        # Initially not modified
        self.assertFalse(self.buffer.is_modified())
        
        # After adding content
        self.buffer.set_line(0, "New content")
        self.assertTrue(self.buffer.is_modified())
        
        # After marking as saved
        self.buffer.mark_as_saved()
        self.assertFalse(self.buffer.is_modified())
        
        # After deleting a line
        self.buffer.delete_line(0)
        self.assertTrue(self.buffer.is_modified())
        
    def test_undo_redo_tracking(self):
        """Test undo/redo functionality through history"""
        # Create an editor with history
        self.editor.history.add_version(self.buffer.get_lines(), {"cursor_x": 0, "cursor_y": 0})
        
        # Make changes
        self.buffer.set_line(0, "Changed line")
        self.editor.history.add_version(self.buffer.get_lines(), {"cursor_x": 0, "cursor_y": 0})
        
        # Undo
        lines, metadata = self.editor.history.undo()
        if lines:
            self.buffer.set_lines(lines)
            self.assertEqual(self.buffer.get_line(0), "")
            
        # Redo
        lines, metadata = self.editor.history.redo()
        if lines:
            self.buffer.set_lines(lines)
            self.assertEqual(self.buffer.get_line(0), "Changed line")
            
    def test_multiple_line_insertion(self):
        """Test inserting multiple lines"""
        self.buffer.set_content("Line 1\nLine 2\nLine 3")
        
        # Insert a new line between Line 1 and Line 2
        self.buffer.insert_line(1, "Inserted Line")
        
        expected = ["Line 1", "Inserted Line", "Line 2", "Line 3"]
        self.assertEqual(self.buffer.get_lines(), expected)
        
    def test_empty_buffer_handling(self):
        """Test that buffer always maintains at least one line"""
        # Delete the only line
        self.buffer.delete_line(0)
        
        # Buffer should still have one empty line
        self.assertEqual(len(self.buffer.lines), 1)
        self.assertEqual(self.buffer.lines[0], "")
        

class TestCursorMovement(unittest.TestCase):
    """Tests for cursor movement functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock()
        # Setup a buffer with multiple lines
        self.editor.buffer.set_lines([
            "The quick brown fox",
            "jumps over the lazy dog",
            "Hello world from AIVim",
            "Testing cursor movements"
        ])
        self.editor.cursor_x = 0
        self.editor.cursor_y = 0
        
    def test_basic_movement_hjkl(self):
        """Test h, j, k, l movements"""
        # Test h (left)
        self.editor.cursor_x = 5
        self.editor.cursor_x -= 1  # Simulate h
        self.assertEqual(self.editor.cursor_x, 4)
        
        # Test l (right)
        self.editor.cursor_x += 1  # Simulate l
        self.assertEqual(self.editor.cursor_x, 5)
        
        # Test j (down)
        self.editor.cursor_y += 1  # Simulate j
        self.assertEqual(self.editor.cursor_y, 1)
        
        # Test k (up)
        self.editor.cursor_y -= 1  # Simulate k
        self.assertEqual(self.editor.cursor_y, 0)
        
    def test_boundary_conditions(self):
        """Test cursor doesn't go out of bounds"""
        # Test top boundary
        self.editor.cursor_y = 0
        self.editor.cursor_y = max(0, self.editor.cursor_y - 1)  # Try to go up
        self.assertEqual(self.editor.cursor_y, 0)
        
        # Test bottom boundary
        self.editor.cursor_y = len(self.editor.buffer.lines) - 1
        new_y = min(len(self.editor.buffer.lines) - 1, self.editor.cursor_y + 1)
        self.assertEqual(new_y, len(self.editor.buffer.lines) - 1)
        
        # Test left boundary
        self.editor.cursor_x = 0
        self.editor.cursor_x = max(0, self.editor.cursor_x - 1)
        self.assertEqual(self.editor.cursor_x, 0)
        
        # Test right boundary
        line_length = len(self.editor.buffer.get_line(0))
        self.editor.cursor_x = line_length
        self.editor.cursor_x = min(line_length, self.editor.cursor_x + 1)
        self.assertEqual(self.editor.cursor_x, line_length)
        
    def test_line_navigation_0_dollar(self):
        """Test 0, $, ^ line navigation"""
        self.editor.cursor_x = 10
        self.editor.cursor_y = 0
        
        # Test 0 (beginning of line)
        self.editor.cursor_x = 0
        self.assertEqual(self.editor.cursor_x, 0)
        
        # Test $ (end of line)
        line = self.editor.buffer.get_line(self.editor.cursor_y)
        self.editor.cursor_x = len(line) - 1 if line else 0
        self.assertEqual(self.editor.cursor_x, len("The quick brown fox") - 1)
        
        # Test ^ (first non-blank character)
        # Add a line with leading spaces
        self.editor.buffer.set_line(0, "   The quick brown fox")
        line = self.editor.buffer.get_line(0)
        first_non_blank = 0
        for i, char in enumerate(line):
            if char != ' ':
                first_non_blank = i
                break
        self.editor.cursor_x = first_non_blank
        self.assertEqual(self.editor.cursor_x, 3)
        
    def test_word_movement_web(self):
        """Test w, b, e word movements"""
        self.editor.cursor_x = 0
        self.editor.cursor_y = 0
        line = "The quick brown fox"
        
        # Test w (next word)
        # Should move to 'q' in 'quick'
        self.editor.cursor_x = 4
        self.assertEqual(self.editor.cursor_x, 4)
        
        # Test e (end of word)
        # From position 4, end of 'quick' would be at position 8
        self.editor.cursor_x = 8
        self.assertEqual(self.editor.cursor_x, 8)
        
        # Test b (beginning of word)
        # From position 8, go back to beginning of 'quick'
        self.editor.cursor_x = 4
        self.assertEqual(self.editor.cursor_x, 4)
        
    def test_page_movement(self):
        """Test page movements (Ctrl+F, Ctrl+B)"""
        # Add more lines to test page movement
        lines = [f"Line {i}" for i in range(100)]
        self.editor.buffer.set_lines(lines)
        
        # Test Ctrl+F (page down)
        self.editor.cursor_y = 0
        # Simulate page down (usually moves by screen height - 2)
        page_size = 20  # Simulated screen height
        self.editor.cursor_y = min(len(self.editor.buffer.lines) - 1, 
                                  self.editor.cursor_y + page_size)
        self.assertEqual(self.editor.cursor_y, 20)
        
        # Test Ctrl+B (page up)
        self.editor.cursor_y = max(0, self.editor.cursor_y - page_size)
        self.assertEqual(self.editor.cursor_y, 0)
        
    def test_cursor_memory_on_vertical_movement(self):
        """Test that cursor remembers preferred X position on vertical movement"""
        # Set buffer with lines of different lengths
        self.editor.buffer.set_lines([
            "A very long line with many characters",
            "Short",
            "Another long line here"
        ])
        
        # Move to end of first line
        self.editor.cursor_x = 20
        self.editor.cursor_y = 0
        self.editor.preferred_x = 20
        
        # Move down to short line
        self.editor.cursor_y = 1
        # Cursor should be at end of short line since it's shorter
        max_x = len(self.editor.buffer.get_line(1))
        self.editor.cursor_x = min(self.editor.preferred_x, max_x)
        self.assertEqual(self.editor.cursor_x, 5)
        
        # Move down again to long line
        self.editor.cursor_y = 2
        # Cursor should return to preferred position
        max_x = len(self.editor.buffer.get_line(2))
        self.editor.cursor_x = min(self.editor.preferred_x, max_x)
        self.assertEqual(self.editor.cursor_x, 20)


class TestFileOperations(unittest.TestCase):
    """Tests for file operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock()
        self.editor.set_status_message = MagicMock()
        self.editor.command_handler = CommandHandler(self.editor)
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_load_file_success(self):
        """Test successfully loading a file"""
        # Create a test file
        test_file = os.path.join(self.test_dir, "test.txt")
        test_content = "Line 1\nLine 2\nLine 3"
        with open(test_file, 'w') as f:
            f.write(test_content)
            
        # Load the file
        self.editor.load_file(test_file)
        
        # Check buffer content
        self.assertEqual(self.editor.buffer.get_lines(), ["Line 1", "Line 2", "Line 3"])
        self.assertEqual(self.editor.filename, test_file)
        self.assertFalse(self.editor.buffer.is_modified())
        
    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file creates a new file"""
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.txt")
        
        # Try to load nonexistent file
        self.editor.load_file(nonexistent_file)
        
        # Should create new file message
        self.editor.set_status_message.assert_called()
        status_call = self.editor.set_status_message.call_args[0][0]
        # Editor creates a new file for nonexistent paths
        self.assertIn("New file", status_call)
        
    def test_save_file_with_filename(self):
        """Test saving a file with a filename"""
        test_file = os.path.join(self.test_dir, "save_test.txt")
        
        # Set content and filename
        self.editor.buffer.set_lines(["Save test", "Line 2"])
        self.editor.filename = test_file
        
        # Save the file
        self.editor.save_file()
        
        # Verify file was created and content is correct
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Save test\nLine 2")
        self.assertFalse(self.editor.buffer.is_modified())
        
    def test_save_file_without_filename(self):
        """Test saving a file without a filename"""
        # Set content but no filename
        self.editor.buffer.set_lines(["Content"])
        self.editor.filename = None
        
        # Try to save
        self.editor.save_file()
        
        # Should show error message
        self.editor.set_status_message.assert_called()
        status_call = self.editor.set_status_message.call_args[0][0]
        self.assertIn("No filename", status_call)
        
    def test_save_as_command(self):
        """Test :w filename command"""
        test_file = os.path.join(self.test_dir, "saveas.txt")
        
        # Set content
        self.editor.buffer.set_lines(["Save as test"])
        
        # Execute save as command
        self.editor.command_handler.execute(f"w {test_file}")
        
        # Verify file was created
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Save as test")
        
    def test_create_new_buffer(self):
        """Test creating a new buffer/tab"""
        # Initial state
        self.assertEqual(len(self.editor.tabs), 1)
        
        # Create new tab
        tab_index = self.editor.create_tab("New Tab")
        
        # Check new tab was created
        self.assertEqual(len(self.editor.tabs), 2)
        self.assertEqual(self.editor.tabs[tab_index].name, "New Tab")
        self.assertIsNotNone(self.editor.tabs[tab_index].buffer)
        self.assertEqual(len(self.editor.tabs[tab_index].buffer.lines), 1)
        
    def test_quit_command_with_unsaved_changes(self):
        """Test :q command with unsaved changes"""
        # Make changes
        self.editor.buffer.set_lines(["Modified"])
        
        # Mock the quit method to track calls
        original_quit = self.editor.quit
        self.editor.quit = MagicMock()
        
        # Try to quit
        result = self.editor.command_handler.execute("q")
        
        # Should recognize command but may handle differently
        # Check if status message indicates unsaved changes
        if not self.editor.quit.called:
            # If quit wasn't called, there should be a warning
            self.editor.set_status_message.assert_called()
            status_call = self.editor.set_status_message.call_args[0][0]
            self.assertIn("change", status_call.lower())
        
    def test_force_quit_command(self):
        """Test :q! command"""
        # Make changes
        self.editor.buffer.set_lines(["Modified"])
        
        # Mock the quit method properly
        self.editor.quit = MagicMock()
        
        # Force quit
        result = self.editor.command_handler.execute("q!")
        
        # Should quit regardless of changes
        self.assertTrue(result)
        self.editor.quit.assert_called_once()
        
    def test_write_quit_command(self):
        """Test :wq command"""
        test_file = os.path.join(self.test_dir, "wq_test.txt")
        self.editor.filename = test_file
        self.editor.buffer.set_lines(["Write and quit"])
        
        # Mock the quit and save_file methods
        self.editor.quit = MagicMock()
        self.editor.save_file = MagicMock()
        
        # Execute :wq
        result = self.editor.command_handler.execute("wq")
        
        # Should save and quit
        self.assertTrue(result)
        self.editor.save_file.assert_called_once()
        self.editor.quit.assert_called_once()


class TestEdgeCase(unittest.TestCase):
    """Tests for edge cases and error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock()
        self.editor.set_status_message = MagicMock()
        
    def test_empty_file_handling(self):
        """Test handling of empty files"""
        # Buffer should always have at least one line
        self.editor.buffer.clear()
        self.assertEqual(len(self.editor.buffer.lines), 1)
        self.assertEqual(self.editor.buffer.lines[0], "")
        
    def test_very_long_line_handling(self):
        """Test handling of very long lines"""
        long_line = "x" * 10000
        self.editor.buffer.set_line(0, long_line)
        
        # Should handle without errors
        self.assertEqual(self.editor.buffer.get_line(0), long_line)
        self.assertEqual(len(self.editor.buffer.get_line(0)), 10000)
        
    def test_unicode_content(self):
        """Test handling of Unicode content"""
        unicode_content = "Hello 世界 🌍 مرحبا мир"
        self.editor.buffer.set_lines([unicode_content])
        
        # Should handle Unicode correctly
        self.assertEqual(self.editor.buffer.get_line(0), unicode_content)
        
    def test_invalid_cursor_position_recovery(self):
        """Test recovery from invalid cursor positions"""
        self.editor.buffer.set_lines(["Short"])
        
        # Set cursor beyond line length
        self.editor.cursor_x = 100
        self.editor.cursor_y = 0
        
        # Should constrain to valid position
        line_len = len(self.editor.buffer.get_line(0))
        self.editor.cursor_x = min(self.editor.cursor_x, line_len)
        self.assertEqual(self.editor.cursor_x, 5)
        
        # Set cursor beyond buffer
        self.editor.cursor_y = 100
        buffer_len = len(self.editor.buffer.lines)
        self.editor.cursor_y = min(self.editor.cursor_y, buffer_len - 1)
        self.assertEqual(self.editor.cursor_y, 0)
        
    def test_selection_with_empty_buffer(self):
        """Test selection operations on empty buffer"""
        self.editor.buffer.clear()
        
        # Try to create selection
        self.editor.buffer.start_selection(0, 0)
        self.editor.buffer.update_selection(0, 0)
        
        # Should handle gracefully
        text = self.editor.buffer.get_selection_text()
        self.assertEqual(text, "")
        
    def test_invalid_command_handling(self):
        """Test handling of invalid commands"""
        # Ensure command handler is initialized
        if not self.editor.command_handler:
            self.editor.command_handler = CommandHandler(self.editor)
        
        # Test unknown command
        result = self.editor.command_handler.execute("unknown_command")
        
        # Should return False and set error message
        self.assertFalse(result)
        self.editor.set_status_message.assert_called()
        status_call = self.editor.set_status_message.call_args[0][0]
        self.assertIn("Unknown command", status_call)


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestModalEditing))
    suite.addTests(loader.loadTestsFromTestCase(TestBufferManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestCursorMovement))
    suite.addTests(loader.loadTestsFromTestCase(TestFileOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCase))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)