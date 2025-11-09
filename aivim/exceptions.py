"""
Custom exception hierarchy for AIVim
"""


class AIVimError(Exception):
    """Base exception for all AIVim errors"""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize AIVim exception

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class EditorError(AIVimError):
    """Errors related to editor operations"""

    pass


class BufferError(EditorError):
    """Errors related to buffer operations"""

    pass


class InvalidLineError(BufferError):
    """Error when accessing invalid line number"""

    def __init__(self, line_number: int, max_lines: int):
        super().__init__(
            f"Invalid line number: {line_number}",
            {"line_number": line_number, "max_lines": max_lines},
        )
        self.line_number = line_number
        self.max_lines = max_lines


class BufferModificationError(BufferError):
    """Error when buffer modification fails"""

    pass


class FileOperationError(EditorError):
    """Errors related to file I/O operations"""

    def __init__(self, filename: str, operation: str, reason: str):
        super().__init__(
            f"File {operation} failed: {filename}",
            {"filename": filename, "operation": operation, "reason": reason},
        )
        self.filename = filename
        self.operation = operation
        self.reason = reason


class FileNotFoundError(FileOperationError):
    """Error when file is not found"""

    def __init__(self, filename: str):
        super().__init__(filename, "read", "File not found")


class FilePermissionError(FileOperationError):
    """Error when file permissions are insufficient"""

    def __init__(self, filename: str, operation: str):
        super().__init__(filename, operation, "Permission denied")


class AIServiceError(AIVimError):
    """Errors related to AI service operations"""

    pass


class AIProviderError(AIServiceError):
    """Errors from specific AI providers"""

    def __init__(self, provider: str, message: str, error_code: str = None):
        super().__init__(
            f"[{provider}] {message}",
            {"provider": provider, "error_code": error_code} if error_code else {"provider": provider},
        )
        self.provider = provider
        self.error_code = error_code


class AIProviderNotAvailableError(AIProviderError):
    """Error when AI provider is not available or configured"""

    def __init__(self, provider: str, reason: str = "Not configured"):
        super().__init__(provider, f"Provider not available: {reason}")
        self.reason = reason


class AIProviderAuthError(AIProviderError):
    """Error when AI provider authentication fails"""

    def __init__(self, provider: str):
        super().__init__(provider, "Authentication failed - check API key")


class AIProviderQuotaError(AIProviderError):
    """Error when AI provider quota is exceeded"""

    def __init__(self, provider: str):
        super().__init__(provider, "API quota exceeded")


class AIProviderTimeoutError(AIProviderError):
    """Error when AI provider request times out"""

    def __init__(self, provider: str, timeout: float):
        super().__init__(provider, f"Request timed out after {timeout}s")
        self.timeout = timeout


class AIProviderResponseError(AIProviderError):
    """Error when AI provider returns invalid response"""

    def __init__(self, provider: str, reason: str):
        super().__init__(provider, f"Invalid response: {reason}")


class ConfigurationError(AIVimError):
    """Errors related to configuration"""

    pass


class InvalidConfigError(ConfigurationError):
    """Error when configuration is invalid"""

    def __init__(self, config_file: str, reason: str):
        super().__init__(
            f"Invalid configuration in {config_file}: {reason}",
            {"config_file": config_file, "reason": reason},
        )
        self.config_file = config_file


class MissingConfigError(ConfigurationError):
    """Error when required configuration is missing"""

    def __init__(self, key: str, config_file: str = None):
        message = f"Missing required configuration: {key}"
        if config_file:
            message += f" in {config_file}"
        super().__init__(message, {"key": key, "config_file": config_file})
        self.key = key


class CommandError(AIVimError):
    """Errors related to command execution"""

    pass


class InvalidCommandError(CommandError):
    """Error when command is invalid or unknown"""

    def __init__(self, command: str):
        super().__init__(
            f"Unknown command: '{command}'. Type ':help' for available commands.",
            {"command": command},
        )
        self.command = command


class CommandExecutionError(CommandError):
    """Error when command execution fails"""

    def __init__(self, command: str, reason: str):
        super().__init__(
            f"Command '{command}' failed: {reason}", {"command": command, "reason": reason}
        )
        self.command = command
        self.reason = reason


class InvalidCommandArgumentError(CommandError):
    """Error when command arguments are invalid"""

    def __init__(self, command: str, argument: str, reason: str):
        super().__init__(
            f"Invalid argument '{argument}' for command '{command}': {reason}",
            {"command": command, "argument": argument, "reason": reason},
        )
        self.command = command
        self.argument = argument


class ValidationError(AIVimError):
    """Errors related to input validation"""

    pass


class InvalidInputError(ValidationError):
    """Error when input validation fails"""

    def __init__(self, field: str, value: str, reason: str):
        super().__init__(
            f"Invalid {field}: {reason}", {"field": field, "value": value, "reason": reason}
        )
        self.field = field
        self.value = value


class InvalidLineRangeError(ValidationError):
    """Error when line range is invalid"""

    def __init__(self, start: int, end: int, reason: str):
        super().__init__(
            f"Invalid line range [{start}:{end}]: {reason}",
            {"start": start, "end": end, "reason": reason},
        )
        self.start = start
        self.end = end


class DisplayError(AIVimError):
    """Errors related to display/UI operations"""

    pass


class TerminalError(DisplayError):
    """Error when terminal operations fail"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"Terminal {operation} failed: {reason}", {"operation": operation, "reason": reason}
        )


class HistoryError(AIVimError):
    """Errors related to history/undo operations"""

    pass


class UndoError(HistoryError):
    """Error when undo operation fails"""

    def __init__(self, reason: str):
        super().__init__(f"Cannot undo: {reason}", {"reason": reason})


class RedoError(HistoryError):
    """Error when redo operation fails"""

    def __init__(self, reason: str):
        super().__init__(f"Cannot redo: {reason}", {"reason": reason})


class NLPModeError(AIVimError):
    """Errors related to NLP mode operations"""

    pass


class NLPTranslationError(NLPModeError):
    """Error when NLP translation fails"""

    def __init__(self, section: str, reason: str):
        super().__init__(
            f"NLP translation failed for section '{section}': {reason}",
            {"section": section, "reason": reason},
        )


class PluginError(AIVimError):
    """Errors related to plugin operations"""

    pass


class PluginLoadError(PluginError):
    """Error when plugin loading fails"""

    def __init__(self, plugin_name: str, reason: str):
        super().__init__(
            f"Failed to load plugin '{plugin_name}': {reason}",
            {"plugin_name": plugin_name, "reason": reason},
        )


class PluginNotFoundError(PluginError):
    """Error when plugin is not found"""

    def __init__(self, plugin_name: str):
        super().__init__(f"Plugin not found: '{plugin_name}'", {"plugin_name": plugin_name})
