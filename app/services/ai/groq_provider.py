"""
TheMemeCanvas Automation Suite — Groq Provider
==============================================
Implements the BaseAIProvider interface using Groq's SDK or OpenAI-compatible endpoint.
"""

from __future__ import annotations

import logging
from typing import Optional

import openai

from app.config.settings import settings
from app.services.ai.base import AIProviderError, BaseAIProvider

logger = logging.getLogger("thememecanvas.ai")


class GroqProvider(BaseAIProvider):
    """
    Groq API provider for text generation.
    Uses the OpenAI-compatible endpoint for maximum speed and simplicity.
    """

    def __init__(self) -> None:
        self._client: Optional[openai.OpenAI] = None

    @property
    def client(self) -> openai.OpenAI:
        if self._client is None:
            if not settings.groq_api_key or settings.groq_api_key == "YOUR_GROQ_API_KEY":
                raise RuntimeError("GROQ_API_KEY is not configured in environment/.env file.")
            
            # Groq provides an OpenAI-compatible endpoint
            self._client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
        return self._client

    @property
    def provider_name(self) -> str:
        return f"Groq ({settings.groq_model})"

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.8,
    ) -> str:
        """Generate text using Groq chat completions."""
        try:
            logger.debug("Groq request: model=%s max_tokens=%d", settings.groq_model, max_tokens)

            response = self.client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert content creator and SEO specialist for TheMemeCanvas, "
                            "a viral meme channel on YouTube Shorts and Instagram Reels. "
                            "Always be punchy, engaging, and optimized for virality."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip()
            logger.debug("Groq response: %d chars", len(text))
            return text

        except Exception as e:
            logger.error("Groq text generation failed: %s", e)
            raise AIProviderError(f"Groq generation error: {e}")

    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 500,
    ) -> str:
        """Generate JSON output using Groq JSON mode."""
        try:
            logger.debug("Groq JSON request: model=%s", settings.groq_model)

            response = self.client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert content strategist for TheMemeCanvas. "
                            "Always respond with valid JSON only. No markdown, no explanation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content.strip()
            return text

        except Exception as e:
            logger.error("Groq JSON generation failed: %s", e)
            raise AIProviderError(f"Groq JSON generation error: {e}")
