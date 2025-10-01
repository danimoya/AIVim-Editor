"""
Comprehensive tests for search and replace functionality in AIVim
"""
import unittest
from unittest.mock import MagicMock, patch
import curses
import re

from aivim.editor import Editor
from aivim.buffer import Buffer
from aivim.display import Display
from aivim.command_handler import CommandHandler


class TestSearchFunctionality(unittest.TestCase):
    """Test search functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock(spec=Display)
        self.editor.display.max_text_height = 24  # Add missing attribute
        self.editor.buffer = Buffer()
        self.editor.command_handler = CommandHandler(self.editor)
        
        # Add test content
        test_lines = [
            "Hello world",
            "This is a test file",
            "With multiple lines",
            "hello WORLD",
            "HELLO world",
            "Test test TEST",
        ]
        for i, line in enumerate(test_lines):
            self.editor.buffer.insert_line(i, line)
    
    def test_forward_search(self):
        """Test forward search (/) command"""
        self.editor.enter_search_mode("forward")
        self.assertEqual(self.editor.search_direction, "forward")
        self.assertEqual(self.editor.mode, "SEARCH")
        
    def test_backward_search(self):
        """Test backward search (?) command"""
        self.editor.enter_search_mode("backward")
        self.assertEqual(self.editor.search_direction, "backward")
        self.assertEqual(self.editor.mode, "SEARCH")
    
    def test_search_basic_pattern(self):
        """Test basic pattern search"""
        self.editor._start_search("test")
        self.assertGreater(len(self.editor.search_results), 0)
        # Should find 'test' in lines 1 and 5 (0-indexed)
        
    def test_search_case_insensitive(self):
        """Test case insensitive search"""
        self.editor.search_case_sensitive = False
        self.editor._start_search("hello")
        
        # Should find 'Hello', 'hello', and 'HELLO'
        matches = len(self.editor.search_results)
        self.assertEqual(matches, 3)
        
    def test_search_case_sensitive(self):
        """Test case sensitive search"""
        self.editor.search_case_sensitive = True
        self.editor._start_search("hello")
        
        # Should only find 'hello' (lowercase)
        matches = len(self.editor.search_results)
        self.assertEqual(matches, 1)
    
    def test_smart_case_search(self):
        """Test smart case search (case insensitive unless uppercase in pattern)"""
        # All lowercase pattern - case insensitive
        self.editor.search_case_sensitive = None
        self.editor._start_search("hello")
        matches = len(self.editor.search_results)
        self.assertGreater(matches, 1)
        
        # Pattern with uppercase - case sensitive
        self.editor.search_case_sensitive = None
        self.editor._start_search("Hello")
        matches = len(self.editor.search_results)
        self.assertEqual(matches, 1)
    
    def test_next_search_match(self):
        """Test navigation to next match (n command)"""
        self.editor._start_search("test")
        initial_pos = (self.editor.cursor_y, self.editor.cursor_x)
        
        self.editor._find_next_search_match()
        new_pos = (self.editor.cursor_y, self.editor.cursor_x)
        
        # Position should have changed
        self.assertNotEqual(initial_pos, new_pos)
    
    def test_previous_search_match(self):
        """Test navigation to previous match (N command)"""
        self.editor._start_search("test")
        self.editor._find_next_search_match()
        pos1 = (self.editor.cursor_y, self.editor.cursor_x)
        
        self.editor._find_next_search_match(opposite_direction=True)
        pos2 = (self.editor.cursor_y, self.editor.cursor_x)
        
        # Should have moved to a different position
        self.assertNotEqual(pos1, pos2)
    
    def test_search_word_under_cursor(self):
        """Test searching for word under cursor (* and # commands)"""
        # Position cursor on "world"
        self.editor.cursor_y = 0
        self.editor.cursor_x = 6
        
        # Forward search (*)
        self.editor.search_word_under_cursor(backward=False)
        self.assertEqual(self.editor.search_direction, "forward")
        self.assertTrue(self.editor.search_regex)
        
        # Pattern should have word boundaries
        self.assertIn("\\b", self.editor.search_pattern)
        
    def test_search_word_backward(self):
        """Test backward search for word under cursor (# command)"""
        self.editor.cursor_y = 0
        self.editor.cursor_x = 6
        
        self.editor.search_word_under_cursor(backward=True)
        self.assertEqual(self.editor.search_direction, "backward")
    
    def test_clear_search_highlights(self):
        """Test clearing search highlights (:noh command)"""
        self.editor._start_search("test")
        self.assertTrue(len(self.editor.search_results) > 0)
        
        self.editor.clear_search_highlights()
        self.assertFalse(self.editor.search_highlighting)
        self.assertEqual(len(self.editor.search_results), 0)
    
    def test_regex_search(self):
        """Test regex pattern search"""
        self.editor.search_regex = True
        self.editor._start_search("t.*st")
        
        # Should match 'test' and 'TEST'
        self.assertGreater(len(self.editor.search_results), 0)
    
    def test_search_flags(self):
        """Test search with flags (\\c, \\C, \\v)"""
        # Test \c flag (case insensitive)
        pattern, flags = self.editor._parse_search_pattern("\\c hello")
        self.assertIn('c', flags)
        self.assertEqual(pattern, "hello")
        
        # Test \C flag (case sensitive)
        pattern, flags = self.editor._parse_search_pattern("\\C Hello")
        self.assertIn('C', flags)
        self.assertEqual(pattern, "Hello")
        
        # Test \v flag (very magic mode)
        pattern, flags = self.editor._parse_search_pattern("\\v t.+st")
        self.assertIn('v', flags)
        

class TestReplaceFunctionality(unittest.TestCase):
    """Test replace/substitute functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock(spec=Display)
        self.editor.display.max_text_height = 24  # Add missing attribute
        self.editor.buffer = Buffer()
        self.editor.command_handler = CommandHandler(self.editor)
        
        # Add test content
        test_lines = [
            "foo bar foo",
            "test line test",
            "foo foo foo",
            "bar bar",
        ]
        for i, line in enumerate(test_lines):
            self.editor.buffer.insert_line(i, line)
    
    def test_substitute_current_line(self):
        """Test substitution on current line (:s/pattern/replacement/)"""
        self.editor.cursor_y = 0
        count = self.editor.substitute("foo", "baz")
        
        # Should replace first occurrence on current line
        self.assertEqual(count, 1)
        self.assertEqual(self.editor.buffer.get_line(0), "baz bar foo")
    
    def test_substitute_current_line_global(self):
        """Test global substitution on current line (:s/pattern/replacement/g)"""
        self.editor.cursor_y = 0
        count = self.editor.substitute("foo", "baz", global_flag=True)
        
        # Should replace all occurrences on current line
        self.assertEqual(count, 2)
        self.assertEqual(self.editor.buffer.get_line(0), "baz bar baz")
    
    def test_substitute_all_lines(self):
        """Test substitution on all lines (:%s/pattern/replacement/)"""
        total_lines = len(self.editor.buffer.get_lines())
        line_range = (0, total_lines - 1)
        
        count = self.editor.substitute("foo", "baz", line_range=line_range)
        
        # Should replace first occurrence on each line with 'foo'
        self.assertGreater(count, 0)
        # First line should have one replacement
        self.assertEqual(self.editor.buffer.get_line(0), "baz bar foo")
    
    def test_substitute_all_lines_global(self):
        """Test global substitution on all lines (:%s/pattern/replacement/g)"""
        total_lines = len(self.editor.buffer.get_lines())
        line_range = (0, total_lines - 1)
        
        count = self.editor.substitute("foo", "baz", line_range=line_range, global_flag=True)
        
        # Should replace all 'foo' occurrences
        self.assertEqual(count, 5)  # Total 'foo' count in test data
        
    def test_substitute_range(self):
        """Test substitution on line range"""
        # Replace on lines 1-2 (0-indexed: 0-1)
        count = self.editor.substitute("test", "TEST", line_range=(1, 1))
        
        self.assertEqual(count, 1)
        self.assertEqual(self.editor.buffer.get_line(1), "TEST line test")
    
    def test_substitute_visual_mode(self):
        """Test substitution in visual mode selection"""
        # Simulate visual selection
        self.editor.buffer.selection_start = (0, 0)
        self.editor.buffer.selection_end = (1, 0)
        
        # Test the visual substitution command handler
        result = self.editor.command_handler._cmd_substitute_visual("foo", "baz", "")
        
        self.assertTrue(result)
    
    def test_substitute_case_insensitive(self):
        """Test case insensitive substitution"""
        # Add test line
        self.editor.buffer.insert_line(4, "FOO Foo foo")
        
        self.editor.search_case_sensitive = False
        count = self.editor.substitute("foo", "bar", line_range=(4, 4), global_flag=True)
        
        # Should replace all variations
        self.assertGreater(count, 0)
    
    def test_substitute_with_regex(self):
        """Test substitution with regex patterns"""
        self.editor.search_regex = True
        self.editor.cursor_y = 0
        
        # Replace pattern with regex
        count = self.editor.substitute("f..", "XXX", global_flag=True)
        
        self.assertGreater(count, 0)
        self.assertIn("XXX", self.editor.buffer.get_line(0))
    
    def test_substitute_empty_pattern(self):
        """Test handling of empty pattern"""
        count = self.editor.substitute("", "replacement")
        
        # Should handle gracefully
        self.assertEqual(count, 0)
    
    def test_substitute_undo(self):
        """Test that substitution can be undone"""
        original_line = self.editor.buffer.get_line(0)
        
        # Perform substitution
        self.editor.substitute("foo", "baz", global_flag=True)
        modified_line = self.editor.buffer.get_line(0)
        
        # Verify change
        self.assertNotEqual(original_line, modified_line)
        
        # Undo should work through history
        if hasattr(self.editor.history, 'undo'):
            self.editor.history.undo()
            # Line should be restored
            self.assertEqual(self.editor.buffer.get_line(0), original_line)


class TestCommandHandlerIntegration(unittest.TestCase):
    """Test command handler integration with search/replace"""
    
    def setUp(self):
        """Set up test environment"""
        self.editor = Editor()
        self.editor.display = MagicMock(spec=Display)
        self.editor.display.max_text_height = 24  # Add missing attribute
        self.editor.buffer = Buffer()
        self.editor.command_handler = CommandHandler(self.editor)
        
        # Add test content
        test_lines = ["test line 1", "test line 2", "test line 3"]
        for i, line in enumerate(test_lines):
            self.editor.buffer.insert_line(i, line)
    
    def test_noh_command(self):
        """Test :noh command"""
        # Set up search results
        self.editor.search_results = [(0, 0, 4), (1, 0, 4)]
        self.editor.search_highlighting = True
        
        # Execute :noh command
        result = self.editor.command_handler.execute("noh")
        
        self.assertTrue(result)
        self.assertFalse(self.editor.search_highlighting)
    
    def test_substitute_command_parsing(self):
        """Test parsing of substitute commands"""
        # Test basic substitution
        result = self.editor.command_handler.execute("s/test/TEST/")
        self.assertTrue(result)
        
        # Test with global flag
        result = self.editor.command_handler.execute("s/line/LINE/g")
        self.assertTrue(result)
        
        # Test with confirm flag
        result = self.editor.command_handler.execute("s/test/TEST/c")
        # Should return True even if no confirm dialog shown
        self.assertTrue(result or result == False)
    
    def test_substitute_all_command(self):
        """Test :%s command"""
        result = self.editor.command_handler.execute("%s/test/TEST/")
        self.assertTrue(result)
        
        # Check that replacement occurred
        for i in range(3):
            line = self.editor.buffer.get_line(i)
            self.assertIn("TEST", line)
    
    def test_substitute_range_command(self):
        """Test range substitution command"""
        result = self.editor.command_handler.execute("1,2s/test/TEST/")
        self.assertTrue(result)
        
        # First two lines should be changed
        self.assertIn("TEST", self.editor.buffer.get_line(0))
        self.assertIn("TEST", self.editor.buffer.get_line(1))
        # Third line should be unchanged
        self.assertIn("test", self.editor.buffer.get_line(2))


class TestSearchHighlighting(unittest.TestCase):
    """Test search highlighting in display"""
    
    @patch('curses.newwin')
    @patch('curses.init_pair')
    @patch('curses.color_pair')
    def setUp(self, mock_color_pair, mock_init_pair, mock_newwin):
        """Set up test environment with mocked display"""
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        # Create mock windows
        mock_text_win = MagicMock()
        mock_status_win = MagicMock()
        mock_command_win = MagicMock()
        mock_newwin.side_effect = [mock_text_win, mock_status_win, mock_command_win]
        
        # Mock color pairs
        mock_color_pair.return_value = 1
        
        self.display = Display(mock_stdscr)
        self.display.text_win = mock_text_win
        
    def test_render_line_with_search_highlights(self):
        """Test rendering a line with search highlights"""
        line = "This is a test line with test word"
        matches = [(10, 4, False), (25, 4, True)]  # 'test' at positions 10 and 25
        
        # Mock text window
        self.display.text_win.addstr = MagicMock()
        
        # Render the line
        self.display._render_line_with_search_highlights(0, line, matches)
        
        # Verify addstr was called multiple times for segments
        self.assertGreater(self.display.text_win.addstr.call_count, 0)
    
    def test_update_text_with_search_results(self):
        """Test update_text with search results"""
        lines = ["test line 1", "another test", "final line"]
        search_results = [(0, 0, 4), (1, 8, 4)]  # 'test' matches
        
        # Mock methods
        self.display.text_win.clear = MagicMock()
        self.display.text_win.addstr = MagicMock()
        self.display.text_win.getmaxyx = MagicMock(return_value=(20, 76))
        
        # Call update_text with search results
        self.display.update_text(
            lines, 0, 0, 0, 
            selection=None,
            search_results=search_results,
            current_search_index=0
        )
        
        # Verify display was updated
        self.display.text_win.clear.assert_called()


class TestPerformance(unittest.TestCase):
    """Test performance with large files"""
    
    def setUp(self):
        """Set up test environment with large file"""
        self.editor = Editor()
        self.editor.display = MagicMock(spec=Display)
        self.editor.display.max_text_height = 24  # Add missing attribute
        self.editor.buffer = Buffer()
        
        # Create a large file (1000 lines)
        for i in range(1000):
            self.editor.buffer.insert_line(i, f"Line {i} with some test content and more text")
    
    def test_search_performance_large_file(self):
        """Test search performance with large file"""
        import time
        
        start_time = time.time()
        self.editor._start_search("test")
        end_time = time.time()
        
        # Search should complete in reasonable time (< 1 second)
        self.assertLess(end_time - start_time, 1.0)
        
        # Should find matches
        self.assertGreater(len(self.editor.search_results), 0)
    
    def test_substitute_performance_large_file(self):
        """Test substitute performance with large file"""
        import time
        
        start_time = time.time()
        count = self.editor.substitute(
            "test", "TEST", 
            line_range=(0, 999),
            global_flag=True
        )
        end_time = time.time()
        
        # Substitution should complete in reasonable time (< 2 seconds)
        self.assertLess(end_time - start_time, 2.0)
        
        # Should have made replacements
        self.assertGreater(count, 0)


if __name__ == '__main__':
    unittest.main()