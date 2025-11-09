"""
Anthropic Claude provider implementation for AIVim
"""
import logging
import os
from typing import List, Dict, Any, Optional

from .base_provider import AIProvider
from ..exceptions import (
    AIProviderError,
    AIProviderNotAvailableError,
    AIProviderAuthError,
    AIProviderTimeoutError,
    AIProviderQuotaError,
    AIProviderResponseError,
)
from ..validation import Validator

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic, APIError, AuthenticationError, RateLimitError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic package not available. Install with: pip install anthropic")


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider implementation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Anthropic provider

        Args:
            config: Configuration dictionary with optional keys:
                   - api_key: Anthropic API key
                   - model: Default model to use
                   - timeout: Request timeout in seconds
                   - max_tokens: Maximum tokens in response
        """
        super().__init__(config)

        # Get API key from config or environment
        self.api_key = (
            config.get('api_key') if config
            else os.environ.get('ANTHROPIC_API_KEY')
        )

        self.client = None
        self.timeout = config.get('timeout', 30) if config else 30
        self.max_tokens = config.get('max_tokens', 4096) if config else 4096

        # Available models
        self._models = [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "description": "Latest Claude model (Oct 2024)"
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "Most powerful Claude model"
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "description": "Balance of intelligence and speed"
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Fast, efficient model"
            },
        ]

        # Set default model
        self._current_model = (
            config.get('model', 'claude-3-5-sonnet-20241022') if config
            else 'claude-3-5-sonnet-20241022'
        )

        # Initialize client if available
        if self.api_key and ANTHROPIC_AVAILABLE:
            try:
                # Validate API key format
                Validator.validate_api_key(self.api_key, "Anthropic")
                self.client = Anthropic(
                    api_key=self.api_key,
                    timeout=self.timeout
                )
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                raise AIProviderError("anthropic", f"Initialization failed: {e}")

    def get_completion(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ) -> str:
        """
        Get completion from Anthropic Claude

        Args:
            prompt: The prompt to send
            context: Optional context/system message
            **kwargs: Additional Anthropic API parameters

        Returns:
            The AI's response

        Raises:
            AIProviderNotAvailableError: If provider is not available
            AIProviderAuthError: If authentication fails
            AIProviderQuotaError: If quota is exceeded
            AIProviderTimeoutError: If request times out
            AIProviderResponseError: If response is invalid
        """
        if not self.is_available():
            raise AIProviderNotAvailableError(
                "anthropic",
                "Provider not configured or Anthropic package not installed"
            )

        # Validate inputs
        try:
            Validator.validate_text_content(prompt, max_length=100000)
            if context:
                Validator.validate_text_content(context, max_length=50000)
        except Exception as e:
            raise AIProviderError("anthropic", f"Input validation failed: {e}")

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Get max_tokens from kwargs or use default
        max_tokens = kwargs.pop('max_tokens', self.max_tokens)

        try:
            # Make API call
            # Anthropic uses system parameter separately
            response = self.client.messages.create(
                model=self._current_model,
                max_tokens=max_tokens,
                system=context if context else None,
                messages=messages,
                **kwargs
            )

            # Validate response
            if not response.content or len(response.content) == 0:
                raise AIProviderResponseError(
                    "anthropic",
                    "No content in response"
                )

            # Extract text from content blocks
            content_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content_text += block.text

            if not content_text:
                raise AIProviderResponseError(
                    "anthropic",
                    "Empty content in response"
                )

            logger.debug(f"Anthropic completion successful ({len(content_text)} chars)")
            return content_text

        except AuthenticationError as e:
            logger.error(f"Anthropic authentication failed: {e}")
            raise AIProviderAuthError("anthropic")

        except RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            raise AIProviderQuotaError("anthropic")

        except TimeoutError as e:
            logger.error(f"Anthropic request timeout: {e}")
            raise AIProviderTimeoutError("anthropic", self.timeout)

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise AIProviderError("anthropic", str(e))

        except Exception as e:
            logger.error(f"Unexpected error from Anthropic: {e}")
            raise AIProviderError("anthropic", f"Unexpected error: {e}")

    def get_models(self) -> List[Dict[str, str]]:
        """Get available Anthropic models"""
        return self._models

    def set_model(self, model_id: str) -> bool:
        """
        Set active model

        Args:
            model_id: Model ID to activate

        Returns:
            True if successful

        Raises:
            InvalidInputError: If model_id is invalid
        """
        # Validate model ID
        Validator.validate_model_id(model_id)

        # Check if model exists
        model_ids = [m['id'] for m in self._models]
        if model_id not in model_ids:
            logger.warning(
                f"Model '{model_id}' not in known models. "
                f"Available: {', '.join(model_ids)}"
            )
            return False

        self._current_model = model_id
        logger.info(f"Anthropic model set to: {model_id}")
        return True

    def get_current_model(self) -> Optional[str]:
        """Get current model ID"""
        return self._current_model

    def is_available(self) -> bool:
        """Check if Anthropic provider is available"""
        return (
            ANTHROPIC_AVAILABLE and
            self.client is not None and
            self.api_key is not None
        )

    def validate_config(self) -> Dict[str, Any]:
        """
        Validate provider configuration

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Check if package is installed
        if not ANTHROPIC_AVAILABLE:
            errors.append("anthropic package not installed (pip install anthropic)")

        # Check API key
        if not self.api_key:
            errors.append("API key not configured")
        else:
            try:
                Validator.validate_api_key(self.api_key, "Anthropic")
            except Exception as e:
                warnings.append(f"API key validation warning: {e}")

        # Check timeout
        try:
            Validator.validate_timeout(self.timeout)
        except Exception as e:
            warnings.append(f"Invalid timeout: {e}")

        # Check model
        if self._current_model:
            model_ids = [m['id'] for m in self._models]
            if self._current_model not in model_ids:
                warnings.append(
                    f"Unknown model '{self._current_model}'. "
                    f"Available: {', '.join(model_ids)}"
                )

        # Check max_tokens
        if self.max_tokens < 1 or self.max_tokens > 100000:
            warnings.append(f"max_tokens should be between 1 and 100000, got {self.max_tokens}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Anthropic"
