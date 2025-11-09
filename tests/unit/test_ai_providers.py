"""
Unit tests for AI provider implementations
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from aivim.ai import AIProvider, ProviderFactory
from aivim.ai.openai_provider import OpenAIProvider
from aivim.ai.anthropic_provider import AnthropicProvider
from aivim.ai.local_provider import LocalLLMProvider
from aivim.exceptions import (
    AIProviderError,
    AIProviderNotAvailableError,
    AIProviderAuthError,
    AIProviderTimeoutError,
)


class TestProviderFactory:
    """Test provider factory"""

    def test_register_provider(self):
        """Test provider registration"""
        # Create mock provider
        class MockProvider(AIProvider):
            def get_completion(self, prompt, context=None, **kwargs):
                return "test"

            def get_models(self):
                return []

            def set_model(self, model_id):
                return True

            def get_current_model(self):
                return "test"

            def is_available(self):
                return True

            def validate_config(self):
                return {"valid": True, "errors": [], "warnings": []}

            def get_provider_name(self):
                return "Mock"

        # Register
        ProviderFactory.register_provider("test", MockProvider)

        # Check registered
        assert "test" in ProviderFactory.get_available_providers()

    def test_create_provider_invalid(self):
        """Test creating invalid provider"""
        from aivim.exceptions import InvalidInputError

        with pytest.raises(InvalidInputError):
            ProviderFactory.create_provider("nonexistent")


class TestOpenAIProvider:
    """Test OpenAI provider"""

    def test_init_no_api_key(self):
        """Test initialization without API key"""
        provider = OpenAIProvider(config={})

        assert not provider.is_available()
        validation = provider.validate_config()
        assert not validation['valid']
        assert any('API key' in err for err in validation['errors'])

    def test_get_models(self):
        """Test getting available models"""
        provider = OpenAIProvider(config={'api_key': 'test-key'})

        models = provider.get_models()

        assert len(models) > 0
        assert any(m['id'] == 'gpt-4o' for m in models)
        assert any(m['id'] == 'gpt-3.5-turbo' for m in models)

    def test_set_model(self):
        """Test setting model"""
        provider = OpenAIProvider(config={'api_key': 'test-key'})

        # Valid model
        assert provider.set_model('gpt-4o')
        assert provider.get_current_model() == 'gpt-4o'

        # Invalid model
        assert not provider.set_model('invalid-model')

    def test_get_provider_name(self):
        """Test getting provider name"""
        provider = OpenAIProvider(config={'api_key': 'test-key'})
        assert provider.get_provider_name() == "OpenAI"

    @patch('aivim.ai.openai_provider.OPENAI_AVAILABLE', True)
    @patch('aivim.ai.openai_provider.OpenAI')
    def test_get_completion_success(self, mock_openai_class):
        """Test successful completion"""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Create provider
        provider = OpenAIProvider(config={'api_key': 'test-key'})
        provider.client = mock_client

        # Test completion
        response = provider.get_completion("Test prompt")

        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()

    def test_get_completion_not_available(self):
        """Test completion when provider not available"""
        provider = OpenAIProvider(config={})

        with pytest.raises(AIProviderNotAvailableError):
            provider.get_completion("Test")


class TestAnthropicProvider:
    """Test Anthropic provider"""

    def test_init_no_api_key(self):
        """Test initialization without API key"""
        provider = AnthropicProvider(config={})

        assert not provider.is_available()
        validation = provider.validate_config()
        assert not validation['valid']

    def test_get_models(self):
        """Test getting available models"""
        provider = AnthropicProvider(config={'api_key': 'test-key'})

        models = provider.get_models()

        assert len(models) > 0
        assert any('claude-3-5-sonnet' in m['id'] for m in models)
        assert any('opus' in m['id'].lower() for m in models)

    def test_set_model(self):
        """Test setting model"""
        provider = AnthropicProvider(config={'api_key': 'test-key'})

        # Valid model
        assert provider.set_model('claude-3-5-sonnet-20241022')
        assert provider.get_current_model() == 'claude-3-5-sonnet-20241022'

    def test_get_provider_name(self):
        """Test getting provider name"""
        provider = AnthropicProvider(config={'api_key': 'test-key'})
        assert provider.get_provider_name() == "Anthropic"

    @patch('aivim.ai.anthropic_provider.ANTHROPIC_AVAILABLE', True)
    @patch('aivim.ai.anthropic_provider.Anthropic')
    def test_get_completion_success(self, mock_anthropic_class):
        """Test successful completion"""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_block = Mock(text="Test response")
        mock_response = Mock(content=[mock_block])
        mock_client.messages.create.return_value = mock_response

        # Create provider
        provider = AnthropicProvider(config={'api_key': 'test-key'})
        provider.client = mock_client

        # Test completion
        response = provider.get_completion("Test prompt")

        assert response == "Test response"
        mock_client.messages.create.assert_called_once()


class TestLocalLLMProvider:
    """Test Local LLM provider"""

    def test_init_no_model_path(self):
        """Test initialization without model path"""
        provider = LocalLLMProvider(config={})

        assert not provider.is_available()
        validation = provider.validate_config()
        assert not validation['valid']
        assert any('model path' in err.lower() for err in validation['errors'])

    def test_get_models_no_model(self):
        """Test getting models when no model loaded"""
        provider = LocalLLMProvider(config={})

        models = provider.get_models()
        assert len(models) == 0

    def test_get_provider_name(self):
        """Test getting provider name"""
        provider = LocalLLMProvider(config={})
        assert provider.get_provider_name() == "LocalLLM"

    def test_validate_config(self):
        """Test configuration validation"""
        provider = LocalLLMProvider(config={})

        validation = provider.validate_config()

        assert not validation['valid']
        assert 'errors' in validation
        assert 'warnings' in validation

    @patch('aivim.ai.local_provider.LLAMA_AVAILABLE', False)
    def test_not_available_no_package(self):
        """Test provider not available when package missing"""
        provider = LocalLLMProvider(config={'model_path': '/tmp/model.gguf'})

        validation = provider.validate_config()

        assert not validation['valid']
        assert any('llama-cpp-python' in err for err in validation['errors'])


class TestProviderConcreteMethod(s):
    """Test concrete methods provided by AIProvider base class"""

    class TestProvider(AIProvider):
        """Test provider implementation"""

        def __init__(self):
            super().__init__()
            self.completion_called = False

        def get_completion(self, prompt, context=None, **kwargs):
            self.completion_called = True
            return f"Response to: {prompt}"

        def get_models(self):
            return [{"id": "test", "name": "Test", "description": "Test model"}]

        def set_model(self, model_id):
            return True

        def get_current_model(self):
            return "test"

        def is_available(self):
            return True

        def validate_config(self):
            return {"valid": True, "errors": [], "warnings": []}

        def get_provider_name(self):
            return "Test"

    def test_explain_code(self):
        """Test explain_code concrete method"""
        provider = self.TestProvider()

        result = provider.explain_code("def foo(): pass")

        assert provider.completion_called
        assert "def foo()" in result

    def test_improve_code(self):
        """Test improve_code concrete method"""
        provider = self.TestProvider()

        result = provider.improve_code("x = 1")

        assert provider.completion_called
        assert "x = 1" in result

    def test_generate_code(self):
        """Test generate_code concrete method"""
        provider = self.TestProvider()

        result = provider.generate_code("function to add two numbers")

        assert provider.completion_called
        assert "function to add" in result

    def test_analyze_code(self):
        """Test analyze_code concrete method"""
        provider = self.TestProvider()

        result = provider.analyze_code("def risky(): eval(input())")

        assert provider.completion_called
        assert "risky" in result

    def test_translate_nlp(self):
        """Test translate_nlp concrete method"""
        provider = self.TestProvider()

        result = provider.translate_nlp("create a list of numbers from 1 to 10")

        assert provider.completion_called
        assert "list of numbers" in result
