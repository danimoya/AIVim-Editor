"""
Local LLM provider implementation for AIVim using llama-cpp-python
"""
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base_provider import AIProvider
from ..exceptions import (
    AIProviderError,
    AIProviderNotAvailableError,
    AIProviderTimeoutError,
    AIProviderResponseError,
)
from ..validation import Validator

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("llama-cpp-python not available. Install with: pip install llama-cpp-python")


class LocalLLMProvider(AIProvider):
    """Local LLM provider using llama.cpp"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Local LLM provider

        Args:
            config: Configuration dictionary with optional keys:
                   - model_path: Path to GGUF model file
                   - n_ctx: Context window size (default: 2048)
                   - n_gpu_layers: Number of layers to offload to GPU (default: 0)
                   - temperature: Sampling temperature (default: 0.7)
                   - max_tokens: Maximum tokens in response (default: 512)
        """
        super().__init__(config)

        # Get model path from config or environment
        self.model_path = (
            config.get('model_path') if config
            else os.environ.get('LLAMA_MODEL_PATH')
        )

        self.llm = None
        self.n_ctx = config.get('n_ctx', 2048) if config else 2048
        self.n_gpu_layers = config.get('n_gpu_layers', 0) if config else 0
        self.temperature = config.get('temperature', 0.7) if config else 0.7
        self.max_tokens = config.get('max_tokens', 512) if config else 512

        # Model metadata (populated when model is loaded)
        self._current_model = None
        self._models = []

        # Initialize model if path is provided
        if self.model_path and LLAMA_AVAILABLE:
            try:
                self._load_model()
            except Exception as e:
                logger.error(f"Failed to load local model: {e}")
                # Don't raise - allow provider to exist even if model not loaded

    def _load_model(self):
        """Load the local LLM model"""
        if not self.model_path:
            raise AIProviderError("local", "No model path configured")

        # Validate model path
        model_path = Path(self.model_path).expanduser()
        if not model_path.exists():
            raise AIProviderError(
                "local",
                f"Model file not found: {model_path}"
            )

        logger.info(f"Loading local model from: {model_path}")

        try:
            self.llm = Llama(
                model_path=str(model_path),
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )

            # Set current model to filename
            self._current_model = model_path.name
            self._models = [{
                "id": model_path.name,
                "name": model_path.stem,
                "description": f"Local model from {model_path.name}"
            }]

            logger.info(f"Successfully loaded local model: {self._current_model}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise AIProviderError("local", f"Model loading failed: {e}")

    def get_completion(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ) -> str:
        """
        Get completion from local LLM

        Args:
            prompt: The prompt to send
            context: Optional context/system message
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            The AI's response

        Raises:
            AIProviderNotAvailableError: If provider is not available
            AIProviderTimeoutError: If generation takes too long
            AIProviderResponseError: If response is invalid
        """
        if not self.is_available():
            raise AIProviderNotAvailableError(
                "local",
                "Model not loaded or llama-cpp-python not installed"
            )

        # Validate inputs
        try:
            Validator.validate_text_content(prompt, max_length=50000)
            if context:
                Validator.validate_text_content(context, max_length=20000)
        except Exception as e:
            raise AIProviderError("local", f"Input validation failed: {e}")

        # Build full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"

        # Get parameters
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)

        try:
            # Generate completion
            logger.debug(f"Generating completion (max_tokens={max_tokens})")

            response = self.llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=kwargs.get('stop', None),
                echo=False,
            )

            # Extract text from response
            if not response or 'choices' not in response:
                raise AIProviderResponseError(
                    "local",
                    "Invalid response structure"
                )

            if len(response['choices']) == 0:
                raise AIProviderResponseError(
                    "local",
                    "No choices in response"
                )

            text = response['choices'][0].get('text', '')
            if not text:
                raise AIProviderResponseError(
                    "local",
                    "Empty text in response"
                )

            logger.debug(f"Local LLM completion successful ({len(text)} chars)")
            return text.strip()

        except TimeoutError as e:
            logger.error(f"Local LLM timeout: {e}")
            raise AIProviderTimeoutError("local", 30.0)

        except Exception as e:
            logger.error(f"Unexpected error from local LLM: {e}")
            raise AIProviderError("local", f"Generation failed: {e}")

    def get_models(self) -> List[Dict[str, str]]:
        """Get available local models"""
        return self._models if self._models else []

    def set_model(self, model_id: str) -> bool:
        """
        Set active model (reload with new model file)

        Args:
            model_id: Path to model file

        Returns:
            True if successful

        Note:
            For local models, this reloads the model from the specified path
        """
        try:
            # Treat model_id as a file path
            self.model_path = model_id
            self._load_model()
            logger.info(f"Local model switched to: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch local model: {e}")
            return False

    def get_current_model(self) -> Optional[str]:
        """Get current model ID"""
        return self._current_model

    def is_available(self) -> bool:
        """Check if local LLM provider is available"""
        return (
            LLAMA_AVAILABLE and
            self.llm is not None
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
        if not LLAMA_AVAILABLE:
            errors.append("llama-cpp-python not installed (pip install llama-cpp-python)")

        # Check model path
        if not self.model_path:
            errors.append("Model path not configured")
        else:
            model_path = Path(self.model_path).expanduser()
            if not model_path.exists():
                errors.append(f"Model file not found: {model_path}")
            elif not model_path.is_file():
                errors.append(f"Model path is not a file: {model_path}")
            elif not model_path.suffix.lower() in ['.gguf', '.ggml', '.bin']:
                warnings.append(
                    f"Model file extension '{model_path.suffix}' may not be compatible. "
                    "Expected .gguf, .ggml, or .bin"
                )

        # Check parameters
        if self.n_ctx < 128 or self.n_ctx > 32768:
            warnings.append(f"n_ctx should be between 128 and 32768, got {self.n_ctx}")

        if self.temperature < 0 or self.temperature > 2:
            warnings.append(f"temperature should be between 0 and 2, got {self.temperature}")

        if self.max_tokens < 1 or self.max_tokens > 8192:
            warnings.append(f"max_tokens should be between 1 and 8192, got {self.max_tokens}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "LocalLLM"

    def unload_model(self):
        """Unload the current model to free memory"""
        if self.llm is not None:
            logger.info("Unloading local model")
            del self.llm
            self.llm = None
            self._current_model = None
            self._models = []
