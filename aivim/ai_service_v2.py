"""
AIService using the new provider architecture with rate limiting and validation

This is the modernized version that integrates:
- Provider ABC architecture
- Rate limiting
- Input validation
- Proper exception handling
- Performance monitoring
"""
import logging
import os
import configparser
from typing import Optional, Dict, Any, List
from pathlib import Path

from .ai import (
    AIProvider,
    ProviderFactory,
    OpenAIProvider,
    AnthropicProvider,
    LocalLLMProvider,
)
from .rate_limiter import MultiProviderRateLimiter
from .validation import Validator
from .exceptions import (
    AIServiceError,
    AIProviderError,
    AIProviderNotAvailableError,
    ConfigurationError,
    InvalidConfigError,
)
from .profiling import PerformanceMonitor

logger = logging.getLogger(__name__)


class AIService:
    """
    Modernized AI service with provider architecture

    Features:
    - Multiple AI providers (OpenAI, Anthropic, Local LLM)
    - Automatic rate limiting per provider
    - Input validation
    - Proper exception handling
    - Performance monitoring
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AI service

        Args:
            config_path: Optional path to config file
        """
        # Performance monitoring
        self.perf_monitor = PerformanceMonitor()

        # Rate limiter for all providers
        self.rate_limiter = MultiProviderRateLimiter()
        self._setup_rate_limits()

        # Provider registry
        self.providers: Dict[str, AIProvider] = {}
        self.current_provider_name = "openai"  # Default

        # Configuration
        self.config_path = config_path
        self.config_status = {"loaded": False, "path": None, "message": "Not loaded"}

        # Register providers
        self._register_providers()

        # Load configuration
        config = self.load_config(config_path)

        # Initialize providers
        self._initialize_providers(config)

        logger.info(
            f"AIService initialized with {len(self.providers)} providers: "
            f"{', '.join(self.providers.keys())}"
        )

    def _register_providers(self):
        """Register all available provider classes"""
        ProviderFactory.register_provider("openai", OpenAIProvider)
        ProviderFactory.register_provider("claude", AnthropicProvider)
        ProviderFactory.register_provider("local", LocalLLMProvider)

        logger.debug("Registered 3 AI providers")

    def _setup_rate_limits(self):
        """Setup rate limits for each provider"""
        # Configure rate limits (calls per minute)
        self.rate_limiter.set_provider_limit("openai", calls_per_minute=60, burst_size=10)
        self.rate_limiter.set_provider_limit("claude", calls_per_minute=100, burst_size=20)
        self.rate_limiter.set_provider_limit("local", calls_per_minute=300, burst_size=50)

        logger.debug("Rate limits configured for all providers")

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file

        Args:
            config_path: Optional specific config file path

        Returns:
            Configuration dictionary
        """
        config = configparser.ConfigParser()
        config_dict = {}

        # Check for config files in common locations
        if config_path:
            config_paths = [config_path]
        else:
            config_paths = [
                os.path.expanduser("~/.aivim/config"),
                os.path.expanduser("~/.config/aivim/config"),
                os.path.expanduser("~/.aivimrc"),
                "./aivim.config"
            ]

        config_found = False
        for path in config_paths:
            if os.path.exists(path):
                try:
                    config.read(path)
                    config_found = True
                    self.config_status = {
                        "loaded": True,
                        "path": path,
                        "message": f"Config loaded from {path}"
                    }
                    logger.info(f"Loaded config from {path}")

                    # Extract provider configurations
                    for section in ['General', 'OpenAI', 'Anthropic', 'LocalLLM']:
                        if section in config:
                            config_dict[section.lower()] = dict(config[section])

                    # Set default provider if specified
                    if 'general' in config_dict and 'default_model' in config_dict['general']:
                        self.current_provider_name = config_dict['general']['default_model'].lower()

                    break

                except Exception as e:
                    logger.error(f"Error loading config from {path}: {e}")
                    self.config_status = {
                        "loaded": False,
                        "path": path,
                        "message": f"Error: {e}"
                    }

        if not config_found:
            logger.info("No config file found, using environment variables")
            self.config_status = {
                "loaded": False,
                "path": None,
                "message": "Using environment variables"
            }

        return config_dict

    def _initialize_providers(self, config: Dict[str, Any]):
        """
        Initialize all available providers

        Args:
            config: Configuration dictionary
        """
        # Initialize OpenAI
        try:
            openai_config = config.get('openai', {})
            if not openai_config.get('api_key'):
                openai_config['api_key'] = os.environ.get('OPENAI_API_KEY')

            provider = ProviderFactory.create_provider('openai', openai_config)
            self.providers['openai'] = provider
            logger.info("OpenAI provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")

        # Initialize Anthropic
        try:
            anthropic_config = config.get('anthropic', {})
            if not anthropic_config.get('api_key'):
                anthropic_config['api_key'] = os.environ.get('ANTHROPIC_API_KEY')

            provider = ProviderFactory.create_provider('claude', anthropic_config)
            self.providers['claude'] = provider
            logger.info("Anthropic provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic provider: {e}")

        # Initialize Local LLM
        try:
            local_config = config.get('localllm', {})
            if not local_config.get('model_path'):
                local_config['model_path'] = os.environ.get('LLAMA_MODEL_PATH')

            if local_config.get('model_path'):
                provider = ProviderFactory.create_provider('local', local_config)
                self.providers['local'] = provider
                logger.info("Local LLM provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Local LLM provider: {e}")

        # Check if at least one provider is available
        if not self.providers:
            raise AIServiceError(
                "No AI providers available. Configure at least one provider."
            )

        # Validate current provider
        if self.current_provider_name not in self.providers:
            # Fall back to first available provider
            self.current_provider_name = list(self.providers.keys())[0]
            logger.warning(
                f"Configured provider not available, "
                f"using {self.current_provider_name}"
            )

    @property
    def current_provider(self) -> AIProvider:
        """
        Get current AI provider

        Returns:
            Current provider instance

        Raises:
            AIProviderNotAvailableError: If current provider is not available
        """
        if self.current_provider_name not in self.providers:
            raise AIProviderNotAvailableError(
                self.current_provider_name,
                f"Provider '{self.current_provider_name}' not initialized"
            )

        return self.providers[self.current_provider_name]

    def set_provider(self, provider_name: str) -> bool:
        """
        Switch to a different AI provider

        Args:
            provider_name: Name of provider to use

        Returns:
            True if successful

        Raises:
            AIProviderNotAvailableError: If provider is not available
        """
        provider_name = provider_name.lower()

        if provider_name not in self.providers:
            available = ', '.join(self.providers.keys())
            raise AIProviderNotAvailableError(
                provider_name,
                f"Provider not available. Available: {available}"
            )

        self.current_provider_name = provider_name
        logger.info(f"Switched to provider: {provider_name}")
        return True

    def get_completion(
        self,
        prompt: str,
        context: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Get AI completion with rate limiting and validation

        Args:
            prompt: The prompt to send
            context: Optional context/system message
            provider: Optional specific provider to use
            **kwargs: Additional provider-specific parameters

        Returns:
            AI response text

        Raises:
            AIProviderError: If API call fails
            AIProviderTimeoutError: If rate limit timeout occurs
        """
        # Use specified provider or current
        provider_name = provider or self.current_provider_name

        # Validate inputs
        Validator.validate_text_content(prompt, max_length=100000)
        if context:
            Validator.validate_text_content(context, max_length=50000)

        # Acquire rate limit token
        if not self.rate_limiter.acquire(provider_name, timeout=10.0):
            from .exceptions import AIProviderTimeoutError
            raise AIProviderTimeoutError(provider_name, timeout=10.0)

        # Get provider
        if provider_name != self.current_provider_name:
            if provider_name not in self.providers:
                raise AIProviderNotAvailableError(
                    provider_name,
                    f"Provider not available"
                )
            ai_provider = self.providers[provider_name]
        else:
            ai_provider = self.current_provider

        # Make API call with performance monitoring
        with self.perf_monitor.measure(f"ai_completion_{provider_name}"):
            try:
                response = ai_provider.get_completion(prompt, context, **kwargs)
                logger.debug(
                    f"Completion from {provider_name}: {len(response)} chars"
                )
                return response
            except Exception as e:
                logger.error(f"Completion failed from {provider_name}: {e}")
                raise

    def explain_code(
        self,
        code: str,
        context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """Explain code using current provider"""
        provider_name = provider or self.current_provider_name
        ai_provider = self.providers.get(provider_name, self.current_provider)

        if not self.rate_limiter.acquire(provider_name, timeout=10.0):
            from .exceptions import AIProviderTimeoutError
            raise AIProviderTimeoutError(provider_name, timeout=10.0)

        with self.perf_monitor.measure(f"explain_code_{provider_name}"):
            return ai_provider.explain_code(code, context)

    def improve_code(
        self,
        code: str,
        context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """Improve code using current provider"""
        provider_name = provider or self.current_provider_name
        ai_provider = self.providers.get(provider_name, self.current_provider)

        if not self.rate_limiter.acquire(provider_name, timeout=10.0):
            from .exceptions import AIProviderTimeoutError
            raise AIProviderTimeoutError(provider_name, timeout=10.0)

        with self.perf_monitor.measure(f"improve_code_{provider_name}"):
            return ai_provider.improve_code(code, context)

    def generate_code(
        self,
        description: str,
        context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """Generate code using current provider"""
        provider_name = provider or self.current_provider_name
        ai_provider = self.providers.get(provider_name, self.current_provider)

        if not self.rate_limiter.acquire(provider_name, timeout=10.0):
            from .exceptions import AIProviderTimeoutError
            raise AIProviderTimeoutError(provider_name, timeout=10.0)

        with self.perf_monitor.measure(f"generate_code_{provider_name}"):
            return ai_provider.generate_code(description, context)

    def analyze_code(
        self,
        code: str,
        context: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """Analyze code using current provider"""
        provider_name = provider or self.current_provider_name
        ai_provider = self.providers.get(provider_name, self.current_provider)

        if not self.rate_limiter.acquire(provider_name, timeout=10.0):
            from .exceptions import AIProviderTimeoutError
            raise AIProviderTimeoutError(provider_name, timeout=10.0)

        with self.perf_monitor.measure(f"analyze_code_{provider_name}"):
            return ai_provider.analyze_code(code, context)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())

    def get_provider_info(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a provider

        Args:
            provider_name: Provider name (uses current if None)

        Returns:
            Dictionary with provider information
        """
        provider_name = provider_name or self.current_provider_name

        if provider_name not in self.providers:
            return {"error": f"Provider '{provider_name}' not available"}

        provider = self.providers[provider_name]

        return {
            "name": provider.get_provider_name(),
            "current_model": provider.get_current_model(),
            "available_models": provider.get_models(),
            "is_available": provider.is_available(),
            "config_status": provider.validate_config(),
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for AI operations"""
        stats = {}

        # Get stats for each operation type
        for provider_name in self.providers.keys():
            for operation in ['completion', 'explain_code', 'improve_code', 'generate_code', 'analyze_code']:
                metric_name = f"ai_{operation}_{provider_name}"
                metric_stats = self.perf_monitor.get_stats(metric_name)
                if metric_stats.get('count', 0) > 0:
                    stats[metric_name] = metric_stats

        return stats

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        return self.rate_limiter.get_stats()

    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration loading status"""
        return self.config_status
