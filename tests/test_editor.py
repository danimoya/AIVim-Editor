"""
Tests for the editor component
"""
import os
import pytest
from unittest.mock import MagicMock, patch

from aivim.editor import Editor
from aivim.modes import Mode


class TestEditor:
    """Tests for the Editor class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = Editor()
    
    def test_initialization(self):
        """Test editor initialization"""
        assert self.editor.filename is None
        assert self.editor.mode == Mode.NORMAL
        assert self.editor.cursor_x == 0
        assert self.editor.cursor_y == 0
        assert self.editor.command_line == ""
        assert not self.editor.ai_processing
    
    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file"""
        self.editor.load_file("nonexistent_file.txt")
        assert "Error loading file" in self.editor.status_message
    
    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="No OpenAI API key available")
    def test_save_file(self, tmp_path):
        """Test saving a file"""
        # Create a temporary file path
        temp_file = tmp_path / "test_file.txt"
        
        # Set some content in the buffer
        self.editor.buffer.set_content("Test content\nLine 2")
        
        # Save the file
        self.editor.save_file(str(temp_file))
        
        # Verify file was saved
        assert temp_file.exists()
        assert temp_file.read_text() == "Test content\nLine 2"
        assert "Saved" in self.editor.status_message
    
    def test_quit_with_unsaved_changes(self):
        """Test quitting with unsaved changes"""
        # Modify the buffer
        self.editor.buffer.set_content("Modified content")
        
        # Try to quit
        self.editor.quit()
        
        # Should not quit and show a warning
        assert self.editor.running is not False
        assert "Unsaved changes" in self.editor.status_message
        
        # Force quit
        self.editor.quit(force=True)
        assert self.editor.running is False
    
    @patch('aivim.ai_service.AIService')
    def test_run_ai_command(self, mock_ai_service):
        """Test running an AI command"""
        # Setup mocks
        self.editor.ai_service = MagicMock()
        self.editor.ai_service.get_explanation.return_value = "Test explanation"
        
        # Add some content to the buffer
        self.editor.buffer.set_content("def test_function():\n    return True")
        
        # Run an AI command
        self.editor.run_ai_command("explain", ["1", "2"])
        
        # Since this runs in a thread, we need to mock and check if thread was started
        assert self.editor.ai_processing is True
        assert "Processing AI request" in self.editor.status_message
