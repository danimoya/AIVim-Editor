#!/usr/bin/env python3
"""
Test script for Buffer module
"""
import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.buffer import Buffer


class TestBuffer(unittest.TestCase):
    """Test cases for Buffer"""
    
    def setUp(self):
        """Set up test environment"""
        self.buffer = Buffer()
    
    def test_init(self):
        """Test buffer initialization"""
        # Buffer should start with a single empty line
        self.assertEqual(self.buffer.lines, [""])
        self.assertFalse(self.buffer.modified)
        self.assertIsNone(self.buffer.selection_start)
        self.assertIsNone(self.buffer.selection_end)
    
    def test_get_lines(self):
        """Test get_lines method"""
        # Initially empty
        self.assertEqual(self.buffer.get_lines(), [""])
        
        # With content
        self.buffer.lines = ["line1", "line2", "line3"]
        self.assertEqual(self.buffer.get_lines(), ["line1", "line2", "line3"])
    
    def test_get_line(self):
        """Test get_line method"""
        self.buffer.lines = ["line1", "line2", "line3"]
        
        # Valid indices
        self.assertEqual(self.buffer.get_line(0), "line1")
        self.assertEqual(self.buffer.get_line(1), "line2")
        self.assertEqual(self.buffer.get_line(2), "line3")
        
        # Invalid indices
        self.assertEqual(self.buffer.get_line(-1), "")
        self.assertEqual(self.buffer.get_line(3), "")
    
    def test_set_line(self):
        """Test set_line method"""
        self.buffer.lines = ["line1", "line2", "line3"]
        self.buffer.modified = False
        
        # Update a line
        self.buffer.set_line(1, "updated line")
        self.assertEqual(self.buffer.lines, ["line1", "updated line", "line3"])
        self.assertTrue(self.buffer.modified)
        
        # Set to same content (should not mark as modified)
        self.buffer.modified = False
        self.buffer.set_line(1, "updated line")
        self.assertFalse(self.buffer.modified)
        
        # Invalid index (should not change anything)
        self.buffer.set_line(5, "invalid")
        self.assertEqual(self.buffer.lines, ["line1", "updated line", "line3"])
    
    def test_insert_line(self):
        """Test insert_line method"""
        self.buffer.lines = ["line1", "line2"]
        self.buffer.modified = False
        
        # Insert at beginning
        self.buffer.insert_line(0, "new line")
        self.assertEqual(self.buffer.lines, ["new line", "line1", "line2"])
        self.assertTrue(self.buffer.modified)
        
        # Insert in middle
        self.buffer.modified = False
        self.buffer.insert_line(2, "another line")
        self.assertEqual(self.buffer.lines, ["new line", "line1", "another line", "line2"])
        self.assertTrue(self.buffer.modified)
        
        # Insert at end
        self.buffer.modified = False
        self.buffer.insert_line(4, "last line")
        self.assertEqual(self.buffer.lines, ["new line", "line1", "another line", "line2", "last line"])
        self.assertTrue(self.buffer.modified)
        
        # Invalid index
        self.buffer.modified = False
        self.buffer.insert_line(10, "invalid")
        self.assertEqual(self.buffer.lines, ["new line", "line1", "another line", "line2", "last line"])
        self.assertFalse(self.buffer.modified)
    
    def test_delete_line(self):
        """Test delete_line method"""
        self.buffer.lines = ["line1", "line2", "line3"]
        self.buffer.modified = False
        
        # Delete a line
        self.buffer.delete_line(1)
        self.assertEqual(self.buffer.lines, ["line1", "line3"])
        self.assertTrue(self.buffer.modified)
        
        # Delete last line
        self.buffer.modified = False
        self.buffer.delete_line(1)
        self.assertEqual(self.buffer.lines, ["line1"])
        self.assertTrue(self.buffer.modified)
        
        # Delete last remaining line - should ensure at least one empty line remains
        self.buffer.modified = False
        self.buffer.delete_line(0)
        self.assertEqual(self.buffer.lines, [""])
        self.assertTrue(self.buffer.modified)
        
        # Invalid index
        self.buffer.modified = False
        self.buffer.delete_line(5)
        self.assertEqual(self.buffer.lines, [""])
        self.assertFalse(self.buffer.modified)
    
    def test_get_content(self):
        """Test get_content method"""
        # Empty buffer
        self.assertEqual(self.buffer.get_content(), "")
        
        # Single line
        self.buffer.lines = ["single line"]
        self.assertEqual(self.buffer.get_content(), "single line")
        
        # Multiple lines
        self.buffer.lines = ["line1", "line2", "line3"]
        self.assertEqual(self.buffer.get_content(), "line1\nline2\nline3")
    
    def test_set_content(self):
        """Test set_content method"""
        self.buffer.modified = False
        
        # Empty string
        self.buffer.set_content("")
        self.assertEqual(self.buffer.lines, [""])
        self.assertTrue(self.buffer.modified)
        
        # Single line
        self.buffer.modified = False
        self.buffer.set_content("single line")
        self.assertEqual(self.buffer.lines, ["single line"])
        self.assertTrue(self.buffer.modified)
        
        # Multiple lines
        self.buffer.modified = False
        self.buffer.set_content("line1\nline2\nline3")
        self.assertEqual(self.buffer.lines, ["line1", "line2", "line3"])
        self.assertTrue(self.buffer.modified)
    
    def test_set_lines(self):
        """Test set_lines method"""
        self.buffer.modified = False
        
        # Empty list
        self.buffer.set_lines([])
        self.assertEqual(self.buffer.lines, [""])
        self.assertTrue(self.buffer.modified)
        
        # Non-empty list
        self.buffer.modified = False
        self.buffer.set_lines(["line1", "line2", "line3"])
        self.assertEqual(self.buffer.lines, ["line1", "line2", "line3"])
        self.assertTrue(self.buffer.modified)
        
        # Check that we get a copy, not a reference
        lines = ["test1", "test2"]
        self.buffer.set_lines(lines)
        lines.append("modified outside")
        self.assertEqual(self.buffer.lines, ["test1", "test2"])
    
    def test_is_modified_and_mark_as_saved(self):
        """Test is_modified and mark_as_saved methods"""
        # Initial state
        self.assertFalse(self.buffer.is_modified())
        
        # After modification
        self.buffer.set_line(0, "modified")
        self.assertTrue(self.buffer.is_modified())
        
        # After marking as saved
        self.buffer.mark_as_saved()
        self.assertFalse(self.buffer.is_modified())
    
    def test_selection_operations(self):
        """Test selection-related methods"""
        # Start a selection
        self.buffer.start_selection(1, 2)
        self.assertEqual(self.buffer.selection_start, (1, 2))
        self.assertEqual(self.buffer.selection_end, (1, 2))
        
        # Update selection
        self.buffer.update_selection(3, 4)
        self.assertEqual(self.buffer.selection_start, (1, 2))
        self.assertEqual(self.buffer.selection_end, (3, 4))
        
        # Get selection coordinates
        start, end = self.buffer.get_selection()
        self.assertEqual(start, (1, 2))
        self.assertEqual(end, (3, 4))
        
        # End selection
        self.buffer.end_selection()
        self.assertIsNone(self.buffer.selection_start)
        self.assertIsNone(self.buffer.selection_end)
    
    def test_get_selection_text_single_line(self):
        """Test get_selection_text for single line selection"""
        self.buffer.lines = ["0123456789"]
        self.buffer.start_selection(0, 2)
        self.buffer.update_selection(0, 5)
        
        # Selection from 2 to 5 on line 0 (index 2 included, 5 excluded)
        self.assertEqual(self.buffer.get_selection_text(), "234")
        
        # Reversed selection (end before start)
        self.buffer.selection_start = (0, 5)
        self.buffer.selection_end = (0, 2)
        self.assertEqual(self.buffer.get_selection_text(), "234")
    
    def test_get_selection_text_multi_line(self):
        """Test get_selection_text for multi-line selection"""
        self.buffer.lines = ["line 1", "line 2", "line 3"]
        
        # Selection from middle of line 0 to middle of line 2
        self.buffer.start_selection(0, 2)
        self.buffer.update_selection(2, 3)
        self.assertEqual(self.buffer.get_selection_text(), "ne 1\nline 2\nlin")
        
        # Reversed selection (end before start)
        self.buffer.selection_start = (2, 3)
        self.buffer.selection_end = (0, 2)
        self.assertEqual(self.buffer.get_selection_text(), "ne 1\nline 2\nlin")
    
    def test_get_selection_text_no_selection(self):
        """Test get_selection_text with no selection"""
        # No selection
        self.assertEqual(self.buffer.get_selection_text(), "")
        
        # Partial selection (missing end)
        self.buffer.selection_start = (0, 0)
        self.buffer.selection_end = None
        self.assertEqual(self.buffer.get_selection_text(), "")


if __name__ == "__main__":
    unittest.main()