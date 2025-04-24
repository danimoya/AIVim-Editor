"""
Test the :nlptranslate command with improved error handling
"""
import unittest
from unittest.mock import MagicMock, patch

from aivim.command_handler import CommandHandler
from aivim.editor import Editor
from aivim.nlp_mode import NLPHandler
from aivim.buffer import Buffer


class TestNLPTranslateCommand(unittest.TestCase):
    """Test the :nlptranslate command functionality"""
    
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
        
        # Create a real CommandHandler with our mocked editor
        self.command_handler = CommandHandler(self.editor)
        
    def test_nlptranslate_with_sections(self):
        """Test nlptranslate command with NLP sections present"""
        # Mock the NLPHandler
        mock_nlp_handler = MagicMock(spec=NLPHandler)
        mock_nlp_handler.nlp_sections = [(3, 5)]  # Mock some NLP sections
        self.editor.nlp_handler = mock_nlp_handler
        
        # Mock display with loading animation methods
        mock_display = MagicMock()
        mock_display.start_loading_animation = MagicMock()
        mock_display.stop_loading_animation = MagicMock()
        self.editor.display = mock_display
        
        # Execute the command
        result = self.command_handler._cmd_translate_nlp()
        
        # Verify the results
        self.assertTrue(result, "Command should return True for successful execution")
        mock_display.start_loading_animation.assert_called_once()
        mock_nlp_handler.scan_buffer_for_nlp_sections.assert_called_once()
        mock_nlp_handler.process_nlp_sections.assert_called_once()
    
    def test_nlptranslate_no_sections(self):
        """Test nlptranslate command with no NLP sections present"""
        # Mock the NLPHandler with no sections
        mock_nlp_handler = MagicMock(spec=NLPHandler)
        mock_nlp_handler.nlp_sections = []  # No NLP sections
        self.editor.nlp_handler = mock_nlp_handler
        
        # Mock display with loading animation methods
        mock_display = MagicMock()
        mock_display.start_loading_animation = MagicMock()
        mock_display.stop_loading_animation = MagicMock()
        self.editor.display = mock_display
        
        # Execute the command
        result = self.command_handler._cmd_translate_nlp()
        
        # Verify the results
        self.assertFalse(result, "Command should return False when no sections found")
        mock_display.start_loading_animation.assert_called_once()
        mock_display.stop_loading_animation.assert_called_once()
        mock_nlp_handler.scan_buffer_for_nlp_sections.assert_called_once()
        mock_nlp_handler.process_nlp_sections.assert_not_called()
        self.editor.set_status_message.assert_called_with("No NLP sections found to translate")
    
    def test_nlptranslate_error_handling(self):
        """Test nlptranslate command error handling"""
        # Mock the NLPHandler that raises an exception
        mock_nlp_handler = MagicMock(spec=NLPHandler)
        mock_nlp_handler.scan_buffer_for_nlp_sections.side_effect = Exception("Test error")
        self.editor.nlp_handler = mock_nlp_handler
        
        # Mock display with loading animation methods
        mock_display = MagicMock()
        mock_display.start_loading_animation = MagicMock()
        mock_display.stop_loading_animation = MagicMock()
        self.editor.display = mock_display
        
        # Execute the command
        result = self.command_handler._cmd_translate_nlp()
        
        # Verify the results
        self.assertFalse(result, "Command should return False on error")
        mock_display.start_loading_animation.assert_called_once()
        mock_display.stop_loading_animation.assert_called_once()
        self.editor.set_status_message.assert_called_with("Error translating NLP sections: Test error")


if __name__ == '__main__':
    unittest.main()