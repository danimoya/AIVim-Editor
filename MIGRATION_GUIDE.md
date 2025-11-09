# AIVim Migration Guide: Old to New Architecture

**Date**: November 9, 2025
**Purpose**: Guide for migrating from `ai_service.py` to `ai_service_v2.py`

---

## Overview

This guide explains how to migrate from the old `AIService` class to the new provider-based architecture. The new system provides:

- ✅ **Better Architecture**: Provider ABC with clean interfaces
- ✅ **Rate Limiting**: Automatic per-provider rate limiting
- ✅ **Input Validation**: Comprehensive validation of all inputs
- ✅ **Better Errors**: Specific exceptions instead of broad catches
- ✅ **Performance Monitoring**: Built-in performance tracking
- ✅ **Type Safety**: Full type hints throughout

---

## Quick Migration

### Option 1: Drop-in Replacement (Minimal Changes)

The new `AIService` is mostly backward compatible with the old one:

```python
# OLD
from aivim.ai_service import AIService

service = AIService()
response = service.get_improvement(code, context)

# NEW
from aivim.ai_service_v2 import AIService

service = AIService()
response = service.improve_code(code, context)  # Method name changed
```

**Method Name Mapping**:
- `get_improvement()` → `improve_code()`
- `get_explanation()` → `explain_code()`
- `get_analysis()` → `analyze_code()`
- `generate_code()` → `generate_code()` (same)
- `query()` → `get_completion()`

### Option 2: Full Migration (Recommended)

Take advantage of new features:

```python
from aivim.ai_service_v2 import AIService
from aivim.exceptions import AIProviderError, AIProviderTimeoutError

# Initialize with config
service = AIService(config_path="~/.aivim/config")

# Check what providers are available
providers = service.get_available_providers()
print(f"Available providers: {providers}")

# Get provider info
info = service.get_provider_info("openai")
print(f"Current model: {info['current_model']}")

# Use with error handling
try:
    response = service.improve_code(
        code,
        context="Python function for data processing",
        provider="claude"  # Can specify provider
    )
except AIProviderTimeoutError as e:
    print(f"Rate limited: {e}")
except AIProviderError as e:
    print(f"API error: {e}")

# Get performance stats
stats = service.get_performance_stats()
print(f"Average improve_code time: {stats.get('improve_code_claude', {}).get('avg', 0):.2f}s")

# Get rate limit stats
rate_stats = service.get_rate_limit_stats()
for provider, stats in rate_stats.items():
    print(f"{provider}: {stats['total_requests']} requests, {stats['block_rate']:.1%} blocked")
```

---

## API Changes

### Constructor

**OLD**:
```python
service = AIService()
# Config loaded automatically from default locations
```

**NEW**:
```python
# Same as old
service = AIService()

# Or specify config path
service = AIService(config_path="/custom/path/config")

# Check config status
status = service.get_config_status()
print(status)  # {"loaded": True, "path": "~/.aivim/config", ...}
```

### Switching Providers

**OLD**:
```python
service.current_model = "claude"  # Direct attribute access
```

**NEW**:
```python
# Method with validation
service.set_provider("claude")

# Or use in specific call
response = service.get_completion(prompt, provider="openai")
```

### Getting Available Models

**OLD**:
```python
# Different attributes for each provider
openai_models = service.openai_models
anthropic_models = service.anthropic_models
```

**NEW**:
```python
# Unified interface
info = service.get_provider_info("openai")
models = info['available_models']

# Or from current provider
info = service.get_provider_info()
models = info['available_models']
```

### Error Handling

**OLD**:
```python
try:
    response = service.get_improvement(code)
except Exception as e:  # Broad catch
    print(f"Error: {e}")
```

**NEW**:
```python
from aivim.exceptions import (
    AIProviderError,
    AIProviderAuthError,
    AIProviderTimeoutError,
    AIProviderQuotaError,
)

try:
    response = service.improve_code(code)
except AIProviderAuthError:
    print("Authentication failed - check API key")
except AIProviderQuotaError:
    print("API quota exceeded")
except AIProviderTimeoutError as e:
    print(f"Rate limited - retry after {e.timeout}s")
except AIProviderError as e:
    print(f"API error: {e}")
```

---

## Configuration

### Old Config Format (Still Supported)

```ini
[General]
default_model = openai

[OpenAI]
api_key = sk-...

[Anthropic]
api_key = sk-ant-...

[LocalLLM]
model_path = /path/to/model.gguf
```

### New Config Options (Optional)

```ini
[General]
default_model = claude

[OpenAI]
api_key = sk-...
model = gpt-4o
timeout = 30

[Anthropic]
api_key = sk-ant-...
model = claude-3-5-sonnet-20241022
timeout = 30
max_tokens = 4096

[LocalLLM]
model_path = /path/to/model.gguf
n_ctx = 2048
n_gpu_layers = 35
temperature = 0.7
max_tokens = 512
```

---

## New Features

### 1. Automatic Rate Limiting

The new service automatically rate limits API calls:

```python
service = AIService()

# Rate limits are pre-configured:
# - OpenAI: 60 calls/min (burst: 10)
# - Claude: 100 calls/min (burst: 20)
# - Local: 300 calls/min (burst: 50)

# If rate limit is hit, blocks for up to 10 seconds
# If still no token available, raises AIProviderTimeoutError
response = service.get_completion(prompt)
```

### 2. Performance Monitoring

Built-in performance tracking:

```python
# Make some calls
for _ in range(10):
    service.improve_code(code)

# Get performance stats
stats = service.get_performance_stats()

# Example output:
# {
#   'ai_improve_code_openai': {
#     'count': 10,
#     'min': 0.52,
#     'max': 1.35,
#     'avg': 0.87,
#     'recent': [0.82, 0.91, 0.85, ...]
#   }
# }
```

### 3. Provider Information

Get detailed provider status:

```python
info = service.get_provider_info("openai")

# Example output:
# {
#   'name': 'OpenAI',
#   'current_model': 'gpt-4o',
#   'available_models': [
#     {'id': 'gpt-4o', 'name': 'GPT-4o', ...},
#     ...
#   ],
#   'is_available': True,
#   'config_status': {
#     'valid': True,
#     'errors': [],
#     'warnings': []
#   }
# }
```

### 4. Input Validation

All inputs are validated:

```python
from aivim.exceptions import InvalidInputError

try:
    # Prompt too long
    service.get_completion("x" * 200000)
except InvalidInputError as e:
    print(f"Validation error: {e}")
    # "Content length 200000 exceeds maximum (100000 characters)"
```

---

## Migration Checklist

### Step 1: Import Changes

Replace:
```python
from aivim.ai_service import AIService
```

With:
```python
from aivim.ai_service_v2 import AIService
```

### Step 2: Update Method Calls

Update method names:
- `get_improvement()` → `improve_code()`
- `get_explanation()` → `explain_code()`
- `get_analysis()` → `analyze_code()`
- `query()` → `get_completion()`

### Step 3: Update Error Handling

Replace:
```python
except Exception as e:
```

With:
```python
from aivim.exceptions import AIProviderError

except AIProviderError as e:
```

### Step 4: Update Provider Switching

Replace:
```python
service.current_model = "claude"
```

With:
```python
service.set_provider("claude")
```

### Step 5: Test Thoroughly

Test all AI functionality:
- ✅ Code explanation
- ✅ Code improvement
- ✅ Code generation
- ✅ Code analysis
- ✅ Provider switching
- ✅ Error handling

---

## Backward Compatibility Notes

### What's Compatible

✅ Config file format (same locations and structure)
✅ Environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, LLAMA_MODEL_PATH)
✅ Basic usage pattern (create service, call methods)

### What Changed

⚠️ Method names (get_improvement → improve_code, etc.)
⚠️ Exception types (specific exceptions instead of generic)
⚠️ Provider switching (method instead of attribute)
⚠️ Some return types have better structure

### Breaking Changes

❌ Direct attribute access to providers (use methods instead)
❌ Some internal methods removed or renamed
❌ Error handling must catch specific exceptions

---

## Example: Complete Migration

### Before (Old Code)

```python
from aivim.ai_service import AIService

class MyEditor:
    def __init__(self):
        self.ai_service = AIService()
        self.ai_service.current_model = "openai"

    def improve_selection(self, code):
        try:
            improved = self.ai_service.get_improvement(code)
            return improved
        except Exception as e:
            print(f"Error: {e}")
            return None

    def explain_selection(self, code):
        try:
            explanation = self.ai_service.get_explanation(code)
            return explanation
        except Exception as e:
            print(f"Error: {e}")
            return None
```

### After (New Code)

```python
from aivim.ai_service_v2 import AIService
from aivim.exceptions import AIProviderError, AIProviderTimeoutError

class MyEditor:
    def __init__(self):
        self.ai_service = AIService()
        self.ai_service.set_provider("openai")

    def improve_selection(self, code):
        try:
            improved = self.ai_service.improve_code(code)
            return improved
        except AIProviderTimeoutError:
            print("Rate limited - please wait and try again")
            return None
        except AIProviderError as e:
            print(f"AI Error: {e}")
            return None

    def explain_selection(self, code):
        try:
            explanation = self.ai_service.explain_code(code)
            return explanation
        except AIProviderTimeoutError:
            print("Rate limited - please wait and try again")
            return None
        except AIProviderError as e:
            print(f"AI Error: {e}")
            return None

    def get_ai_stats(self):
        """New feature: Get performance stats"""
        stats = self.ai_service.get_performance_stats()
        rate_stats = self.ai_service.get_rate_limit_stats()
        return {
            'performance': stats,
            'rate_limits': rate_stats,
        }
```

---

## Gradual Migration Strategy

You can migrate gradually using both versions:

```python
# Import both
from aivim.ai_service import AIService as OldAIService
from aivim.ai_service_v2 import AIService as NewAIService

# Use new for new features
new_service = NewAIService()

# Keep old for compatibility during transition
old_service = OldAIService()

# Gradually update call sites
response = new_service.improve_code(code)  # Updated
response = old_service.get_explanation(code)  # Not yet updated
```

Then remove old service once migration is complete.

---

## Testing Your Migration

### Unit Tests

Update your unit tests:

```python
import pytest
from aivim.ai_service_v2 import AIService
from aivim.exceptions import AIProviderError

def test_ai_service():
    service = AIService()

    # Should have at least one provider
    assert len(service.get_available_providers()) > 0

    # Should be able to switch providers
    if 'claude' in service.get_available_providers():
        assert service.set_provider('claude')
        assert service.current_provider_name == 'claude'

def test_error_handling():
    service = AIService()

    # Test with invalid input
    with pytest.raises(AIProviderError):
        service.get_completion("")  # Empty prompt
```

### Integration Tests

Test with real API calls (if keys available):

```python
def test_real_improvement():
    service = AIService()

    code = "def add(a, b): return a + b"
    improved = service.improve_code(code)

    assert improved is not None
    assert len(improved) > 0
```

---

## Troubleshooting

### Problem: "No AI providers available"

**Solution**: Check that at least one provider is configured:
```python
service = AIService()
providers = service.get_available_providers()
print(f"Available: {providers}")

for provider in ['openai', 'claude', 'local']:
    if provider in service.providers:
        info = service.get_provider_info(provider)
        print(f"{provider}: {info['config_status']}")
```

### Problem: "Rate limit timeout"

**Solution**: Increase timeout or reduce request rate:
```python
# Option 1: Wait and retry
import time
time.sleep(2)
response = service.get_completion(prompt)

# Option 2: Use different provider
response = service.get_completion(prompt, provider='local')

# Option 3: Check rate limit stats
stats = service.get_rate_limit_stats()
print(stats)  # See which provider is limited
```

### Problem: Method not found

**Solution**: Check method name mapping in this guide. Update to new names.

---

## Support

For issues or questions:
1. Check this migration guide
2. Review `IMPLEMENTATION_GUIDE.md`
3. Check provider validation: `service.get_provider_info(provider)`
4. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

---

**Migration Status**: Ready for Testing
**Backward Compatibility**: High (with minor method name changes)
**Recommended Approach**: Gradual migration with testing

