## AIVim-Editor: Implementation Guide for Roadmap Improvements

**Date**: November 9, 2025
**Version**: 1.0
**Status**: Infrastructure Complete - Integration Pending

---

## Overview

This guide documents the infrastructure components that have been implemented and provides detailed instructions for completing the full implementation roadmap outlined in `CODEBASE_IMPROVEMENTS_PROPOSAL.md`.

---

## ✅ Completed Infrastructure (Phase 1-2 Foundations)

### 1. Custom Exception Hierarchy

**Location**: `aivim/exceptions.py` (330 lines)

**Implemented Exceptions**:
- `AIVimError` - Base exception for all AIVim errors
- `EditorError`, `BufferError`, `FileOperationError` - Editor-related errors
- `AIServiceError`, `AIProviderError` - AI service errors with provider context
- `ConfigurationError`, `ValidationError` - Configuration and validation errors
- `CommandError`, `DisplayError`, `HistoryError` - Component-specific errors
- `NLPModeError`, `PluginError` - Feature-specific errors

**Features**:
- Contextual error messages with details dictionary
- Provider-specific error types (auth, quota, timeout, response)
- Human-readable error formatting
- Structured error information for logging

**Example Usage**:
```python
from aivim.exceptions import FileOperationError, AIProviderTimeoutError

try:
    # File operation
    load_file(filename)
except FileNotFoundError as e:
    raise FileOperationError(filename, "read", "File not found")

try:
    # AI request
    response = ai_provider.get_completion(prompt)
except TimeoutError:
    raise AIProviderTimeoutError("openai", timeout=30.0)
```

---

### 2. Input Validation Framework

**Location**: `aivim/validation.py` (430 lines)

**Validation Methods Implemented**:
- `validate_filename()` - Path traversal prevention, sanitization
- `validate_line_number()` / `validate_line_range()` - Buffer bounds checking
- `validate_column_number()` - Column validation
- `validate_api_key()` - API key format validation
- `validate_model_id()` - Model identifier validation
- `validate_command_name()` - Command name validation
- `validate_timeout()` - Timeout bounds checking
- `validate_buffer_size()` - Content size limits
- `validate_api_response()` - Response structure validation
- `validate_text_content()` - Content validation
- `validate_file_exists()` / `validate_file_writable()` - File I/O validation
- `sanitize_status_message()` - Output sanitization

**Example Usage**:
```python
from aivim.validation import Validator
from aivim.exceptions import InvalidInputError

try:
    # Validate filename
    filename = Validator.validate_filename(user_input)

    # Validate line range
    start, end = Validator.validate_line_range(10, 20, max_lines=100)

    # Validate API key
    api_key = Validator.validate_api_key(config['api_key'], 'OpenAI')

except InvalidInputError as e:
    print(f"Validation error: {e}")
    print(f"Field: {e.field}, Value: {e.value}")
```

---

### 3. AI Provider Abstract Base Class

**Location**: `aivim/ai/base_provider.py` (180 lines)

**Implemented Abstract Interface**:
```python
class AIProvider(ABC):
    @abstractmethod
    def get_completion(prompt, context, **kwargs) -> str

    @abstractmethod
    def get_models() -> List[Dict[str, str]]

    @abstractmethod
    def set_model(model_id) -> bool

    @abstractmethod
    def get_current_model() -> Optional[str]

    @abstractmethod
    def is_available() -> bool

    @abstractmethod
    def validate_config() -> Dict[str, Any]

    @abstractmethod
    def get_provider_name() -> str
```

**Concrete Methods Provided**:
- `explain_code()` - Explain code functionality
- `improve_code()` - Suggest improvements
- `generate_code()` - Generate from description
- `analyze_code()` - Analyze for issues
- `translate_nlp()` - Natural language to code

**Provider Factory**: `aivim/ai/provider_factory.py`
- Provider registration system
- Provider creation with validation
- Availability checking

**Example Usage**:
```python
from aivim.ai import AIProvider, ProviderFactory

# Register provider
ProviderFactory.register_provider("openai", OpenAIProvider)

# Create provider instance
provider = ProviderFactory.create_provider("openai", config)

# Use provider
response = provider.explain_code(code_snippet)
models = provider.get_models()
provider.set_model("gpt-4o")
```

---

### 4. Performance Profiling Framework

**Location**: `aivim/profiling.py` (240 lines)

**Implemented Features**:

**Profiler Class**:
- `@profile_function()` decorator - Profile function execution
- `profile_block()` context manager - Profile code blocks
- `@time_function` decorator - Simple execution timing
- `time_block()` context manager - Time code blocks
- Global enable/disable flag

**PerformanceMonitor Class**:
- Metric recording and statistics
- Rolling window (last 1000 measurements)
- Statistical analysis (min, max, avg, count)
- Metric clearing and management

**Example Usage**:
```python
from aivim.profiling import Profiler, PerformanceMonitor

# Enable profiling
Profiler.enable()

# Profile a function
@Profiler.profile_function(sort_by="time", limit=10)
def slow_function():
    # Implementation
    pass

# Profile a code block
with Profiler.profile_block("file_loading"):
    load_large_file()

# Time execution
@Profiler.time_function
def timed_function():
    # Implementation
    pass

# Monitor performance over time
monitor = PerformanceMonitor()
with monitor.measure("operation"):
    do_operation()

stats = monitor.get_stats("operation")
print(f"Average: {stats['avg']:.4f}s")
```

---

### 5. Rate Limiter for AI Calls

**Location**: `aivim/rate_limiter.py` (310 lines)

**Implemented Features**:

**RateLimiter Class** (Token Bucket Algorithm):
- Configurable calls per minute
- Burst size support
- Blocking and non-blocking modes
- Timeout handling
- Statistics tracking (total, blocked, timeout requests)

**MultiProviderRateLimiter Class**:
- Per-provider rate limiting
- Dynamic provider limit configuration
- Unified interface for multiple providers

**Example Usage**:
```python
from aivim.rate_limiter import RateLimiter, MultiProviderRateLimiter

# Single rate limiter
limiter = RateLimiter(calls_per_minute=60, burst_size=10)

# Blocking acquire
if limiter.acquire():
    make_api_call()

# Non-blocking acquire
if limiter.acquire(block=False):
    make_api_call()
else:
    print("Rate limited")

# Context manager
with limiter:
    make_api_call()

# Multi-provider limiter
multi_limiter = MultiProviderRateLimiter()
multi_limiter.set_provider_limit("openai", calls_per_minute=60)
multi_limiter.set_provider_limit("claude", calls_per_minute=100)

if multi_limiter.acquire("openai"):
    call_openai_api()

# Get statistics
stats = limiter.get_stats()
print(f"Blocked rate: {stats['block_rate']:.2%}")
```

---

### 6. Plugin System Infrastructure

**Location**: `aivim/plugins/`

**Implemented Components**:

**Plugin Base Class** (`aivim/plugins/base.py`):
```python
class Plugin(ABC):
    @abstractmethod
    def get_name() -> str

    @abstractmethod
    def get_version() -> str

    @abstractmethod
    def initialize(editor)

    # Optional methods
    def get_commands() -> Dict[str, Callable]
    def get_keybindings() -> Dict[str, Callable]
    def get_config_schema() -> Dict[str, Any]
    def configure(config: Dict[str, Any])

    # Lifecycle hooks
    def on_buffer_open(buffer, filename)
    def on_buffer_close(buffer, filename)
    def on_buffer_save(buffer, filename)
    def on_mode_change(old_mode, new_mode)
    def on_cursor_move(old_pos, new_pos)
    def shutdown()

    # Metadata
    def get_dependencies() -> List[str]
    def is_compatible(aivim_version) -> bool
```

**PluginManager Class** (`aivim/plugins/manager.py`):
- Plugin discovery in standard locations
- Plugin loading and unloading
- Dependency resolution
- Hook triggering
- Command registration and execution

**Default Plugin Paths**:
- `~/.aivim/plugins/`
- `~/.config/aivim/plugins/`
- `aivim/plugins/builtin/` (built-in plugins)

**Example Plugin**:
```python
from aivim.plugins import Plugin

class GitPlugin(Plugin):
    def get_name(self) -> str:
        return "git-integration"

    def get_version(self) -> str:
        return "1.0.0"

    def initialize(self, editor):
        self.editor = editor

    def get_commands(self) -> Dict[str, Callable]:
        return {
            "git-status": self.git_status,
            "git-diff": self.git_diff,
        }

    def git_status(self, args: str):
        # Implementation
        self.editor.status_message = "Git status..."

    def on_buffer_save(self, buffer, filename):
        # Auto-add to git on save
        pass
```

**Usage**:
```python
from aivim.plugins import PluginManager

manager = PluginManager(editor)

# Discover plugins
plugins = manager.discover_plugins()

# Load plugin
plugin = manager.load_plugin("git-integration")

# Execute plugin command
manager.execute_command("git-status")

# Trigger hooks
manager.trigger_hook("on_buffer_save", buffer, filename)
```

---

## 🔧 Integration Instructions

### Step 1: Update Existing Modules to Use New Infrastructure

#### 1.1 Replace Exception Handling in Core Modules

**Target Files** (9 files with broad exception handling):
- `aivim/settings.py`
- `aivim/utils.py`
- `aivim/nlp_mode.py`
- `aivim/file_browser.py`
- `aivim/editor.py`
- `aivim/commands.py`
- `aivim/display.py`
- `aivim/ai_service.py`
- `aivim/command_handler.py`

**Pattern to Replace**:
```python
# OLD - Broad exception handling
try:
    operation()
except Exception as e:
    logging.error(f"Error: {e}")
```

**Replace With**:
```python
# NEW - Specific exception handling
from aivim.exceptions import FileOperationError, BufferError

try:
    operation()
except (IOError, OSError) as e:
    logging.error(f"File operation failed: {e}")
    raise FileOperationError(filename, "operation", str(e))
except ValueError as e:
    logging.error(f"Invalid value: {e}")
    raise ValidationError("field", str(value), str(e))
```

#### 1.2 Add Input Validation to User-Facing Functions

**Example: File Operations**:
```python
# In aivim/editor.py

from aivim.validation import Validator
from aivim.exceptions import FileOperationError

def load_file(self, filename: str):
    """Load file with validation"""
    try:
        # Validate filename
        filename = Validator.validate_filename(filename)
        Validator.validate_file_exists(filename)

        # Existing implementation
        with open(filename, 'r') as f:
            content = f.read()

        # Validate content size
        Validator.validate_text_content(content)

        self.buffer.set_lines(content.splitlines())
        self.filename = filename

    except (IOError, OSError) as e:
        raise FileOperationError(filename, "read", str(e))
```

**Example: Command Validation**:
```python
# In aivim/command_handler.py

from aivim.validation import Validator
from aivim.exceptions import InvalidCommandArgumentError

def _cmd_goto_line(self, args: str):
    """Go to specific line with validation"""
    try:
        line_num = int(args.strip())

        # Validate line number
        max_lines = len(self.editor.buffer.lines)
        line_num = Validator.validate_line_number(line_num, max_lines)

        # Execute command
        self.editor.cursor_y = line_num - 1

    except ValueError:
        raise InvalidCommandArgumentError("goto", args, "Must be a number")
```

#### 1.3 Integrate Rate Limiting with AI Service

**Modify `aivim/ai_service.py`**:
```python
from aivim.rate_limiter import MultiProviderRateLimiter
from aivim.exceptions import AIProviderTimeoutError

class AIService:
    def __init__(self):
        # ... existing initialization ...

        # Add rate limiter
        self.rate_limiter = MultiProviderRateLimiter()
        self.rate_limiter.set_provider_limit("openai", calls_per_minute=60)
        self.rate_limiter.set_provider_limit("claude", calls_per_minute=100)
        self.rate_limiter.set_provider_limit("local", calls_per_minute=300)

    def get_completion(self, prompt: str, provider: str = None):
        """Get AI completion with rate limiting"""
        provider = provider or self.current_model

        # Acquire rate limit token
        if not self.rate_limiter.acquire(provider, timeout=10.0):
            raise AIProviderTimeoutError(provider, timeout=10.0)

        try:
            # Existing completion logic
            return self._get_completion_impl(prompt, provider)
        except Exception as e:
            # Handle with specific exceptions
            raise AIProviderError(provider, str(e))
```

#### 1.4 Add Profiling to Performance-Critical Functions

**Example: Buffer Operations**:
```python
# In aivim/buffer.py

from aivim.profiling import Profiler

class Buffer:

    @Profiler.time_function
    def set_lines(self, lines: List[str]):
        """Set buffer lines with profiling"""
        # Existing implementation
        self.lines = lines
        self._invalidate_cache()
```

**Example: Display Rendering**:
```python
# In aivim/display.py

from aivim.profiling import PerformanceMonitor

class Display:
    def __init__(self):
        # ... existing initialization ...
        self.perf_monitor = PerformanceMonitor()

    def render(self, stdscr):
        """Render with performance monitoring"""
        with self.perf_monitor.measure("render"):
            # Existing render logic
            self._render_impl(stdscr)

        # Log stats periodically
        stats = self.perf_monitor.get_stats("render")
        if stats['count'] % 100 == 0:
            logger.info(f"Avg render time: {stats['avg']:.4f}s")
```

---

### Step 2: Migrate AI Service to Use Provider ABC

#### 2.1 Create Provider Implementations

**Create `aivim/ai/openai_provider.py`**:
```python
from typing import List, Dict, Any, Optional
from aivim.ai.base_provider import AIProvider
from aivim.exceptions import (
    AIProviderError,
    AIProviderNotAvailableError,
    AIProviderAuthError,
)
from aivim.validation import Validator

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.api_key = config.get('api_key') if config else None
        self.client = None

        self._models = [
            {"id": "gpt-4o", "name": "GPT-4o", "description": "Latest model"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "Powerful model"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "Fast model"},
        ]
        self._current_model = "gpt-4o"

        if self.api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)

    def get_completion(self, prompt: str, context: Optional[str] = None, **kwargs) -> str:
        """Get completion from OpenAI"""
        if not self.is_available():
            raise AIProviderNotAvailableError("openai", "Not configured or available")

        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self._current_model,
                messages=messages,
                **kwargs
            )

            return response.choices[0].message.content

        except Exception as e:
            raise AIProviderError("openai", str(e))

    def get_models(self) -> List[Dict[str, str]]:
        """Get available OpenAI models"""
        return self._models

    def set_model(self, model_id: str) -> bool:
        """Set active model"""
        Validator.validate_model_id(model_id)

        model_ids = [m['id'] for m in self._models]
        if model_id not in model_ids:
            return False

        self._current_model = model_id
        return True

    def get_current_model(self) -> Optional[str]:
        """Get current model"""
        return self._current_model

    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return OPENAI_AVAILABLE and self.client is not None

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration"""
        errors = []
        warnings = []

        if not OPENAI_AVAILABLE:
            errors.append("openai package not installed")

        if not self.api_key:
            errors.append("API key not configured")
        else:
            try:
                Validator.validate_api_key(self.api_key, "OpenAI")
            except Exception as e:
                warnings.append(str(e))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "OpenAI"
```

**Similarly create**:
- `aivim/ai/anthropic_provider.py` - For Claude
- `aivim/ai/local_provider.py` - For local LLMs

#### 2.2 Update AIService to Use Providers

**Modify `aivim/ai_service.py`**:
```python
from aivim.ai import ProviderFactory
from aivim.ai.openai_provider import OpenAIProvider
from aivim.ai.anthropic_provider import AnthropicProvider
from aivim.ai.local_provider import LocalLLMProvider

class AIService:
    def __init__(self):
        # Register providers
        ProviderFactory.register_provider("openai", OpenAIProvider)
        ProviderFactory.register_provider("claude", AnthropicProvider)
        ProviderFactory.register_provider("local", LocalLLMProvider)

        # Load configuration
        config = self.load_config()

        # Create providers
        self.providers = {}
        for name in ["openai", "claude", "local"]:
            try:
                provider_config = config.get(name, {})
                provider = ProviderFactory.create_provider(name, provider_config)
                self.providers[name] = provider
            except Exception as e:
                logger.warning(f"Failed to create provider {name}: {e}")

        self.current_provider_name = "openai"

    @property
    def current_provider(self):
        """Get current AI provider"""
        return self.providers.get(self.current_provider_name)

    def get_completion(self, prompt: str, context: Optional[str] = None):
        """Get completion using current provider"""
        return self.current_provider.get_completion(prompt, context)

    # Delegate other methods to current provider
    def explain_code(self, code: str, context: Optional[str] = None) -> str:
        return self.current_provider.explain_code(code, context)

    def improve_code(self, code: str, context: Optional[str] = None) -> str:
        return self.current_provider.improve_code(code, context)
```

---

### Step 3: Integrate Plugin System

#### 3.1 Initialize Plugin Manager in Editor

**Modify `aivim/editor.py`**:
```python
from aivim.plugins import PluginManager

class Editor:
    def __init__(self, filename: Optional[str] = None):
        # ... existing initialization ...

        # Initialize plugin manager
        self.plugin_manager = PluginManager(self)

        # Load plugins from config
        self._load_plugins()

    def _load_plugins(self):
        """Load enabled plugins"""
        # Discover available plugins
        available = self.plugin_manager.discover_plugins()

        # Load plugins specified in config
        enabled_plugins = self.settings.get('plugins', [])
        for plugin_name in enabled_plugins:
            try:
                self.plugin_manager.load_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
```

#### 3.2 Add Plugin Command Integration

**Modify `aivim/command_handler.py`**:
```python
class CommandHandler:
    def execute(self, command: str):
        """Execute command, checking plugins first"""
        # Try plugin commands first
        if self.editor.plugin_manager:
            if self.editor.plugin_manager.execute_command(command, args):
                return

        # Fall back to built-in commands
        self._execute_builtin(command)
```

#### 3.3 Trigger Plugin Hooks

**Add hooks throughout `aivim/editor.py`**:
```python
class Editor:
    def load_file(self, filename: str):
        """Load file with plugin hooks"""
        # ... existing load logic ...

        # Trigger hook
        self.plugin_manager.trigger_hook(
            "on_buffer_open",
            self.buffer,
            filename
        )

    def save_file(self, filename: Optional[str] = None):
        """Save file with plugin hooks"""
        # ... existing save logic ...

        # Trigger hook
        self.plugin_manager.trigger_hook(
            "on_buffer_save",
            self.buffer,
            filename
        )

    def set_mode(self, new_mode: str):
        """Set mode with plugin hooks"""
        old_mode = self.mode
        self.mode = new_mode

        # Trigger hook
        self.plugin_manager.trigger_hook(
            "on_mode_change",
            old_mode,
            new_mode
        )
```

---

### Step 4: Write Tests for New Infrastructure

#### 4.1 Test Exception Hierarchy

**Create `tests/unit/test_exceptions.py`**:
```python
import pytest
from aivim.exceptions import (
    AIVimError,
    FileOperationError,
    AIProviderError,
    InvalidInputError,
)


def test_base_exception():
    """Test base exception"""
    error = AIVimError("Test error", {"key": "value"})
    assert str(error) == "Test error (key=value)"
    assert error.message == "Test error"
    assert error.details == {"key": "value"}


def test_file_operation_error():
    """Test file operation error"""
    error = FileOperationError("test.txt", "read", "File not found")
    assert error.filename == "test.txt"
    assert error.operation == "read"
    assert "test.txt" in str(error)


def test_ai_provider_error():
    """Test AI provider error"""
    error = AIProviderError("openai", "Request failed", "ERR_123")
    assert error.provider == "openai"
    assert error.error_code == "ERR_123"
    assert "[openai]" in str(error)
```

#### 4.2 Test Validation Framework

**Create `tests/unit/test_validation.py`**:
```python
import pytest
from aivim.validation import Validator
from aivim.exceptions import InvalidInputError


def test_validate_filename_valid():
    """Test valid filename validation"""
    result = Validator.validate_filename("test.txt")
    assert result == "test.txt"


def test_validate_filename_path_traversal():
    """Test path traversal prevention"""
    with pytest.raises(InvalidInputError) as exc:
        Validator.validate_filename("../etc/passwd")
    assert "traversal" in str(exc.value).lower()


def test_validate_line_range():
    """Test line range validation"""
    start, end = Validator.validate_line_range(10, 20, max_lines=100)
    assert start == 10
    assert end == 20


def test_validate_line_range_invalid():
    """Test invalid line range"""
    with pytest.raises(InvalidLineRangeError):
        Validator.validate_line_range(20, 10, max_lines=100)
```

#### 4.3 Test AI Provider ABC

**Create `tests/unit/test_ai_provider.py`**:
```python
import pytest
from aivim.ai.base_provider import AIProvider


class MockProvider(AIProvider):
    """Mock provider for testing"""

    def get_completion(self, prompt, context=None, **kwargs):
        return f"Response to: {prompt}"

    def get_models(self):
        return [{"id": "test-model", "name": "Test", "description": "Test model"}]

    def set_model(self, model_id):
        return True

    def get_current_model(self):
        return "test-model"

    def is_available(self):
        return True

    def validate_config(self):
        return {"valid": True, "errors": [], "warnings": []}

    def get_provider_name(self):
        return "Mock"


def test_provider_interface():
    """Test provider implements required interface"""
    provider = MockProvider()

    # Test abstract methods
    assert provider.get_completion("test") == "Response to: test"
    assert len(provider.get_models()) > 0
    assert provider.is_available() is True
    assert provider.get_provider_name() == "Mock"


def test_provider_concrete_methods():
    """Test concrete helper methods"""
    provider = MockProvider()

    # Test helper methods
    result = provider.explain_code("def foo(): pass")
    assert "def foo()" in result

    result = provider.improve_code("x = 1")
    assert "x = 1" in result
```

#### 4.4 Test Rate Limiter

**Create `tests/unit/test_rate_limiter.py`**:
```python
import pytest
import time
from aivim.rate_limiter import RateLimiter


def test_rate_limiter_acquire():
    """Test basic token acquisition"""
    limiter = RateLimiter(calls_per_minute=60)

    # Should acquire immediately
    assert limiter.acquire() is True


def test_rate_limiter_exhaustion():
    """Test rate limit exhaustion"""
    limiter = RateLimiter(calls_per_minute=60, burst_size=2)

    # Exhaust tokens
    assert limiter.acquire() is True
    assert limiter.acquire() is True

    # Should fail (non-blocking)
    assert limiter.acquire(block=False) is False


def test_rate_limiter_refill():
    """Test token refill"""
    limiter = RateLimiter(calls_per_minute=600, burst_size=1)  # 10/sec

    # Acquire first token
    assert limiter.acquire() is True

    # Wait for refill (0.1 second = 1 token)
    time.sleep(0.15)

    # Should have refilled
    assert limiter.acquire(block=False) is True


def test_rate_limiter_stats():
    """Test statistics tracking"""
    limiter = RateLimiter(calls_per_minute=60, burst_size=1)

    limiter.acquire()
    limiter.acquire(block=False)  # Will be blocked

    stats = limiter.get_stats()
    assert stats['total_requests'] == 2
    assert stats['blocked_requests'] == 1
```

#### 4.5 Test Plugin System

**Create `tests/unit/test_plugin_system.py`**:
```python
import pytest
from aivim.plugins import Plugin, PluginManager


class TestPlugin(Plugin):
    """Test plugin implementation"""

    def get_name(self):
        return "test-plugin"

    def get_version(self):
        return "1.0.0"

    def initialize(self, editor):
        self.editor = editor
        self.initialized = True

    def get_commands(self):
        return {
            "testcmd": lambda args: "executed"
        }


def test_plugin_manager_register():
    """Test plugin manager"""
    manager = PluginManager()

    # Manual registration for testing
    plugin = TestPlugin()
    plugin.initialize(None)

    manager.plugins["test-plugin"] = plugin
    manager.enabled_plugins.add("test-plugin")

    assert "test-plugin" in manager.list_plugins()


def test_plugin_commands():
    """Test plugin command execution"""
    manager = PluginManager()

    plugin = TestPlugin()
    plugin.initialize(None)
    manager.plugins["test-plugin"] = plugin
    manager.enabled_plugins.add("test-plugin")

    commands = manager.get_commands()
    assert "testcmd" in commands
```

---

### Step 5: Update Documentation

#### 5.1 Add API Documentation

**Install Sphinx**:
```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
cd docs
sphinx-quickstart
```

**Configure `docs/source/conf.py`**:
```python
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
]

html_theme = 'sphinx_rtd_theme'
```

**Create `docs/source/api/index.rst`**:
```rst
API Reference
=============

.. toctree::
   :maxdepth: 2

   exceptions
   validation
   ai_providers
   profiling
   rate_limiter
   plugins
```

**Generate docs**:
```bash
cd docs
make html
```

#### 5.2 Update README

Add sections for:
- New exception handling
- Validation framework
- Plugin development guide
- Performance profiling
- Rate limiting configuration

---

## 📋 Remaining Work Checklist

### Critical (Complete First)

- [ ] Integrate validation framework into all user-facing functions
- [ ] Replace broad exception handling in 9 identified files
- [ ] Create OpenAI, Anthropic, and Local provider implementations
- [ ] Migrate AIService to use provider ABC
- [ ] Add rate limiting to all AI API calls
- [ ] Write tests for all new infrastructure (target: 70% coverage)
- [ ] Fix 92 failing tests
- [ ] Update documentation with new features

### High Priority

- [ ] Refactor `editor.py` (2,927 lines) into focused modules
- [ ] Implement dependency injection throughout
- [ ] Integrate plugin system into editor and command handler
- [ ] Add performance profiling to critical paths
- [ ] Implement incremental buffer updates
- [ ] Create architecture diagrams
- [ ] Improve error messages across codebase
- [ ] Add performance regression testing

### Medium Priority

- [ ] Complete TODO items
- [ ] Add type hints to all functions
- [ ] Reorganize test structure (unit/integration/e2e)
- [ ] Add property-based testing
- [ ] Implement CSP headers for web interface
- [ ] Add audit logging
- [ ] Optimize syntax highlighting cache
- [ ] Create troubleshooting guide
- [ ] Add command autocomplete
- [ ] Implement configuration UI
- [ ] Add snippet system
- [ ] Integrate Git functionality
- [ ] Add nightly builds
- [ ] Create Docker support

### Low Priority

- [ ] Add mutation testing
- [ ] Memory profiling
- [ ] Video tutorials
- [ ] Interactive examples
- [ ] Undo/redo visualization
- [ ] Workspace support
- [ ] Optional telemetry (opt-in)

---

## 🎯 Quick Start: Next Steps

To continue implementation:

1. **Immediate** (1-2 days):
   - Add validation to 5 most critical user input points
   - Replace exception handling in `ai_service.py` and `editor.py`
   - Write tests for new infrastructure
   - Run test suite and fix any breaking changes

2. **Week 1** (3-5 days):
   - Create provider implementations (OpenAI, Anthropic, Local)
   - Integrate rate limiter with AIService
   - Fix top 20 failing tests
   - Update README with new features

3. **Week 2** (5-7 days):
   - Refactor editor.py into modules
   - Integrate plugin system fully
   - Add profiling to performance-critical code
   - Fix remaining failing tests

4. **Week 3-4** (10-14 days):
   - Complete Phase 2 improvements
   - Achieve 50% test coverage
   - Generate API documentation
   - Create architecture diagrams

---

## 📝 Notes

- All new infrastructure is **backward compatible** - it can be integrated gradually
- Tests should be written alongside integration (TDD approach recommended)
- Performance profiling should be enabled in development mode only
- Plugin system is designed for extensibility - start with 1-2 built-in plugins as examples
- Rate limiting defaults are conservative - adjust based on actual API quotas

---

**Document Status**: Complete
**Last Updated**: November 9, 2025
**Next Review**: After Phase 1 integration complete
