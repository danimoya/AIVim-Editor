"""
Factory for creating AI provider instances
"""
import os
from typing import Optional, Dict, Any
import logging

from .base_provider import AIProvider
from ..exceptions import AIProviderNotAvailableError, InvalidInputError

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing AI provider instances"""

    # Registry of available providers
    _providers: Dict[str, type] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a provider class

        Args:
            name: Provider name (e.g., "openai", "claude", "local")
            provider_class: Provider class that implements AIProvider
        """
        if not issubclass(provider_class, AIProvider):
            raise ValueError(f"Provider class must inherit from AIProvider")
        cls._providers[name.lower()] = provider_class
        logger.debug(f"Registered AI provider: {name}")

    @classmethod
    def create_provider(
        cls, provider_name: str, config: Optional[Dict[str, Any]] = None
    ) -> AIProvider:
        """
        Create an AI provider instance

        Args:
            provider_name: Name of the provider (e.g., "openai", "claude", "local")
            config: Optional configuration dictionary

        Returns:
            AI provider instance

        Raises:
            AIProviderNotAvailableError: If provider is not available
            InvalidInputError: If provider name is invalid
        """
        provider_name = provider_name.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise InvalidInputError(
                "provider",
                provider_name,
                f"Unknown provider. Available: {available}",
            )

        provider_class = cls._providers[provider_name]

        try:
            provider = provider_class(config)

            # Validate provider is available
            if not provider.is_available():
                validation = provider.validate_config()
                errors = validation.get("errors", ["Provider not properly configured"])
                raise AIProviderNotAvailableError(
                    provider_name, "; ".join(errors)
                )

            logger.info(f"Created AI provider: {provider_name}")
            return provider

        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            raise

    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get list of registered provider names

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, provider_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a provider is available and properly configured

        Args:
            provider_name: Name of the provider
            config: Optional configuration

        Returns:
            True if provider is available, False otherwise
        """
        try:
            provider = cls.create_provider(provider_name, config)
            return provider.is_available()
        except Exception:
            return False
