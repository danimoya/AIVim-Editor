"""
Test the Shift+Enter functionality in NLP mode
"""
import curses
import unittest
from unittest.mock import MagicMock, patch

from aivim.nlp_mode import NLPHandler
from aivim.editor import Editor
from aivim.buffer import Buffer
from aivim.display import Display


class TestNLPShiftEnter(unittest.TestCase):
    """Test the Shift+Enter functionality in NLP mode"""
    
    def setUp(self):
        """Set up the test environment"""
        # Mock the editor
        self.editor = MagicMock(spec=Editor)
        
        # Create a real buffer 
        self.buffer = Buffer()
        self.buffer.set_lines([
            "# This is a test file",
            "# with some NLP sections",
            "#nlp",
            "This is natural language that should be translated to code",
            "It should do something amazing",
            "#nlp",
            "",
            "def existing_function():",
            "    return 'hello world'"
        ])
        
        # Assign the buffer to the editor
        self.editor.buffer = self.buffer
        
        # Mock the display
        self.editor.display = MagicMock(spec=Display)
        
        # Create thread lock
        self.editor.thread_lock = MagicMock()
        
        # Create a real NLP handler with our mocked editor
        self.nlp_handler = NLPHandler(self.editor)
        
    def test_scan_nlp_sections(self):
        """Test scanning buffer for NLP sections"""
        # Scan the buffer
        self.nlp_handler.scan_buffer_for_nlp_sections()
        
        # Verify that the NLP sections were detected
        self.assertGreaterEqual(len(self.nlp_handler.nlp_sections), 1)
        
        # Check if our section is properly identified
        # Some implementations might detect 1 or 2 sections here depending on the algorithm
        found_section = False
        for section in self.nlp_handler.nlp_sections:
            start, end = section[0], section[1]
            if start <= 3 and end >= 5:  # This covers the nlp section (lines 3-5)
                found_section = True
                break
                
        self.assertTrue(found_section, "Failed to identify the NLP section")
    
    @patch('threading.Thread')
    def test_handle_shift_enter(self, mock_thread):
        """Test handling Shift+Enter in NLP mode"""
        # Mock the Thread to avoid actually starting a thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Call the function we're testing
        self.nlp_handler.handle_shift_enter()
        
        # Verify that scan_buffer_for_nlp_sections was called
        self.editor.set_status_message.assert_called_with("Processing NLP sections (current file only)...")
        
        # Verify that the thread was started
        mock_thread_instance.start.assert_called_once()
    
    def test_handle_key_shift_enter(self):
        """Test that the key handler correctly identifies Shift+Enter"""
        # Mock the keyname function to return the sequence for Shift+Enter
        with patch('curses.keyname') as mock_keyname:
            # Simulate the key code for Shift+Enter
            mock_keyname.return_value = b'key_enter'
            
            # Call the key handler with the key code for Enter
            result = self.nlp_handler.handle_key(10)  # 10 is the ASCII code for Enter/Return
            
            # Verify that the function recognized it as Shift+Enter and returned True
            self.assertTrue(result, "Shift+Enter was not recognized or handled")


if __name__ == '__main__':
    unittest.main()