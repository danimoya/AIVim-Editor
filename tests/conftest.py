#!/usr/bin/env python3
"""
Pytest configuration and fixtures for AIVim tests
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock curses module before importing anything that uses it
import unittest.mock
mock_curses = unittest.mock.MagicMock()
mock_curses.napms = unittest.mock.Mock()
mock_curses.KEY_RESIZE = -1
mock_curses.set_escdelay = unittest.mock.Mock()
mock_curses.initscr = unittest.mock.Mock()
mock_curses.endwin = unittest.mock.Mock()
mock_curses.wrapper = unittest.mock.Mock()
sys.modules['curses'] = mock_curses

from aivim.editor import Editor
from aivim.buffer import Buffer
from aivim.ai_service import AIService
from aivim.command_handler import CommandHandler
from aivim.history import History


class MockCursesWindow:
    """Mock curses window for testing"""
    def __init__(self, height=24, width=80):
        self.height = height
        self.width = width
        self._content = []
    
    def getmaxyx(self):
        return (self.height, self.width)
    
    def addstr(self, y, x, text, *args, **kwargs):
        pass
    
    def addch(self, y, x, char, *args, **kwargs):
        pass
    
    def clear(self):
        pass
    
    def refresh(self):
        pass
    
    def clrtobot(self):
        pass
    
    def clrtoeol(self):
        pass
    
    def move(self, y, x):
        pass
    
    def resize(self, height, width):
        self.height = height
        self.width = width
    
    def mvwin(self, y, x):
        pass
    
    def keypad(self, enable):
        pass
    
    def getch(self):
        return -1
    
    def nodelay(self, flag):
        pass


class MockStdscr:
    """Mock stdscr for testing"""
    def __init__(self, height=24, width=80):
        self.height = height
        self.width = width
        
    def getmaxyx(self):
        return (self.height, self.width)
    
    def keypad(self, enable):
        pass
    
    def getch(self):
        return -1
    
    def refresh(self):
        pass
    
    def clear(self):
        pass
    
    def nodelay(self, flag):
        pass
    
    def timeout(self, ms):
        pass


@pytest.fixture
def mock_curses():
    """Mock curses module"""
    with patch('aivim.editor.curses') as mock_curses_module, \
         patch('aivim.display.curses') as mock_display_curses:
        
        # Setup color pairs
        mock_curses_module.color_pair = Mock(side_effect=lambda x: x)
        mock_display_curses.color_pair = Mock(side_effect=lambda x: x)
        
        # Setup color functions
        mock_curses_module.start_color = Mock()
        mock_curses_module.use_default_colors = Mock()
        mock_curses_module.init_pair = Mock()
        mock_display_curses.start_color = Mock()
        mock_display_curses.use_default_colors = Mock()
        mock_display_curses.init_pair = Mock()
        
        # Setup curses constants
        for module in [mock_curses_module, mock_display_curses]:
            module.COLOR_WHITE = 7
            module.COLOR_BLACK = 0
            module.COLOR_BLUE = 4
            module.COLOR_CYAN = 6
            module.COLOR_YELLOW = 3
            module.COLOR_GREEN = 2
            module.COLOR_RED = 1
            module.COLOR_MAGENTA = 5
            module.A_BOLD = 1 << 21
            module.A_REVERSE = 1 << 10
            
        # Setup other functions
        mock_curses_module.noecho = Mock()
        mock_curses_module.cbreak = Mock()
        mock_curses_module.curs_set = Mock()
        mock_curses_module.napms = Mock()
        mock_curses_module.newwin = Mock(return_value=MockCursesWindow())
        mock_display_curses.noecho = Mock()
        mock_display_curses.cbreak = Mock()
        mock_display_curses.curs_set = Mock()
        mock_display_curses.napms = Mock()
        mock_display_curses.newwin = Mock(return_value=MockCursesWindow())
        
        yield mock_curses_module


@pytest.fixture
def editor(mock_curses):
    """Create a mocked Editor instance for testing"""
    # Create a mock stdscr
    stdscr = MockStdscr()
    
    # Create the editor with a test file
    test_editor = Editor()
    
    # Mock the display to avoid curses initialization
    from aivim.display import Display
    with patch('aivim.editor.Display') as MockDisplay:
        mock_display = MagicMock()
        mock_display.height = 24
        mock_display.width = 80
        mock_display.max_text_height = 22
        mock_display.max_text_width = 76
        mock_display.gutter_width = 4
        mock_display.is_dialog_open = Mock(return_value=False)
        MockDisplay.return_value = mock_display
        test_editor.display = mock_display
    
    # Mock the command handler
    test_editor.command_handler = MagicMock()
    test_editor.command_handler.execute = Mock()
    
    # Mock the _initialize_editor method to prevent curses operations
    with patch.object(test_editor, '_initialize_editor'):
        pass
    
    # Mock some commonly used methods that interact with curses
    test_editor._update_display = Mock()
    test_editor.set_status_message = Mock()
    test_editor._process_command = Mock()
    test_editor._handle_insert_mode = Mock()
    
    # Initialize AI service if not already present
    if not hasattr(test_editor, 'ai_service') or test_editor.ai_service is None:
        test_editor.ai_service = AIService()
    
    # Set some default values for testing
    test_editor.mode = "NORMAL"
    test_editor.cursor_x = 0
    test_editor.cursor_y = 0
    test_editor.scroll_y = 0
    test_editor.should_quit = False
    test_editor.command_buffer = ""
    test_editor.command_cursor = 0
    test_editor.status_message = ""
    
    # Mock methods that are commonly used in tests
    test_editor.save_file = Mock()
    test_editor.quit = Mock()
    test_editor.ai_explain = Mock()
    test_editor.ai_improve = Mock()
    test_editor.confirm_ai_action = Mock()
    test_editor.switch_to_tab = Mock(return_value=True)
    test_editor.next_tab = Mock()
    test_editor.prev_tab = Mock()
    test_editor.load_file = Mock()
    test_editor.handle_input = Mock()
    
    return test_editor


@pytest.fixture
def buffer():
    """Create a Buffer instance for testing"""
    return Buffer()


@pytest.fixture
def ai_service():
    """Create an AIService instance for testing"""
    return AIService()


@pytest.fixture
def command_handler(editor):
    """Create a CommandHandler instance for testing"""
    return CommandHandler(editor)


@pytest.fixture
def history():
    """Create a History instance for testing"""
    return History()


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file"""
    test_file = tmp_path / "test_file.py"
    test_file.write_text("""#!/usr/bin/env python3
'''
Test file for testing
'''

def test_function():
    '''Test function'''
    print('Hello, World!')
    return True

if __name__ == '__main__':
    test_function()
""")
    return str(test_file)


# Mock the curses.wrapper function that some tests use
def mock_wrapper(func, *args, **kwargs):
    """Mock curses.wrapper for tests that use it"""
    stdscr = MockStdscr()
    return func(stdscr, *args, **kwargs)


# Patch curses at module level for imports
import unittest.mock
with unittest.mock.patch('curses.wrapper', mock_wrapper):
    pass