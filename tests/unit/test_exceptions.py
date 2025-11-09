"""
Unit tests for custom exception hierarchy
"""
import pytest
from aivim.exceptions import (
    AIVimError,
    EditorError,
    BufferError,
    InvalidLineError,
    FileOperationError,
    FileNotFoundError,
    AIServiceError,
    AIProviderError,
    AIProviderNotAvailableError,
    AIProviderTimeoutError,
    ConfigurationError,
    InvalidConfigError,
    CommandError,
    InvalidCommandError,
    ValidationError,
    InvalidInputError,
)


class TestBaseException:
    """Test base exception class"""

    def test_basic_exception(self):
        """Test basic exception creation"""
        error = AIVimError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_exception_with_details(self):
        """Test exception with details dictionary"""
        error = AIVimError("Test error", {"key": "value", "count": 42})
        assert "Test error" in str(error)
        assert "key=value" in str(error)
        assert "count=42" in str(error)

    def test_exception_inheritance(self):
        """Test exception hierarchy"""
        error = EditorError("Editor error")
        assert isinstance(error, AIVimError)
        assert isinstance(error, Exception)


class TestFileOperationError:
    """Test file operation errors"""

    def test_file_operation_error(self):
        """Test file operation error creation"""
        error = FileOperationError("test.txt", "read", "File not found")
        assert error.filename == "test.txt"
        assert error.operation == "read"
        assert error.reason == "File not found"
        assert "test.txt" in str(error)
        assert "read" in str(error)

    def test_file_not_found_error(self):
        """Test file not found error"""
        error = FileNotFoundError("missing.txt")
        assert error.filename == "missing.txt"
        assert error.operation == "read"
        assert "File not found" in error.reason


class TestBufferError:
    """Test buffer errors"""

    def test_invalid_line_error(self):
        """Test invalid line error"""
        error = InvalidLineError(150, 100)
        assert error.line_number == 150
        assert error.max_lines == 100
        assert "150" in str(error)
        assert "100" in str(error)


class TestAIProviderError:
    """Test AI provider errors"""

    def test_provider_error_basic(self):
        """Test basic AI provider error"""
        error = AIProviderError("openai", "Request failed")
        assert error.provider == "openai"
        assert "[openai]" in str(error)
        assert "Request failed" in str(error)

    def test_provider_error_with_code(self):
        """Test AI provider error with error code"""
        error = AIProviderError("claude", "API error", "ERR_123")
        assert error.provider == "claude"
        assert error.error_code == "ERR_123"
        assert "[claude]" in str(error)

    def test_provider_not_available_error(self):
        """Test provider not available error"""
        error = AIProviderNotAvailableError("local", "Model not loaded")
        assert error.provider == "local"
        assert error.reason == "Model not loaded"

    def test_provider_timeout_error(self):
        """Test provider timeout error"""
        error = AIProviderTimeoutError("openai", 30.0)
        assert error.provider == "openai"
        assert error.timeout == 30.0
        assert "30" in str(error)


class TestCommandError:
    """Test command errors"""

    def test_invalid_command_error(self):
        """Test invalid command error"""
        error = InvalidCommandError("invalidcmd")
        assert error.command == "invalidcmd"
        assert "invalidcmd" in str(error)
        assert ":help" in str(error)


class TestValidationError:
    """Test validation errors"""

    def test_invalid_input_error(self):
        """Test invalid input error"""
        error = InvalidInputError("filename", "../etc/passwd", "Path traversal not allowed")
        assert error.field == "filename"
        assert error.value == "../etc/passwd"
        assert "filename" in str(error)
        assert "Path traversal" in str(error)


class TestConfigurationError:
    """Test configuration errors"""

    def test_invalid_config_error(self):
        """Test invalid configuration error"""
        error = InvalidConfigError("~/.aivimrc", "Missing required field")
        assert error.config_file == "~/.aivimrc"
        assert error.reason == "Missing required field"
        assert "~/.aivimrc" in str(error)
