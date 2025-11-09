"""
Abstract base class for AI providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AI provider

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._current_model = None

    @abstractmethod
    def get_completion(
        self, prompt: str, context: Optional[str] = None, **kwargs
    ) -> str:
        """
        Get AI completion for a prompt

        Args:
            prompt: The prompt to send to the AI
            context: Optional context to provide with the prompt
            **kwargs: Additional provider-specific parameters

        Returns:
            The AI's response as a string

        Raises:
            AIProviderError: If the request fails
        """
        pass

    @abstractmethod
    def get_models(self) -> List[Dict[str, str]]:
        """
        Get available models for this provider

        Returns:
            List of model dictionaries with keys: id, name, description

        Example:
            [
                {
                    "id": "gpt-4o",
                    "name": "GPT-4o",
                    "description": "Latest OpenAI model"
                }
            ]
        """
        pass

    @abstractmethod
    def set_model(self, model_id: str) -> bool:
        """
        Set the active model

        Args:
            model_id: The model ID to activate

        Returns:
            True if successful, False otherwise

        Raises:
            InvalidInputError: If model_id is invalid
        """
        pass

    @abstractmethod
    def get_current_model(self) -> Optional[str]:
        """
        Get the currently active model ID

        Returns:
            Current model ID or None if not set
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is properly configured and available

        Returns:
            True if provider is available, False otherwise
        """
        pass

    @abstractmethod
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate provider configuration

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider

        Returns:
            Provider name (e.g., "OpenAI", "Anthropic", "LocalLLM")
        """
        pass

    def explain_code(self, code: str, context: Optional[str] = None) -> str:
        """
        Explain code functionality

        Args:
            code: Code to explain
            context: Optional additional context

        Returns:
            Explanation of the code
        """
        prompt = f"Explain the following code:\n\n{code}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.get_completion(prompt)

    def improve_code(self, code: str, context: Optional[str] = None) -> str:
        """
        Suggest improvements for code

        Args:
            code: Code to improve
            context: Optional additional context

        Returns:
            Improved version of the code
        """
        prompt = f"Improve the following code:\n\n{code}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.get_completion(prompt)

    def generate_code(self, description: str, context: Optional[str] = None) -> str:
        """
        Generate code from description

        Args:
            description: Description of what to generate
            context: Optional additional context

        Returns:
            Generated code
        """
        prompt = f"Generate code for: {description}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.get_completion(prompt)

    def analyze_code(self, code: str, context: Optional[str] = None) -> str:
        """
        Analyze code for issues

        Args:
            code: Code to analyze
            context: Optional additional context

        Returns:
            Analysis results
        """
        prompt = f"Analyze the following code for potential issues:\n\n{code}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.get_completion(prompt)

    def translate_nlp(self, nlp_text: str, context: Optional[str] = None) -> str:
        """
        Translate natural language to code

        Args:
            nlp_text: Natural language description
            context: Optional additional context

        Returns:
            Generated code
        """
        prompt = f"Translate this natural language description to code:\n\n{nlp_text}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.get_completion(prompt)
