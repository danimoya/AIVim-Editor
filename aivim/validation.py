"""
Input validation framework for AIVim
"""
import os
import re
from typing import Any, List, Optional, Tuple
from pathlib import Path

from .exceptions import (
    ValidationError,
    InvalidInputError,
    InvalidLineRangeError,
    FileOperationError,
)


class Validator:
    """Input validation framework with comprehensive validation methods"""

    # Regular expressions for common validations
    FILENAME_PATTERN = re.compile(r'^[^<>:"|?*\x00-\x1f]+$')
    COMMAND_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    MODEL_ID_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')

    @staticmethod
    def validate_filename(filename: str, allow_absolute: bool = True) -> str:
        """
        Validate and sanitize filename

        Args:
            filename: Filename to validate
            allow_absolute: Whether to allow absolute paths

        Returns:
            Sanitized filename

        Raises:
            InvalidInputError: If filename is invalid
        """
        if not filename:
            raise InvalidInputError("filename", "", "Filename cannot be empty")

        if not isinstance(filename, str):
            raise InvalidInputError("filename", str(filename), "Filename must be a string")

        # Check for path traversal attempts
        if ".." in filename:
            raise InvalidInputError(
                "filename", filename, "Path traversal not allowed (contains '..')"
            )

        # Check for absolute paths if not allowed
        if not allow_absolute and os.path.isabs(filename):
            raise InvalidInputError(
                "filename", filename, "Absolute paths not allowed in this context"
            )

        # Validate filename characters
        basename = os.path.basename(filename)
        if not Validator.FILENAME_PATTERN.match(basename):
            raise InvalidInputError(
                "filename",
                filename,
                "Filename contains invalid characters",
            )

        # Normalize path
        try:
            normalized = os.path.normpath(filename)
            return normalized
        except (ValueError, OSError) as e:
            raise InvalidInputError("filename", filename, f"Path normalization failed: {e}")

    @staticmethod
    def validate_line_number(
        line_number: int, max_lines: int, allow_zero: bool = False
    ) -> int:
        """
        Validate line number

        Args:
            line_number: Line number to validate
            max_lines: Maximum valid line number
            allow_zero: Whether to allow line number 0

        Returns:
            Validated line number

        Raises:
            InvalidInputError: If line number is invalid
        """
        if not isinstance(line_number, int):
            raise InvalidInputError(
                "line_number",
                str(line_number),
                f"Line number must be an integer, got {type(line_number).__name__}",
            )

        min_line = 0 if allow_zero else 1

        if line_number < min_line:
            raise InvalidInputError(
                "line_number",
                str(line_number),
                f"Line number must be >= {min_line}",
            )

        if line_number > max_lines:
            raise InvalidInputError(
                "line_number",
                str(line_number),
                f"Line number {line_number} exceeds buffer size ({max_lines} lines)",
            )

        return line_number

    @staticmethod
    def validate_line_range(
        start: int, end: int, max_lines: int, allow_zero: bool = False
    ) -> Tuple[int, int]:
        """
        Validate line range

        Args:
            start: Start line number
            end: End line number
            max_lines: Maximum valid line number
            allow_zero: Whether to allow line number 0

        Returns:
            Tuple of (validated_start, validated_end)

        Raises:
            InvalidLineRangeError: If line range is invalid
        """
        # Validate individual line numbers
        try:
            start = Validator.validate_line_number(start, max_lines, allow_zero)
            end = Validator.validate_line_number(end, max_lines, allow_zero)
        except InvalidInputError as e:
            raise InvalidLineRangeError(start, end, str(e))

        # Check range order
        if start > end:
            raise InvalidLineRangeError(
                start, end, f"Start line ({start}) must be <= end line ({end})"
            )

        return start, end

    @staticmethod
    def validate_column_number(column: int, max_columns: int) -> int:
        """
        Validate column number

        Args:
            column: Column number to validate
            max_columns: Maximum valid column number

        Returns:
            Validated column number

        Raises:
            InvalidInputError: If column number is invalid
        """
        if not isinstance(column, int):
            raise InvalidInputError(
                "column",
                str(column),
                f"Column must be an integer, got {type(column).__name__}",
            )

        if column < 0:
            raise InvalidInputError("column", str(column), "Column must be >= 0")

        if column > max_columns:
            raise InvalidInputError(
                "column",
                str(column),
                f"Column {column} exceeds line length ({max_columns})",
            )

        return column

    @staticmethod
    def validate_api_key(api_key: str, provider: str) -> str:
        """
        Validate API key format

        Args:
            api_key: API key to validate
            provider: Provider name (for error messages)

        Returns:
            Validated API key

        Raises:
            InvalidInputError: If API key is invalid
        """
        if not api_key:
            raise InvalidInputError("api_key", "", f"{provider} API key cannot be empty")

        if not isinstance(api_key, str):
            raise InvalidInputError(
                "api_key", str(api_key), f"{provider} API key must be a string"
            )

        # Basic length check
        if len(api_key) < 10:
            raise InvalidInputError(
                "api_key", "***", f"{provider} API key seems too short (< 10 characters)"
            )

        # Check for common mistakes
        if api_key.startswith("sk-") and len(api_key) < 20:
            raise InvalidInputError(
                "api_key",
                "sk-***",
                f"{provider} API key format appears invalid (too short for sk- prefix)",
            )

        return api_key

    @staticmethod
    def validate_model_id(model_id: str) -> str:
        """
        Validate model ID format

        Args:
            model_id: Model ID to validate

        Returns:
            Validated model ID

        Raises:
            InvalidInputError: If model ID is invalid
        """
        if not model_id:
            raise InvalidInputError("model_id", "", "Model ID cannot be empty")

        if not isinstance(model_id, str):
            raise InvalidInputError(
                "model_id", str(model_id), "Model ID must be a string"
            )

        if not Validator.MODEL_ID_PATTERN.match(model_id):
            raise InvalidInputError(
                "model_id",
                model_id,
                "Model ID contains invalid characters (allowed: a-z, A-Z, 0-9, ., _, -)",
            )

        return model_id

    @staticmethod
    def validate_command_name(command: str) -> str:
        """
        Validate command name format

        Args:
            command: Command name to validate

        Returns:
            Validated command name

        Raises:
            InvalidInputError: If command name is invalid
        """
        if not command:
            raise InvalidInputError("command", "", "Command name cannot be empty")

        if not isinstance(command, str):
            raise InvalidInputError(
                "command", str(command), "Command name must be a string"
            )

        if not Validator.COMMAND_PATTERN.match(command):
            raise InvalidInputError(
                "command",
                command,
                "Command name must start with letter and contain only letters, numbers, _, -",
            )

        return command

    @staticmethod
    def validate_timeout(timeout: float, min_timeout: float = 0.1, max_timeout: float = 600.0) -> float:
        """
        Validate timeout value

        Args:
            timeout: Timeout in seconds
            min_timeout: Minimum allowed timeout
            max_timeout: Maximum allowed timeout

        Returns:
            Validated timeout

        Raises:
            InvalidInputError: If timeout is invalid
        """
        if not isinstance(timeout, (int, float)):
            raise InvalidInputError(
                "timeout",
                str(timeout),
                f"Timeout must be a number, got {type(timeout).__name__}",
            )

        if timeout < min_timeout:
            raise InvalidInputError(
                "timeout",
                str(timeout),
                f"Timeout must be >= {min_timeout} seconds",
            )

        if timeout > max_timeout:
            raise InvalidInputError(
                "timeout",
                str(timeout),
                f"Timeout must be <= {max_timeout} seconds",
            )

        return float(timeout)

    @staticmethod
    def validate_buffer_size(size: int, max_size: int = 100_000_000) -> int:
        """
        Validate buffer/content size

        Args:
            size: Size in bytes
            max_size: Maximum allowed size

        Returns:
            Validated size

        Raises:
            InvalidInputError: If size is invalid
        """
        if not isinstance(size, int):
            raise InvalidInputError(
                "buffer_size", str(size), f"Size must be an integer, got {type(size).__name__}"
            )

        if size < 0:
            raise InvalidInputError("buffer_size", str(size), "Size must be >= 0")

        if size > max_size:
            raise InvalidInputError(
                "buffer_size",
                str(size),
                f"Size {size} bytes exceeds maximum ({max_size} bytes)",
            )

        return size

    @staticmethod
    def validate_api_response(
        response: Any, expected_type: type, required_keys: Optional[List[str]] = None
    ) -> Any:
        """
        Validate API response structure

        Args:
            response: Response to validate
            expected_type: Expected type of response
            required_keys: Required keys if response is a dict

        Returns:
            Validated response

        Raises:
            InvalidInputError: If response is invalid
        """
        if not isinstance(response, expected_type):
            raise InvalidInputError(
                "api_response",
                str(type(response).__name__),
                f"Expected {expected_type.__name__}, got {type(response).__name__}",
            )

        if required_keys and isinstance(response, dict):
            missing_keys = [key for key in required_keys if key not in response]
            if missing_keys:
                raise InvalidInputError(
                    "api_response",
                    "dict",
                    f"Missing required keys: {', '.join(missing_keys)}",
                )

        return response

    @staticmethod
    def validate_text_content(content: str, max_length: int = 1_000_000) -> str:
        """
        Validate text content

        Args:
            content: Text content to validate
            max_length: Maximum allowed length

        Returns:
            Validated content

        Raises:
            InvalidInputError: If content is invalid
        """
        if not isinstance(content, str):
            raise InvalidInputError(
                "content",
                str(type(content).__name__),
                f"Content must be a string, got {type(content).__name__}",
            )

        if len(content) > max_length:
            raise InvalidInputError(
                "content",
                f"{len(content)} chars",
                f"Content length {len(content)} exceeds maximum ({max_length} characters)",
            )

        return content

    @staticmethod
    def sanitize_status_message(message: str, max_length: int = 200) -> str:
        """
        Sanitize status message for display

        Args:
            message: Message to sanitize
            max_length: Maximum message length

        Returns:
            Sanitized message
        """
        if not isinstance(message, str):
            message = str(message)

        # Remove control characters except newline and tab
        sanitized = "".join(
            char for char in message if char in ("\n", "\t") or ord(char) >= 32
        )

        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[: max_length - 3] + "..."

        return sanitized

    @staticmethod
    def validate_file_exists(filepath: str) -> str:
        """
        Validate that file exists

        Args:
            filepath: Path to file

        Returns:
            Validated filepath

        Raises:
            FileOperationError: If file doesn't exist
        """
        filepath = Validator.validate_filename(filepath)

        if not os.path.exists(filepath):
            raise FileOperationError(filepath, "read", "File does not exist")

        if not os.path.isfile(filepath):
            raise FileOperationError(filepath, "read", "Path is not a file")

        return filepath

    @staticmethod
    def validate_file_writable(filepath: str) -> str:
        """
        Validate that file is writable

        Args:
            filepath: Path to file

        Returns:
            Validated filepath

        Raises:
            FileOperationError: If file is not writable
        """
        filepath = Validator.validate_filename(filepath)

        # Check parent directory is writable
        parent = os.path.dirname(filepath) or "."
        if not os.path.exists(parent):
            raise FileOperationError(
                filepath, "write", f"Parent directory does not exist: {parent}"
            )

        if not os.access(parent, os.W_OK):
            raise FileOperationError(filepath, "write", f"Parent directory not writable: {parent}")

        # Check file is writable if it exists
        if os.path.exists(filepath):
            if not os.path.isfile(filepath):
                raise FileOperationError(filepath, "write", "Path exists but is not a file")

            if not os.access(filepath, os.W_OK):
                raise FileOperationError(filepath, "write", "File is not writable")

        return filepath

    @staticmethod
    def validate_directory_exists(dirpath: str) -> str:
        """
        Validate that directory exists

        Args:
            dirpath: Path to directory

        Returns:
            Validated directory path

        Raises:
            FileOperationError: If directory doesn't exist
        """
        if not dirpath:
            raise InvalidInputError("directory", "", "Directory path cannot be empty")

        if not os.path.exists(dirpath):
            raise FileOperationError(dirpath, "read", "Directory does not exist")

        if not os.path.isdir(dirpath):
            raise FileOperationError(dirpath, "read", "Path is not a directory")

        return dirpath
