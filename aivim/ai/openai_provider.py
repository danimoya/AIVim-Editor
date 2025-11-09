"""
OpenAI provider implementation for AIVim
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
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available. Install with: pip install openai")


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OpenAI provider

        Args:
            config: Configuration dictionary with optional keys:
                   - api_key: OpenAI API key
                   - model: Default model to use
                   - timeout: Request timeout in seconds
        """
        super().__init__(config)

        # Get API key from config or environment
        self.api_key = (
            config.get('api_key') if config
            else os.environ.get('OPENAI_API_KEY')
        )

        self.client = None
        self.timeout = config.get('timeout', 30) if config else 30

        # Available models
        self._models = [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "description": "Latest multimodal OpenAI model (May 2024)"
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "description": "Powerful model with good balance of quality and speed"
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "description": "Previous generation flagship model"
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "description": "Fast and efficient language model"
            },
        ]

        # Set default model
        self._current_model = (
            config.get('model', 'gpt-4o') if config
            else 'gpt-4o'
        )

        # Initialize client if available
        if self.api_key and OPENAI_AVAILABLE:
            try:
                # Validate API key format
                Validator.validate_api_key(self.api_key, "OpenAI")
                self.client = OpenAI(api_key=self.api_key, timeout=self.timeout)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise AIProviderError("openai", f"Initialization failed: {e}")

    def get_completion(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ) -> str:
        """
        Get completion from OpenAI

        Args:
            prompt: The prompt to send
            context: Optional context/system message
            **kwargs: Additional OpenAI API parameters (temperature, max_tokens, etc.)

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
                "openai",
                "Provider not configured or OpenAI package not installed"
            )

        # Validate inputs
        try:
            Validator.validate_text_content(prompt, max_length=100000)
            if context:
                Validator.validate_text_content(context, max_length=50000)
        except Exception as e:
            raise AIProviderError("openai", f"Input validation failed: {e}")

        # Build messages
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self._current_model,
                messages=messages,
                **kwargs
            )

            # Validate response
            if not response.choices or len(response.choices) == 0:
                raise AIProviderResponseError(
                    "openai",
                    "No choices in response"
                )

            content = response.choices[0].message.content
            if not content:
                raise AIProviderResponseError(
                    "openai",
                    "Empty content in response"
                )

            logger.debug(f"OpenAI completion successful ({len(content)} chars)")
            return content

        except AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise AIProviderAuthError("openai")

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise AIProviderQuotaError("openai")

        except TimeoutError as e:
            logger.error(f"OpenAI request timeout: {e}")
            raise AIProviderTimeoutError("openai", self.timeout)

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIProviderError("openai", str(e))

        except Exception as e:
            logger.error(f"Unexpected error from OpenAI: {e}")
            raise AIProviderError("openai", f"Unexpected error: {e}")

    def get_models(self) -> List[Dict[str, str]]:
        """Get available OpenAI models"""
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
        logger.info(f"OpenAI model set to: {model_id}")
        return True

    def get_current_model(self) -> Optional[str]:
        """Get current model ID"""
        return self._current_model

    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        return (
            OPENAI_AVAILABLE and
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
        if not OPENAI_AVAILABLE:
            errors.append("openai package not installed (pip install openai)")

        # Check API key
        if not self.api_key:
            errors.append("API key not configured")
        else:
            try:
                Validator.validate_api_key(self.api_key, "OpenAI")
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

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "OpenAI"
