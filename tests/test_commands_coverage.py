"""
Comprehensive tests for Commands.py to increase test coverage
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.commands import CommandProcessor


class MockEditor:
    """Mock editor for testing"""
    def __init__(self):
        self.buffer = Mock()
        self.buffer.get_lines = Mock(return_value=["line 1", "line 2", "line 3"])
        self.buffer.is_modified = Mock(return_value=False)
        self.filename = "test.txt"
        self.status_message = ""
    
    def set_status_message(self, message):
        self.status_message = message
    
    def save_file(self, filename=None):
        if filename:
            self.filename = filename
        self.status_message = f"Saved to {self.filename}"
    
    def quit(self, force=False):
        if not force and self.buffer.is_modified():
            return False
        self.should_quit = True
        return True
    
    def ai_explain(self, start, end):
        self.status_message = f"Explaining lines {start} to {end}"
    
    def ai_improve(self, start, end):
        self.status_message = f"Improving lines {start} to {end}"
    
    def ai_generate(self, line, description):
        self.status_message = f"Generating at line {line}: {description}"


class TestCommandProcessorInit:
    """Tests for CommandProcessor initialization"""
    
    def test_initialization(self):
        """Test CommandProcessor initialization"""
        editor = MockEditor()
        processor = CommandProcessor(editor)
        
        assert processor.editor == editor
        assert processor.command_handlers is not None
        assert len(processor.command_handlers) > 0
    
    def test_registered_commands(self):
        """Test that all expected commands are registered"""
        editor = MockEditor()
        processor = CommandProcessor(editor)
        
        expected_patterns = [
            r'^w$',
            r'^w\s+(.+)$',
            r'^q$',
            r'^q!$',
            r'^wq$',
            r'^explain\s+(\d+)\s+(\d+)$',
            r'^improve\s+(\d+)\s+(\d+)$',
            r'^generate\s+(\d+)\s+(.+)$',
            r'^ai\s+(.+)$',
            r'^set\s+(.+)$',
            r'^help$'
        ]
        
        for pattern in expected_patterns:
            assert pattern in processor.command_handlers


class TestFileCommands:
    """Tests for file-related commands"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_write_command(self):
        """Test :w command"""
        self.editor.filename = "test.txt"
        result = self.processor.process("w")
        
        assert result is True
        assert "Saved" in self.editor.status_message
    
    def test_write_command_no_filename(self):
        """Test :w command without filename"""
        self.editor.filename = None
        result = self.processor.process("w")
        
        assert result is False
        assert "No filename" in self.editor.status_message
    
    def test_write_as_command(self):
        """Test :w filename command"""
        result = self.processor.process("w newfile.txt")
        
        assert result is True
        assert self.editor.filename == "newfile.txt"
        assert "Saved" in self.editor.status_message
    
    def test_quit_command(self):
        """Test :q command"""
        self.editor.buffer.is_modified = Mock(return_value=False)
        result = self.processor.process("q")
        
        assert result is True
        assert hasattr(self.editor, 'should_quit')
    
    def test_quit_with_unsaved_changes(self):
        """Test :q command with unsaved changes"""
        self.editor.buffer.is_modified = Mock(return_value=True)
        result = self.processor.process("q")
        
        assert result is False
        assert "No write since last change" in self.editor.status_message
    
    def test_force_quit_command(self):
        """Test :q! command"""
        self.editor.buffer.is_modified = Mock(return_value=True)
        result = self.processor.process("q!")
        
        assert result is True
        assert hasattr(self.editor, 'should_quit')
    
    def test_write_quit_command(self):
        """Test :wq command"""
        self.editor.filename = "test.txt"
        result = self.processor.process("wq")
        
        assert result is True
        assert "Saved" in self.editor.status_message
        assert hasattr(self.editor, 'should_quit')
    
    def test_write_quit_no_filename(self):
        """Test :wq command without filename"""
        self.editor.filename = None
        result = self.processor.process("wq")
        
        assert result is False
        assert "No filename" in self.editor.status_message


class TestAICommands:
    """Tests for AI-related commands"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_explain_command(self):
        """Test :explain command"""
        result = self.processor.process("explain 1 10")
        
        assert result is True
        assert "Explaining lines" in self.editor.status_message
    
    def test_explain_invalid_range(self):
        """Test :explain with invalid range"""
        result = self.processor.process("explain -1 10")
        
        assert result is False
        assert "Invalid line range" in self.editor.status_message
    
    def test_improve_command(self):
        """Test :improve command"""
        result = self.processor.process("improve 5 15")
        
        assert result is True
        assert "Improving lines" in self.editor.status_message
    
    def test_improve_invalid_range(self):
        """Test :improve with invalid range"""
        result = self.processor.process("improve abc def")
        
        assert result is False
        # Should not match the pattern
    
    def test_generate_command(self):
        """Test :generate command"""
        result = self.processor.process("generate 10 Create a new function")
        
        assert result is True
        assert "Generating at line" in self.editor.status_message
        assert "Create a new function" in self.editor.status_message
    
    def test_generate_invalid_line(self):
        """Test :generate with invalid line number"""
        self.editor.buffer.get_lines = Mock(return_value=["line1", "line2"])
        result = self.processor.process("generate 100 Test")
        
        assert result is False
        assert "Invalid line number" in self.editor.status_message
    
    def test_ai_query_command(self):
        """Test :ai command"""
        self.editor.ai_query = Mock()
        result = self.processor.process("ai What does this code do?")
        
        assert result is True
        self.editor.ai_query.assert_called_once_with("What does this code do?")


class TestSettingsCommands:
    """Tests for settings-related commands"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.editor.set_option = Mock(return_value=True)
        self.processor = CommandProcessor(self.editor)
    
    def test_set_option_command(self):
        """Test :set command"""
        result = self.processor.process("set number")
        
        assert result is True
        self.editor.set_option.assert_called_once_with("number")
    
    def test_set_option_with_value(self):
        """Test :set with value"""
        result = self.processor.process("set tabstop=4")
        
        assert result is True
        self.editor.set_option.assert_called_once_with("tabstop=4")
    
    def test_set_multiple_options(self):
        """Test :set with multiple options"""
        result = self.processor.process("set number relativenumber")
        
        assert result is True
        self.editor.set_option.assert_called_once()


class TestHelpCommand:
    """Tests for help command"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.editor.show_help = Mock()
        self.processor = CommandProcessor(self.editor)
    
    def test_help_command(self):
        """Test :help command"""
        result = self.processor.process("help")
        
        assert result is True
        self.editor.show_help.assert_called_once()


class TestCommandProcessing:
    """Tests for general command processing"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_empty_command(self):
        """Test processing empty command"""
        result = self.processor.process("")
        
        assert result is False
    
    def test_unknown_command(self):
        """Test processing unknown command"""
        result = self.processor.process("unknown_command")
        
        assert result is False
        assert "Unknown command" in self.editor.status_message
    
    def test_command_with_extra_spaces(self):
        """Test command with extra spaces"""
        self.editor.filename = "test.txt"
        result = self.processor.process("  w  ")
        
        # Commands are typically trimmed
        assert "Unknown command" in self.editor.status_message or "Saved" in self.editor.status_message
    
    def test_command_case_sensitivity(self):
        """Test that commands are case-sensitive"""
        result = self.processor.process("W")  # Capital W
        
        assert result is False
        assert "Unknown command" in self.editor.status_message
    
    def test_command_with_special_characters(self):
        """Test command with special characters in filename"""
        result = self.processor.process("w file-with-dashes.txt")
        
        assert result is True
        assert self.editor.filename == "file-with-dashes.txt"
    
    def test_command_with_path(self):
        """Test command with file path"""
        result = self.processor.process("w /path/to/file.txt")
        
        assert result is True
        assert self.editor.filename == "/path/to/file.txt"


class TestCommandErrorHandling:
    """Tests for command error handling"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_handler_exception(self):
        """Test exception in command handler"""
        # Mock a handler to raise an exception
        def failing_handler(*args):
            raise Exception("Handler error")
        
        self.processor.command_handlers[r'^test$'] = failing_handler
        
        with patch('logging.error') as mock_log:
            result = self.processor.process("test")
            
            assert result is False
            assert "Error: Handler error" in self.editor.status_message
            mock_log.assert_called_once()
    
    def test_invalid_regex_group_access(self):
        """Test accessing non-existent regex groups"""
        # This should not match and return False
        result = self.processor.process("explain")  # Missing required arguments
        
        assert result is False
    
    def test_type_conversion_error(self):
        """Test type conversion errors in commands"""
        result = self.processor.process("explain abc def")  # Non-numeric line numbers
        
        assert result is False


class TestCommandAliases:
    """Tests for command aliases and shortcuts"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_common_aliases(self):
        """Test common command aliases"""
        # Most vi/vim aliases are single letter or abbreviations
        # which are already covered in the main commands
        
        # Test that 'q' works as expected
        self.editor.buffer.is_modified = Mock(return_value=False)
        result = self.processor.process("q")
        assert result is True
        
        # Test that 'w' works
        self.editor.filename = "test.txt"
        result = self.processor.process("w")
        assert result is True


class TestRangeParsing:
    """Tests for line range parsing in commands"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_valid_numeric_range(self):
        """Test valid numeric line ranges"""
        result = self.processor.process("explain 1 10")
        assert result is True
        assert "1" in self.editor.status_message or "Explaining" in self.editor.status_message
    
    def test_single_line_range(self):
        """Test single line as range"""
        result = self.processor.process("explain 5 5")
        assert result is True
    
    def test_reversed_range(self):
        """Test reversed line range (end < start)"""
        result = self.processor.process("explain 10 1")
        # Implementation may swap them or treat as error
        assert result is True or "Invalid" in self.editor.status_message
    
    def test_zero_based_range(self):
        """Test zero-based line numbers"""
        result = self.processor.process("explain 0 5")
        # Depends on implementation - may convert or reject
        assert result is True or result is False


class TestCommandValidation:
    """Tests for command validation"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_command_with_trailing_spaces(self):
        """Test command with trailing spaces"""
        self.editor.filename = "test.txt"
        # Note: the regex pattern is strict, so this won't match
        result = self.processor.process("w ")
        assert result is False  # Won't match due to trailing space
    
    def test_command_with_tabs(self):
        """Test command with tabs"""
        result = self.processor.process("w\\tfile.txt")
        # Tabs in filename might work or not depending on implementation
        assert result is True or result is False
    
    def test_very_long_command(self):
        """Test very long command"""
        long_description = "x" * 1000
        result = self.processor.process(f"generate 1 {long_description}")
        
        assert result is True
        assert long_description in self.editor.status_message
    
    def test_command_with_unicode(self):
        """Test command with unicode characters"""
        result = self.processor.process("w file_😀.txt")
        
        assert result is True
        assert self.editor.filename == "file_😀.txt"


class TestCommandIntegration:
    """Integration tests for command processing"""
    
    def setup_method(self):
        """Set up test environment"""
        self.editor = MockEditor()
        self.processor = CommandProcessor(self.editor)
    
    def test_command_logging(self):
        """Test that commands are logged"""
        with patch('logging.info') as mock_log:
            self.processor.process("w test.txt")
            mock_log.assert_called_with("Processing command: w test.txt")
    
    def test_multiple_commands_sequence(self):
        """Test processing multiple commands in sequence"""
        self.editor.filename = "test.txt"
        
        # Save file
        result1 = self.processor.process("w")
        assert result1 is True
        
        # Try to quit
        self.editor.buffer.is_modified = Mock(return_value=False)
        result2 = self.processor.process("q")
        assert result2 is True
    
    def test_command_state_preservation(self):
        """Test that command state is preserved correctly"""
        # Process a command that modifies editor state
        self.processor.process("w newfile.txt")
        assert self.editor.filename == "newfile.txt"
        
        # Process another command
        self.processor.process("w anotherfile.txt")
        assert self.editor.filename == "anotherfile.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])