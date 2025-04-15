#!/usr/bin/env python3
"""
Test script for Utils module
"""
import os
import sys
import unittest
import tempfile
import re
from unittest.mock import patch, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.utils import (
    create_diff, 
    split_diff_line, 
    tokenize_command, 
    parse_line_range,
    create_backup_file
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions"""
    
    def test_create_diff_with_changes(self):
        """Test create_diff with text that has differences"""
        old_text = "line1\nline2\nline3"
        new_text = "line1\nmodified\nline3\nnew line"
        
        diff = create_diff(old_text, new_text)
        
        # Check we have the expected number of lines (headers + context + changes)
        self.assertGreater(len(diff), 4)
        
        # Check for expected prefixes
        header_count = 0
        added_count = 0
        removed_count = 0
        context_count = 0
        
        for line in diff:
            prefix, _ = split_diff_line(line)
            if prefix == "HEADER":
                header_count += 1
            elif prefix == "ADDED":
                added_count += 1
            elif prefix == "REMOVED":
                removed_count += 1
            elif prefix == "CONTEXT":
                context_count += 1
        
        # We should have at least one of each type
        self.assertGreater(header_count, 0)
        self.assertGreater(added_count, 0)
        self.assertGreater(removed_count, 0)
        self.assertGreater(context_count, 0)
    
    def test_create_diff_no_changes(self):
        """Test create_diff with identical text"""
        text = "line1\nline2\nline3"
        
        diff = create_diff(text, text)
        
        # Should have one line indicating no differences
        self.assertEqual(len(diff), 1)
        self.assertEqual(diff[0], "No differences found.")
    
    def test_split_diff_line(self):
        """Test split_diff_line function"""
        # Test valid diff line formats
        self.assertEqual(split_diff_line("HEADER|--- old"), ("HEADER", "--- old"))
        self.assertEqual(split_diff_line("ADDED|+new line"), ("ADDED", "+new line"))
        self.assertEqual(split_diff_line("REMOVED|-old line"), ("REMOVED", "-old line"))
        self.assertEqual(split_diff_line("CONTEXT| unchanged"), ("CONTEXT", " unchanged"))
        
        # Test invalid format (should default to CONTEXT)
        self.assertEqual(split_diff_line("invalid line"), ("CONTEXT", "invalid line"))
    
    def test_tokenize_command(self):
        """Test tokenize_command function"""
        # Simple command
        self.assertEqual(tokenize_command("command arg1 arg2"), ["command", "arg1", "arg2"])
        
        # Command with quoted arguments
        self.assertEqual(
            tokenize_command('command "quoted arg" arg2'),
            ["command", "quoted arg", "arg2"]
        )
        
        # Command with single quotes
        self.assertEqual(
            tokenize_command("command 'single quoted' arg2"),
            ["command", "single quoted", "arg2"]
        )
        
        # Command with mixed quotes
        self.assertEqual(
            tokenize_command('command "double quoted" \'single quoted\''),
            ["command", "double quoted", "single quoted"]
        )
        
        # Empty command
        self.assertEqual(tokenize_command(""), [])
    
    def test_parse_line_range(self):
        """Test parse_line_range function"""
        # Valid ranges
        self.assertEqual(parse_line_range("1", "3"), (0, 3))  # 1-3 in 1-based becomes 0-3 in 0-based
        self.assertEqual(parse_line_range("5", "5"), (4, 5))  # Single line
        
        # Invalid ranges
        self.assertEqual(parse_line_range("0", "3"), (-1, -1))  # 0 is invalid in 1-based
        self.assertEqual(parse_line_range("-1", "3"), (-1, -1))  # Negative is invalid
        self.assertEqual(parse_line_range("abc", "3"), (-1, -1))  # Non-numeric
        self.assertEqual(parse_line_range("1", "abc"), (-1, -1))  # Non-numeric
    
    @patch('os.path.exists')
    @patch('shutil.copy2')
    @patch('datetime.datetime')
    def test_create_backup_file(self, mock_datetime, mock_copy2, mock_exists):
        """Test create_backup_file function"""
        # Setup mocks
        mock_exists.return_value = True
        mock_datetime.now.return_value.strftime.return_value = "20240415123456"
        
        # Test creating backup for a file in the current directory
        result = create_backup_file("test.txt")
        self.assertEqual(result, ".test.txt.20240415123456")
        mock_copy2.assert_called_once_with("test.txt", ".test.txt.20240415123456")
        
        # Reset mocks
        mock_copy2.reset_mock()
        
        # Test creating backup for a file in a different directory
        result = create_backup_file("/path/to/test.txt")
        self.assertEqual(result, "/path/to/.test.txt.20240415123456")
        mock_copy2.assert_called_once_with("/path/to/test.txt", "/path/to/.test.txt.20240415123456")
    
    @patch('os.path.exists')
    def test_create_backup_file_nonexistent(self, mock_exists):
        """Test create_backup_file with nonexistent file"""
        mock_exists.return_value = False
        
        result = create_backup_file("nonexistent.txt")
        self.assertEqual(result, "")
    
    @patch('os.path.exists')
    @patch('shutil.copy2')
    def test_create_backup_file_error(self, mock_copy2, mock_exists):
        """Test create_backup_file with copy error"""
        mock_exists.return_value = True
        mock_copy2.side_effect = Exception("Copy failed")
        
        result = create_backup_file("test.txt")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()