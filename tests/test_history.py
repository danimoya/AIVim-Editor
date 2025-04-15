#!/usr/bin/env python3
"""
Test script for History module
"""
import os
import sys
import unittest
import time
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.history import History


class TestHistory(unittest.TestCase):
    """Test cases for History"""
    
    def setUp(self):
        """Set up test environment"""
        self.history = History(max_history=5)
    
    def test_init(self):
        """Test history initialization"""
        self.assertEqual(self.history.versions, [])
        self.assertEqual(self.history.metadata, [])
        self.assertEqual(self.history.current_index, -1)
        self.assertEqual(self.history.max_history, 5)
    
    def test_add_version(self):
        """Test add_version method"""
        test_lines = ["line1", "line2"]
        test_metadata = {"type": "edit"}
        
        # Add first version
        self.history.add_version(test_lines, test_metadata)
        
        # Check versions and metadata
        self.assertEqual(len(self.history.versions), 1)
        self.assertEqual(len(self.history.metadata), 1)
        self.assertEqual(self.history.current_index, 0)
        
        # Check deep copy was made (no references to original)
        self.assertEqual(self.history.versions[0], test_lines)
        self.assertIsNot(self.history.versions[0], test_lines)
        
        # Check metadata was copied and timestamp added
        self.assertEqual(self.history.metadata[0]["type"], "edit")
        self.assertIn("timestamp", self.history.metadata[0])
        
        # Add another version
        test_lines2 = ["line1", "modified line2"]
        self.history.add_version(test_lines2)
        
        # Check versions
        self.assertEqual(len(self.history.versions), 2)
        self.assertEqual(len(self.history.metadata), 2)
        self.assertEqual(self.history.current_index, 1)
        
        # Check that original lines weren't modified
        self.assertEqual(test_lines, ["line1", "line2"])
    
    def test_undo_redo(self):
        """Test undo and redo functionality"""
        # Add some versions
        self.history.add_version(["v1"])
        self.history.add_version(["v2"])
        self.history.add_version(["v3"])
        
        # Initial state
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        
        # Undo once
        lines, meta = self.history.undo()
        self.assertEqual(lines, ["v2"])
        self.assertEqual(self.history.current_index, 1)
        self.assertTrue(self.history.can_undo())
        self.assertTrue(self.history.can_redo())
        
        # Undo again
        lines, meta = self.history.undo()
        self.assertEqual(lines, ["v1"])
        self.assertEqual(self.history.current_index, 0)
        self.assertFalse(self.history.can_undo())
        self.assertTrue(self.history.can_redo())
        
        # Attempt undo when at beginning (should return None)
        lines, meta = self.history.undo()
        self.assertIsNone(lines)
        self.assertIsNone(meta)
        self.assertEqual(self.history.current_index, 0)
        
        # Redo
        lines, meta = self.history.redo()
        self.assertEqual(lines, ["v2"])
        self.assertEqual(self.history.current_index, 1)
        self.assertTrue(self.history.can_undo())
        self.assertTrue(self.history.can_redo())
        
        # Redo again
        lines, meta = self.history.redo()
        self.assertEqual(lines, ["v3"])
        self.assertEqual(self.history.current_index, 2)
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        
        # Attempt redo when at end (should return None)
        lines, meta = self.history.redo()
        self.assertIsNone(lines)
        self.assertIsNone(meta)
        self.assertEqual(self.history.current_index, 2)
    
    def test_branching_history(self):
        """Test branching history by adding after undo"""
        # Add some versions
        self.history.add_version(["v1"])
        self.history.add_version(["v2"])
        self.history.add_version(["v3"])
        
        # Undo twice
        self.history.undo()
        self.history.undo()
        
        # Now at v1, add a new version
        self.history.add_version(["v4"])
        
        # Check that v2 and v3 were discarded
        self.assertEqual(len(self.history.versions), 2)
        self.assertEqual(self.history.versions, [["v1"], ["v4"]])
        self.assertEqual(self.history.current_index, 1)
    
    def test_prune_history(self):
        """Test that history is pruned when it exceeds max_history"""
        # Add more versions than max_history
        for i in range(10):
            self.history.add_version([f"v{i}"])
        
        # Should only keep the most recent max_history (5) versions
        self.assertEqual(len(self.history.versions), 5)
        self.assertEqual(self.history.versions[0][0], "v5")
        self.assertEqual(self.history.versions[-1][0], "v9")
        self.assertEqual(self.history.current_index, 4)
    
    def test_get_current_version(self):
        """Test get_current_version method"""
        # Empty history
        lines, meta = self.history.get_current_version()
        self.assertIsNone(lines)
        self.assertIsNone(meta)
        
        # Add versions and check
        self.history.add_version(["v1"], {"id": 1})
        self.history.add_version(["v2"], {"id": 2})
        
        lines, meta = self.history.get_current_version()
        self.assertEqual(lines, ["v2"])
        self.assertEqual(meta["id"], 2)
        
        # Undo and check
        self.history.undo()
        lines, meta = self.history.get_current_version()
        self.assertEqual(lines, ["v1"])
        self.assertEqual(meta["id"], 1)
    
    def test_get_version_info(self):
        """Test get_version_info method"""
        # Add versions
        self.history.add_version(["v1"], {"type": "a"})
        self.history.add_version(["v2"], {"type": "b"})
        self.history.add_version(["v3"], {"type": "c"})
        
        # Get version info
        info = self.history.get_version_info()
        
        # Should have 3 versions
        self.assertEqual(len(info), 3)
        
        # Check indexes and current flag
        self.assertEqual(info[0]["index"], 0)
        self.assertEqual(info[1]["index"], 1)
        self.assertEqual(info[2]["index"], 2)
        
        self.assertFalse(info[0]["is_current"])
        self.assertFalse(info[1]["is_current"])
        self.assertTrue(info[2]["is_current"])
        
        # Check metadata was copied
        self.assertEqual(info[0]["type"], "a")
        self.assertEqual(info[1]["type"], "b")
        self.assertEqual(info[2]["type"], "c")
        
        # Change current version and check again
        self.history.undo()
        info = self.history.get_version_info()
        self.assertFalse(info[0]["is_current"])
        self.assertTrue(info[1]["is_current"])
        self.assertFalse(info[2]["is_current"])
    
    def test_clear(self):
        """Test clear method"""
        # Add versions
        self.history.add_version(["v1"])
        self.history.add_version(["v2"])
        
        # Clear
        self.history.clear()
        
        # Check that history was cleared
        self.assertEqual(self.history.versions, [])
        self.assertEqual(self.history.metadata, [])
        self.assertEqual(self.history.current_index, -1)
        
        # Check that can_undo and can_redo are false
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())


if __name__ == "__main__":
    unittest.main()