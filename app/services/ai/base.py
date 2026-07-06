"""
TheMemeCanvas Automation Suite — Abstract AI Provider Interface
==============================================================
Defines the contract all AI providers must implement.
Switching providers requires zero changes to the calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseAIProvider(ABC):
    """
    Abstract base class for AI text generation providers.
    
    Implement this class to add support for any AI provider:
    - OpenAI (implemented)
    - Anthropic Claude
    - Google Gemini
    - Ollama (local)
    - Any other provider
    """

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.8,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).

        Returns:
            Generated text string.

        Raises:
            AIProviderError: If the API call fails.
        """
        ...

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate text expected to be valid JSON.

        Args:
            prompt: Prompt requesting JSON output.
            max_tokens: Max tokens.

        Returns:
            Raw JSON string (caller is responsible for parsing).
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider name."""
        ...


class AIProviderError(Exception):
    """Raised when an AI provider API call fails."""
    pass


def get_ai_provider() -> BaseAIProvider:
    """
    Factory function — returns the configured AI provider singleton.

    Always returns the GroqProvider.
    """
    from app.services.ai.groq_provider import GroqProvider
    return GroqProvider()
