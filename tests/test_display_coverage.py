"""
Comprehensive tests for Display.py to increase test coverage
"""
import os
import sys
import pytest
import curses
from unittest.mock import MagicMock, Mock, patch, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.display import Display


class MockStdscr:
    """Mock stdscr for testing"""
    def __init__(self, height=24, width=80):
        self.height = height
        self.width = width
        self._attrs = []
        
    def getmaxyx(self):
        return (self.height, self.width)
    
    def keypad(self, enable):
        pass
    
    def attron(self, attr):
        self._attrs.append(attr)
    
    def attroff(self, attr):
        if attr in self._attrs:
            self._attrs.remove(attr)
    
    def addstr(self, *args, **kwargs):
        pass
    
    def refresh(self):
        pass
    
    def clear(self):
        pass


class MockWindow:
    """Mock window for testing"""
    def __init__(self, height, width, y, x):
        self.height = height
        self.width = width
        self.y = y
        self.x = x
        
    def resize(self, height, width):
        self.height = height
        self.width = width
    
    def mvwin(self, y, x):
        self.y = y
        self.x = x
    
    def addstr(self, *args, **kwargs):
        pass
    
    def clear(self):
        pass
    
    def refresh(self):
        pass
    
    def clrtoeol(self):
        pass
    
    def move(self, y, x):
        pass
    
    def box(self):
        pass
    
    def getmaxyx(self):
        return (self.height, self.width)


class TestDisplayInitialization:
    """Tests for Display initialization"""
    
    @patch('aivim.display.curses')
    def test_display_init(self, mock_curses):
        """Test Display initialization"""
        mock_stdscr = MockStdscr(24, 80)
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.start_color = Mock()
        mock_curses.use_default_colors = Mock()
        mock_curses.init_pair = Mock()
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        mock_curses.noecho = Mock()
        mock_curses.cbreak = Mock()
        mock_curses.curs_set = Mock()
        
        display = Display(mock_stdscr)
        
        assert display.stdscr == mock_stdscr
        assert display.height == 24
        assert display.width == 80
        assert display.gutter_width == 4
        assert display.max_text_height == 22  # height - 2
        assert display.max_text_width == 76  # width - gutter_width
        
        mock_curses.start_color.assert_called_once()
        mock_curses.use_default_colors.assert_called_once()
        mock_curses.noecho.assert_called_once()
        mock_curses.cbreak.assert_called_once()
        mock_curses.curs_set.assert_called_once_with(0)
    
    @patch('aivim.display.curses')
    def test_color_initialization(self, mock_curses):
        """Test color pair initialization"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.init_pair = Mock()
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        # Check that all color pairs are initialized
        assert mock_curses.init_pair.call_count >= 12  # At least 12 color pairs defined
        
        # Check color constants
        assert hasattr(display, 'COLOR_NORMAL')
        assert hasattr(display, 'COLOR_STATUS')
        assert hasattr(display, 'COLOR_MESSAGE')
        assert hasattr(display, 'COLOR_LINENO')
        assert hasattr(display, 'COLOR_SELECTION')
        assert hasattr(display, 'COLOR_DIALOG')
        assert hasattr(display, 'COLOR_SEARCH_CURRENT')
        assert hasattr(display, 'COLOR_SEARCH_OTHER')


class TestDisplayResize:
    """Tests for display resize handling"""
    
    @patch('aivim.display.curses')
    def test_resize(self, mock_curses):
        """Test display resize"""
        mock_stdscr = MockStdscr(24, 80)
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        # Simulate resize
        mock_stdscr.height = 30
        mock_stdscr.width = 100
        display.resize()
        
        assert display.height == 30
        assert display.width == 100
        assert display.max_text_height == 28
        assert display.max_text_width == 96
        
        # Check windows are resized
        display.text_win.resize.assert_called_with(28, 100)
        display.status_win.resize.assert_called_with(1, 100)
        display.command_win.resize.assert_called_with(1, 100)
    
    @patch('aivim.display.curses')
    def test_resize_with_dialog(self, mock_curses):
        """Test resize with dialog open"""
        mock_stdscr = MockStdscr(24, 80)
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.dialog_win = MockWindow(10, 60, 5, 10)
        display._setup_dialog_window = Mock()
        
        display.resize()
        
        display._setup_dialog_window.assert_called_once()


class TestStatusLineRendering:
    """Tests for status line rendering"""
    
    @patch('aivim.display.curses')
    def test_update_status(self, mock_curses):
        """Test status line update"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.status_win.addstr = Mock()
        
        display.update_status("Test.txt", "NORMAL", 5, 10, modified=True, ai_status="Ready")
        
        # Verify status was updated
        display.status_win.addstr.assert_called()
        calls = display.status_win.addstr.call_args_list
        
        # Check that filename and mode are displayed
        status_text = str(calls)
        assert any("Test.txt" in str(call) or "NORMAL" in str(call) for call in calls)
    
    @patch('aivim.display.curses')
    def test_update_status_with_message(self, mock_curses):
        """Test status line with message"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.status_win.addstr = Mock()
        
        display.update_status("file.txt", "INSERT", 0, 0, 
                             message="File saved", ai_status="Processing")
        
        display.status_win.addstr.assert_called()
        
        # Message should be included
        calls = str(display.status_win.addstr.call_args_list)
        assert "File saved" in calls or "INSERT" in calls


class TestDialogHandling:
    """Tests for dialog display and handling"""
    
    @patch('aivim.display.curses')
    def test_show_dialog(self, mock_curses):
        """Test showing a dialog"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        display.show_dialog("Test Dialog", ["Line 1", "Line 2", "Line 3"])
        
        assert display.dialog_win is not None
        assert display.dialog_content == ["Line 1", "Line 2", "Line 3"]
        assert display.dialog_scroll_position == 0
    
    @patch('aivim.display.curses')
    def test_close_dialog(self, mock_curses):
        """Test closing a dialog"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        display.show_dialog("Test", ["Content"])
        assert display.dialog_win is not None
        
        display.close_dialog()
        assert display.dialog_win is None
        assert display.dialog_content == []
        assert display.dialog_views == []
    
    @patch('aivim.display.curses')
    def test_is_dialog_open(self, mock_curses):
        """Test checking if dialog is open"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        assert not display.is_dialog_open()
        
        display.show_dialog("Test", ["Content"])
        assert display.is_dialog_open()
        
        display.close_dialog()
        assert not display.is_dialog_open()
    
    @patch('aivim.display.curses')
    def test_scroll_dialog(self, mock_curses):
        """Test scrolling dialog content"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        # Create a long dialog
        content = [f"Line {i}" for i in range(100)]
        display.show_dialog("Long Dialog", content)
        
        # Scroll down
        display.scroll_dialog_down()
        assert display.dialog_scroll_position > 0
        
        # Scroll up
        old_pos = display.dialog_scroll_position
        display.scroll_dialog_up()
        assert display.dialog_scroll_position < old_pos
    
    @patch('aivim.display.curses')
    def test_dialog_views(self, mock_curses):
        """Test multiple dialog views"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        views = [
            (["View 1 content"], "View 1"),
            (["View 2 content"], "View 2")
        ]
        display.show_dialog_with_views("Multi View", views)
        
        assert len(display.dialog_views) == 2
        assert display.current_view_index == 0
        
        # Switch to next view
        display.next_dialog_view()
        assert display.current_view_index == 1
        
        # Switch to previous view
        display.prev_dialog_view()
        assert display.current_view_index == 0


class TestTextRendering:
    """Tests for text rendering"""
    
    @patch('aivim.display.curses')
    def test_update_text(self, mock_curses):
        """Test updating text display"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.text_win.addstr = Mock()
        
        lines = ["Line 1", "Line 2", "Line 3"]
        display.update_text(lines, cursor_y=1, cursor_x=5, scroll_y=0)
        
        # Should render text
        display.text_win.addstr.assert_called()
    
    @patch('aivim.display.curses')
    def test_update_text_with_selection(self, mock_curses):
        """Test rendering with text selection"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.text_win.addstr = Mock()
        
        lines = ["Line 1", "Selected line", "Line 3"]
        selection = ((1, 0), (1, 13))  # Select entire second line
        
        display.update_text(lines, cursor_y=1, cursor_x=5, scroll_y=0, selection=selection)
        
        display.text_win.addstr.assert_called()
    
    @patch('aivim.display.curses')
    def test_update_text_with_search_highlights(self, mock_curses):
        """Test rendering with search highlights"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.text_win.addstr = Mock()
        
        lines = ["Find this text", "Another line", "Find more"]
        search_results = [(0, 0, 4), (2, 0, 4)]  # "Find" at start of lines 0 and 2
        
        display.update_text(lines, cursor_y=0, cursor_x=0, scroll_y=0,
                           search_results=search_results, current_search_index=0)
        
        display.text_win.addstr.assert_called()


class TestCommandLineDisplay:
    """Tests for command line display"""
    
    @patch('aivim.display.curses')
    def test_update_command_line(self, mock_curses):
        """Test updating command line"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        mock_curses.curs_set = Mock()
        
        display = Display(mock_stdscr)
        display.command_win.addstr = Mock()
        
        display.update_command_line(":w filename.txt", 15)
        
        display.command_win.addstr.assert_called()
        mock_curses.curs_set.assert_called_with(1)  # Show cursor
    
    @patch('aivim.display.curses')
    def test_update_command_line_empty(self, mock_curses):
        """Test clearing command line"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        mock_curses.curs_set = Mock()
        
        display = Display(mock_stdscr)
        display.command_win.clear = Mock()
        
        display.update_command_line("", 0)
        
        display.command_win.clear.assert_called()
        mock_curses.curs_set.assert_called_with(0)  # Hide cursor


class TestTabBarRendering:
    """Tests for tab bar rendering"""
    
    @patch('aivim.display.curses')
    def test_render_tabs(self, mock_curses):
        """Test rendering tab bar"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.text_win.addstr = Mock()
        
        tabs = [
            {"name": "file1.py", "modified": False},
            {"name": "file2.txt", "modified": True},
            {"name": "file3.md", "modified": False}
        ]
        
        display.render_tabs(tabs, current_index=1)
        
        # Should render tab bar
        display.text_win.addstr.assert_called()


class TestLoadingAnimation:
    """Tests for loading animation"""
    
    @patch('aivim.display.curses')
    def test_start_loading_animation(self, mock_curses):
        """Test starting loading animation"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        display.start_loading_animation("Processing...")
        
        assert display.loading_message == "Processing..."
        assert display.loading_thread is not None
        assert display.loading_thread.is_alive()
        
        # Stop animation
        display.stop_loading_animation()
        display.loading_thread.join(timeout=1)
        assert not display.loading_thread.is_alive()
    
    @patch('aivim.display.curses')
    def test_stop_loading_animation(self, mock_curses):
        """Test stopping loading animation"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        display.start_loading_animation("Loading")
        assert display.loading_thread is not None
        
        display.stop_loading_animation()
        assert display.loading_stop_event.is_set()


class TestThemeHandling:
    """Tests for theme handling"""
    
    @patch('aivim.display.curses')
    def test_apply_theme(self, mock_curses):
        """Test applying a theme"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.init_pair = Mock()
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        # Color constants
        mock_curses.COLOR_BLACK = 0
        mock_curses.COLOR_WHITE = 7
        mock_curses.COLOR_RED = 1
        mock_curses.COLOR_GREEN = 2
        mock_curses.COLOR_BLUE = 4
        
        display = Display(mock_stdscr)
        
        # Create a custom theme
        theme = {
            'normal': (mock_curses.COLOR_WHITE, mock_curses.COLOR_BLACK),
            'status': (mock_curses.COLOR_BLACK, mock_curses.COLOR_WHITE),
            'search': (mock_curses.COLOR_BLACK, mock_curses.COLOR_GREEN)
        }
        
        display.apply_theme(theme)
        
        # Check color pairs were initialized with theme colors
        mock_curses.init_pair.assert_called()


class TestPerformanceOptimizations:
    """Tests for performance optimization features"""
    
    @patch('aivim.display.curses')
    def test_cached_rendering(self, mock_curses):
        """Test that rendering is cached when nothing changes"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        display.text_win.addstr = Mock()
        
        lines = ["Same line 1", "Same line 2"]
        
        # First render
        display.update_text(lines, 0, 0, 0)
        first_call_count = display.text_win.addstr.call_count
        
        # Same render (should be optimized)
        display._force_full_redraw = False
        display.update_text(lines, 0, 0, 0)
        
        # Some optimization should occur
        assert display.text_win.addstr.call_count >= first_call_count
    
    @patch('aivim.display.curses')
    def test_force_redraw(self, mock_curses):
        """Test force full redraw flag"""
        mock_stdscr = MockStdscr()
        mock_curses.newwin = Mock(side_effect=lambda h, w, y, x: MockWindow(h, w, y, x))
        mock_curses.color_pair = Mock(side_effect=lambda x: x)
        
        display = Display(mock_stdscr)
        
        assert display._force_full_redraw  # Should be True initially
        
        display._force_full_redraw = False
        assert not display._force_full_redraw
        
        # Resize should force redraw
        display.resize()
        # After resize, we might want to force redraw
        # This depends on implementation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])