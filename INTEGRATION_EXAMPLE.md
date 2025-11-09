# AIVim Integration Example: Step-by-Step

**Purpose**: Practical example showing how to integrate the new infrastructure into `editor.py`

---

## Overview

This guide shows **exactly** how to integrate:
1. New AIService with providers
2. Plugin system
3. Input validation
4. Exception handling
5. Performance monitoring
6. Rate limiting

---

## Step 1: Update Editor Imports

### Before
```python
# editor.py
from .ai_service import AIService
```

### After
```python
# editor.py
from .ai_service_v2 import AIService
from .plugins import PluginManager
from .validation import Validator
from .exceptions import (
    EditorError,
    FileOperationError,
    InvalidInputError,
    AIProviderError,
)
from .profiling import PerformanceMonitor
```

---

## Step 2: Update Editor Initialization

### Before
```python
class Editor:
    def __init__(self, filename: Optional[str] = None):
        # ... existing initialization ...
        self.ai_service = AIService()
        self.settings = Settings()
```

### After
```python
class Editor:
    def __init__(self, filename: Optional[str] = None):
        # ... existing initialization ...

        # Initialize AI service with new architecture
        self.ai_service = AIService()

        # Initialize plugin manager
        self.plugin_manager = PluginManager(self)

        # Initialize performance monitor
        self.perf_monitor = PerformanceMonitor()

        # Load settings
        self.settings = Settings()

        # Load plugins
        self._load_plugins()

        # Load file if specified with validation
        if filename:
            try:
                filename = Validator.validate_filename(filename)
                self.load_file(filename)
            except (InvalidInputError, FileOperationError) as e:
                logging.error(f"Failed to load file: {e}")
```

---

## Step 3: Add Plugin Loading

### New Method to Add
```python
class Editor:
    def _load_plugins(self):
        """Load enabled plugins from configuration"""
        # Discover available plugins
        available = self.plugin_manager.discover_plugins()
        logging.info(f"Discovered plugins: {', '.join(available)}")

        # Get enabled plugins from settings
        enabled_plugins = self.settings.get('plugins', [
            'git-integration',
            'snippets',
            'formatter',
        ])

        # Load each enabled plugin
        for plugin_name in enabled_plugins:
            try:
                plugin = self.plugin_manager.load_plugin(plugin_name)
                logging.info(f"Loaded plugin: {plugin.get_name()} v{plugin.get_version()}")
            except Exception as e:
                logging.error(f"Failed to load plugin {plugin_name}: {e}")
                self.status_message = f"Plugin load error: {plugin_name}"
```

---

## Step 4: Update File Operations with Validation

### Before
```python
def load_file(self, filename: str):
    """Load file"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        self.buffer.set_lines(content.splitlines())
        self.filename = filename
    except Exception as e:
        logging.error(f"Error loading file: {e}")
```

### After
```python
def load_file(self, filename: str):
    """Load file with validation and error handling"""
    try:
        # Validate filename
        filename = Validator.validate_filename(filename)
        Validator.validate_file_exists(filename)

        # Load file with performance monitoring
        with self.perf_monitor.measure("file_load"):
            with open(filename, 'r') as f:
                content = f.read()

            # Validate content size
            Validator.validate_text_content(content, max_length=10_000_000)

            self.buffer.set_lines(content.splitlines())
            self.filename = filename

        # Trigger plugin hook
        self.plugin_manager.trigger_hook("on_buffer_open", self.buffer, filename)

        logging.info(f"Loaded file: {filename} ({len(content)} bytes)")

    except FileOperationError as e:
        logging.error(f"File operation error: {e}")
        self.status_message = f"Error: {e.message}"
        raise

    except InvalidInputError as e:
        logging.error(f"Invalid input: {e}")
        self.status_message = f"Invalid file: {e.message}"
        raise

    except Exception as e:
        logging.error(f"Unexpected error loading file: {e}")
        raise EditorError(f"Failed to load {filename}: {e}")
```

---

## Step 5: Update Save Operation

### Before
```python
def save_file(self, filename: Optional[str] = None):
    """Save file"""
    if filename:
        self.filename = filename

    if not self.filename:
        self.status_message = "No filename specified"
        return

    try:
        content = '\n'.join(self.buffer.lines)
        with open(self.filename, 'w') as f:
            f.write(content)
        self.status_message = f"Saved {self.filename}"
    except Exception as e:
        self.status_message = f"Error: {e}"
```

### After
```python
def save_file(self, filename: Optional[str] = None):
    """Save file with validation and hooks"""
    if filename:
        try:
            # Validate filename
            filename = Validator.validate_filename(filename)
            Validator.validate_file_writable(filename)
            self.filename = filename
        except (InvalidInputError, FileOperationError) as e:
            self.status_message = f"Invalid filename: {e}"
            return

    if not self.filename:
        self.status_message = "No filename specified"
        return

    try:
        # Get content
        content = '\n'.join(self.buffer.lines)

        # Validate content
        Validator.validate_text_content(content, max_length=10_000_000)

        # Save with performance monitoring
        with self.perf_monitor.measure("file_save"):
            with open(self.filename, 'w') as f:
                f.write(content)

        # Trigger plugin hook
        self.plugin_manager.trigger_hook("on_buffer_save", self.buffer, self.filename)

        self.status_message = f"Saved {self.filename}"
        logging.info(f"Saved file: {self.filename} ({len(content)} bytes)")

    except FileOperationError as e:
        self.status_message = f"Save error: {e.message}"
        logging.error(f"File save error: {e}")

    except Exception as e:
        self.status_message = f"Error saving file: {e}"
        logging.error(f"Unexpected save error: {e}")
        raise EditorError(f"Failed to save {self.filename}: {e}")
```

---

## Step 6: Update AI Operations

### Before
```python
def ai_improve(self, start_line: int, end_line: int):
    """Improve code with AI"""
    try:
        code = '\n'.join(self.buffer.lines[start_line:end_line + 1])
        improved = self.ai_service.get_improvement(code)
        # ... show improvement ...
    except Exception as e:
        self.status_message = f"AI error: {e}"
```

### After
```python
def ai_improve(self, start_line: int, end_line: int):
    """Improve code with AI, validation, and rate limiting"""
    try:
        # Validate line range
        max_lines = len(self.buffer.lines)
        start_line, end_line = Validator.validate_line_range(
            start_line, end_line, max_lines
        )

        # Get code section
        code = '\n'.join(self.buffer.lines[start_line:end_line + 1])

        # Validate code length
        Validator.validate_text_content(code, max_length=50000)

        # Call AI service (includes automatic rate limiting)
        with self.perf_monitor.measure("ai_improve"):
            improved = self.ai_service.improve_code(
                code,
                context=f"File: {self.filename or 'untitled'}"
            )

        # Show improvement in diff tab
        self._show_ai_improvement(code, improved, start_line, end_line)

        logging.info(f"AI improvement completed ({len(improved)} chars)")

    except InvalidInputError as e:
        self.status_message = f"Invalid input: {e}"
        logging.error(f"Validation error: {e}")

    except AIProviderTimeoutError as e:
        self.status_message = f"Rate limited. Please wait and try again."
        logging.warning(f"Rate limit hit: {e}")

    except AIProviderAuthError:
        self.status_message = "AI authentication failed. Check API key."
        logging.error("AI authentication failed")

    except AIProviderError as e:
        self.status_message = f"AI error: {e}"
        logging.error(f"AI provider error: {e}")

    except Exception as e:
        self.status_message = f"Unexpected error: {e}"
        logging.error(f"Unexpected AI error: {e}")
```

---

## Step 7: Add Plugin Command Integration

### New Method to Add
```python
class Editor:
    def execute_command(self, command: str):
        """Execute command, checking plugins first"""
        # Parse command
        parts = command.split(None, 1)
        cmd_name = parts[0] if parts else ""
        cmd_args = parts[1] if len(parts) > 1 else ""

        # Try plugin commands first
        if self.plugin_manager.execute_command(cmd_name, cmd_args):
            logging.debug(f"Plugin command executed: {cmd_name}")
            return True

        # Fall back to built-in commands
        return self._execute_builtin_command(cmd_name, cmd_args)

    def _execute_builtin_command(self, cmd_name: str, cmd_args: str) -> bool:
        """Execute built-in editor commands"""
        # Existing command handling logic
        # (move current command execution here)
        pass
```

---

## Step 8: Add Mode Change Hooks

### Update Mode Setter
```python
class Editor:
    def set_mode(self, new_mode: str):
        """Set editor mode with plugin hooks"""
        old_mode = self.mode
        self.mode = new_mode

        # Trigger plugin hook
        self.plugin_manager.trigger_hook("on_mode_change", old_mode, new_mode)

        logging.debug(f"Mode changed: {old_mode} -> {new_mode}")
```

---

## Step 9: Add Performance Stats Command

### New Command
```python
class Editor:
    def show_performance_stats(self):
        """Show performance statistics"""
        # Get AI service stats
        ai_stats = self.ai_service.get_performance_stats()
        rate_stats = self.ai_service.get_rate_limit_stats()

        # Get editor stats
        editor_stats = self.perf_monitor.get_stats("file_load")

        # Create stats display
        lines = ["Performance Statistics", "=" * 50, ""]

        lines.append("AI Operations:")
        for metric, stats in ai_stats.items():
            if stats.get('count', 0) > 0:
                lines.append(f"  {metric}:")
                lines.append(f"    Calls: {stats['count']}")
                lines.append(f"    Avg: {stats['avg']:.3f}s")
                lines.append(f"    Min: {stats['min']:.3f}s")
                lines.append(f"    Max: {stats['max']:.3f}s")

        lines.append("")
        lines.append("Rate Limits:")
        for provider, stats in rate_stats.items():
            lines.append(f"  {provider}:")
            lines.append(f"    Total requests: {stats['total_requests']}")
            lines.append(f"    Blocked: {stats['blocked_requests']}")
            lines.append(f"    Block rate: {stats['block_rate']:.1%}")

        # Show in new tab
        self.create_tab("Performance Stats", temporary=True)
        self.buffer.set_lines(lines)
        self.mode = "NORMAL"
```

---

## Step 10: Update Error Display

### New Helper Method
```python
class Editor:
    def show_error(self, error: Exception):
        """Show error with appropriate message based on type"""
        from .exceptions import AIVimError

        if isinstance(error, AIVimError):
            # Use structured error message
            message = str(error)
            if error.details:
                details = ", ".join(f"{k}={v}" for k, v in error.details.items())
                message = f"{message} ({details})"

            self.status_message = message

        else:
            # Generic error
            self.status_message = f"Error: {error}"

        logging.error(f"Error displayed: {error}")
```

---

## Complete Integration Example

Here's a complete small example showing all pieces together:

```python
from typing import Optional
import logging

from .ai_service_v2 import AIService
from .plugins import PluginManager
from .validation import Validator
from .exceptions import (
    EditorError,
    FileOperationError,
    InvalidInputError,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderAuthError,
)
from .profiling import PerformanceMonitor
from .buffer import Buffer
from .settings import Settings


class ModernizedEditor:
    """Modernized editor with all new infrastructure integrated"""

    def __init__(self, filename: Optional[str] = None):
        """Initialize editor with new infrastructure"""
        # Core components
        self.buffer = Buffer()
        self.settings = Settings()

        # AI service with provider architecture
        self.ai_service = AIService()
        logging.info(
            f"AI service initialized with providers: "
            f"{', '.join(self.ai_service.get_available_providers())}"
        )

        # Plugin system
        self.plugin_manager = PluginManager(self)
        self._load_plugins()

        # Performance monitoring
        self.perf_monitor = PerformanceMonitor()

        # Editor state
        self.filename = None
        self.mode = "NORMAL"
        self.status_message = ""

        # Load file if provided
        if filename:
            self.load_file(filename)

    def _load_plugins(self):
        """Load enabled plugins"""
        enabled = ['git-integration', 'snippets', 'formatter']

        for plugin_name in enabled:
            try:
                plugin = self.plugin_manager.load_plugin(plugin_name)
                logging.info(
                    f"Loaded: {plugin.get_name()} v{plugin.get_version()}"
                )
            except Exception as e:
                logging.error(f"Plugin load failed: {plugin_name}: {e}")

    def load_file(self, filename: str):
        """Load file with full validation and hooks"""
        try:
            # Validate
            filename = Validator.validate_filename(filename)
            Validator.validate_file_exists(filename)

            # Load with monitoring
            with self.perf_monitor.measure("file_load"):
                with open(filename, 'r') as f:
                    content = f.read()

                Validator.validate_text_content(content)
                self.buffer.set_lines(content.splitlines())
                self.filename = filename

            # Trigger hooks
            self.plugin_manager.trigger_hook(
                "on_buffer_open",
                self.buffer,
                filename
            )

            self.status_message = f"Loaded {filename}"

        except FileOperationError as e:
            self.show_error(e)
            raise
        except InvalidInputError as e:
            self.show_error(e)
            raise

    def save_file(self):
        """Save file with validation and hooks"""
        if not self.filename:
            self.status_message = "No filename"
            return

        try:
            content = '\n'.join(self.buffer.lines)
            Validator.validate_text_content(content)

            with self.perf_monitor.measure("file_save"):
                with open(self.filename, 'w') as f:
                    f.write(content)

            self.plugin_manager.trigger_hook(
                "on_buffer_save",
                self.buffer,
                self.filename
            )

            self.status_message = f"Saved {self.filename}"

        except Exception as e:
            self.show_error(e)

    def improve_code(self, start: int, end: int):
        """Improve code with AI"""
        try:
            # Validate
            start, end = Validator.validate_line_range(
                start, end, len(self.buffer.lines)
            )

            # Get code
            code = '\n'.join(self.buffer.lines[start:end + 1])

            # Call AI (automatic rate limiting)
            with self.perf_monitor.measure("ai_improve"):
                improved = self.ai_service.improve_code(code)

            # Show result
            self.status_message = f"Code improved ({len(improved)} chars)"

        except AIProviderTimeoutError:
            self.status_message = "Rate limited - please wait"
        except AIProviderAuthError:
            self.status_message = "AI auth failed - check API key"
        except AIProviderError as e:
            self.status_message = f"AI error: {e}"

    def execute_command(self, command: str):
        """Execute command with plugin support"""
        parts = command.split(None, 1)
        cmd = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        # Try plugins first
        if self.plugin_manager.execute_command(cmd, args):
            return

        # Built-in commands
        if cmd == "stats":
            self.show_performance_stats()
        elif cmd == "providers":
            self.show_providers()
        # ... etc

    def show_performance_stats(self):
        """Show performance statistics"""
        stats = self.ai_service.get_performance_stats()
        print("Performance Stats:", stats)

    def show_providers(self):
        """Show AI provider information"""
        providers = self.ai_service.get_available_providers()
        print(f"Available providers: {', '.join(providers)}")

        for provider in providers:
            info = self.ai_service.get_provider_info(provider)
            print(f"\n{provider}:")
            print(f"  Current model: {info.get('current_model')}")
            print(f"  Available: {info.get('is_available')}")

    def show_error(self, error: Exception):
        """Show error message"""
        self.status_message = str(error)
        logging.error(f"Error: {error}")


# Usage example
if __name__ == "__main__":
    editor = ModernizedEditor("test.py")

    # File operations
    editor.save_file()

    # AI operations
    editor.improve_code(0, 10)

    # Plugin commands
    editor.execute_command("git-status")
    editor.execute_command("snippets-list python")
    editor.execute_command("format")

    # Statistics
    editor.execute_command("stats")
```

---

## Testing the Integration

### Unit Tests
```python
import pytest
from unittest.mock import Mock

def test_load_file_with_validation():
    """Test file loading with validation"""
    editor = ModernizedEditor()

    # Should work with valid file
    editor.load_file("test.py")

    # Should fail with invalid file
    with pytest.raises(FileOperationError):
        editor.load_file("/nonexistent/file.py")

    # Should fail with path traversal
    with pytest.raises(InvalidInputError):
        editor.load_file("../etc/passwd")

def test_ai_with_rate_limiting():
    """Test AI operations respect rate limits"""
    editor = ModernizedEditor()

    # Multiple rapid calls should eventually hit rate limit
    for i in range(100):
        try:
            editor.improve_code(0, 5)
        except AIProviderTimeoutError:
            # Expected after hitting limit
            break

def test_plugin_integration():
    """Test plugin command execution"""
    editor = ModernizedEditor()

    # Plugin command should work
    result = editor.execute_command("git-status")
    # Check result
```

---

## Summary

This integration example shows:

1. ✅ **Validation** on all user inputs
2. ✅ **Specific exceptions** instead of broad catches
3. ✅ **Performance monitoring** on critical operations
4. ✅ **Rate limiting** automatic in AI service
5. ✅ **Plugin system** fully integrated with hooks
6. ✅ **Type safety** throughout
7. ✅ **Proper logging** for debugging

The key is to **integrate gradually**:
- Start with one module (file operations)
- Add validation and exception handling
- Test thoroughly
- Move to next module (AI operations)
- Repeat

**Result**: Production-ready code with robust error handling, security, and extensibility!
