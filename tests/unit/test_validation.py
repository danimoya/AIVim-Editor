"""
Unit tests for input validation framework
"""
import pytest
import os
import tempfile
from pathlib import Path

from aivim.validation import Validator
from aivim.exceptions import (
    InvalidInputError,
    InvalidLineRangeError,
    FileOperationError,
)


class TestFilenameValidation:
    """Test filename validation"""

    def test_validate_simple_filename(self):
        """Test valid simple filename"""
        result = Validator.validate_filename("test.txt")
        assert result == "test.txt"

    def test_validate_filename_with_path(self):
        """Test valid filename with path"""
        result = Validator.validate_filename("path/to/test.txt")
        assert "test.txt" in result

    def test_validate_empty_filename(self):
        """Test empty filename raises error"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_filename("")
        assert "empty" in str(exc.value).lower()

    def test_validate_path_traversal(self):
        """Test path traversal prevention"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_filename("../etc/passwd")
        assert "traversal" in str(exc.value).lower()

    def test_validate_absolute_path_disallowed(self):
        """Test absolute path when not allowed"""
        with pytest.raises(InvalidInputError):
            Validator.validate_filename("/etc/passwd", allow_absolute=False)

    def test_validate_absolute_path_allowed(self):
        """Test absolute path when allowed"""
        result = Validator.validate_filename("/tmp/test.txt", allow_absolute=True)
        assert result == "/tmp/test.txt"


class TestLineNumberValidation:
    """Test line number validation"""

    def test_validate_valid_line_number(self):
        """Test valid line number"""
        result = Validator.validate_line_number(50, max_lines=100)
        assert result == 50

    def test_validate_line_number_negative(self):
        """Test negative line number"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_line_number(-1, max_lines=100)
        assert "must be >=" in str(exc.value)

    def test_validate_line_number_exceeds_max(self):
        """Test line number exceeds maximum"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_line_number(150, max_lines=100)
        assert "exceeds" in str(exc.value).lower()
        assert "100" in str(exc.value)

    def test_validate_line_number_zero_allowed(self):
        """Test line number zero when allowed"""
        result = Validator.validate_line_number(0, max_lines=100, allow_zero=True)
        assert result == 0

    def test_validate_line_number_zero_disallowed(self):
        """Test line number zero when not allowed"""
        with pytest.raises(InvalidInputError):
            Validator.validate_line_number(0, max_lines=100, allow_zero=False)


class TestLineRangeValidation:
    """Test line range validation"""

    def test_validate_valid_range(self):
        """Test valid line range"""
        start, end = Validator.validate_line_range(10, 20, max_lines=100)
        assert start == 10
        assert end == 20

    def test_validate_range_same_line(self):
        """Test range on same line"""
        start, end = Validator.validate_line_range(15, 15, max_lines=100)
        assert start == 15
        assert end == 15

    def test_validate_range_reversed(self):
        """Test reversed range (start > end)"""
        with pytest.raises(InvalidLineRangeError) as exc:
            Validator.validate_line_range(20, 10, max_lines=100)
        assert "must be <=" in str(exc.value)

    def test_validate_range_exceeds_max(self):
        """Test range exceeds maximum"""
        with pytest.raises(InvalidLineRangeError):
            Validator.validate_line_range(10, 150, max_lines=100)


class TestAPIKeyValidation:
    """Test API key validation"""

    def test_validate_valid_api_key(self):
        """Test valid API key"""
        result = Validator.validate_api_key("sk-1234567890abcdef1234567890", "OpenAI")
        assert result == "sk-1234567890abcdef1234567890"

    def test_validate_empty_api_key(self):
        """Test empty API key"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_api_key("", "OpenAI")
        assert "empty" in str(exc.value).lower()

    def test_validate_short_api_key(self):
        """Test too-short API key"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_api_key("short", "OpenAI")
        assert "short" in str(exc.value).lower()


class TestModelIDValidation:
    """Test model ID validation"""

    def test_validate_valid_model_id(self):
        """Test valid model ID"""
        result = Validator.validate_model_id("gpt-4o")
        assert result == "gpt-4o"

    def test_validate_complex_model_id(self):
        """Test complex model ID"""
        result = Validator.validate_model_id("claude-3-5-sonnet-20241022")
        assert result == "claude-3-5-sonnet-20241022"

    def test_validate_empty_model_id(self):
        """Test empty model ID"""
        with pytest.raises(InvalidInputError):
            Validator.validate_model_id("")

    def test_validate_invalid_model_id(self):
        """Test invalid characters in model ID"""
        with pytest.raises(InvalidInputError):
            Validator.validate_model_id("invalid model!")


class TestTimeoutValidation:
    """Test timeout validation"""

    def test_validate_valid_timeout(self):
        """Test valid timeout"""
        result = Validator.validate_timeout(30.0)
        assert result == 30.0

    def test_validate_timeout_too_small(self):
        """Test timeout below minimum"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_timeout(0.01, min_timeout=0.1)
        assert ">=" in str(exc.value)

    def test_validate_timeout_too_large(self):
        """Test timeout above maximum"""
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_timeout(1000.0, max_timeout=600.0)
        assert "<=" in str(exc.value)


class TestTextContentValidation:
    """Test text content validation"""

    def test_validate_simple_text(self):
        """Test simple text validation"""
        result = Validator.validate_text_content("Hello, world!")
        assert result == "Hello, world!"

    def test_validate_large_text(self):
        """Test large text validation"""
        text = "x" * 100000
        result = Validator.validate_text_content(text, max_length=200000)
        assert len(result) == 100000

    def test_validate_text_too_large(self):
        """Test text exceeding max length"""
        text = "x" * 2000
        with pytest.raises(InvalidInputError) as exc:
            Validator.validate_text_content(text, max_length=1000)
        assert "exceeds" in str(exc.value).lower()


class TestSanitization:
    """Test sanitization methods"""

    def test_sanitize_status_message(self):
        """Test status message sanitization"""
        result = Validator.sanitize_status_message("Normal message")
        assert result == "Normal message"

    def test_sanitize_control_characters(self):
        """Test control character removal"""
        result = Validator.sanitize_status_message("Test\x00\x01\x02message")
        assert "\x00" not in result
        assert "message" in result

    def test_sanitize_long_message(self):
        """Test truncation of long messages"""
        long_msg = "x" * 300
        result = Validator.sanitize_status_message(long_msg, max_length=200)
        assert len(result) <= 200
        assert result.endswith("...")


class TestFileValidation:
    """Test file validation methods"""

    def test_validate_file_exists(self):
        """Test file exists validation"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = Validator.validate_file_exists(tmp_path)
            assert result == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_validate_file_not_exists(self):
        """Test file does not exist"""
        with pytest.raises(FileOperationError) as exc:
            Validator.validate_file_exists("/nonexistent/file.txt")
        assert "does not exist" in str(exc.value).lower()

    def test_validate_directory_exists(self):
        """Test directory exists validation"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = Validator.validate_directory_exists(tmp_dir)
            assert result == tmp_dir

    def test_validate_directory_not_exists(self):
        """Test directory does not exist"""
        with pytest.raises(FileOperationError):
            Validator.validate_directory_exists("/nonexistent/directory")
