"""
TheMemeCanvas Automation Suite — AI Metadata Generator
=======================================================
Generates all AI-powered metadata for each video:
  - Multiple titles (scored and ranked)
  - YouTube description opening sentence
  - YouTube SEO tags
  - Instagram caption
  - Instagram hashtags

Maintains title history to prevent repetition.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from app.config.constants import (
    AI_DESCRIPTION_OPENING_PROMPT,
    AI_TAGS_PROMPT,
    AI_TITLE_PROMPT,
    BASE_YOUTUBE_TAGS,
    BRAND_NAME,
    YOUTUBE_DESCRIPTION_TEMPLATE,
)
from app.config.settings import settings
from app.services.ai.base import AIProviderError, BaseAIProvider, get_ai_provider

logger = logging.getLogger("thememecanvas.ai")


@dataclass
class VideoMetadata:
    """Complete AI-generated metadata for one video."""

    title: str
    title_candidates: List[str] = field(default_factory=list)
    description: str = ""
    ai_opening: str = ""
    tags: List[str] = field(default_factory=list)
    provider_name: str = ""


class MetadataGenerator:
    """
    Orchestrates AI metadata generation for TheMemeCanvas videos.

    Design:
        - Generates 5 title candidates, scores them, picks the best
        - Maintains recent title history to avoid repetition
        - Combines brand base tags with AI-generated specific tags
        - Builds final YouTube description from templates
    """

    NUM_TITLE_CANDIDATES = 5
    NUM_ADDITIONAL_TAGS = 15

    def __init__(self, provider: Optional[BaseAIProvider] = None) -> None:
        self.provider = provider or get_ai_provider()
        logger.info("MetadataGenerator initialized with provider: %s", self.provider.provider_name)

    def generate(self, filename: str, recent_titles: Optional[List[str]] = None) -> VideoMetadata:
        """
        Generate complete metadata for a video.

        Args:
            filename: Original video filename (used as content hint).
            recent_titles: List of recently used titles to avoid repetition.

        Returns:
            VideoMetadata instance with all fields populated.
        """
        recent_titles = recent_titles or []
        logger.info("Generating AI metadata for: %s", filename)

        # --- Step 1: Generate title candidates ---
        title, candidates = self._generate_title(filename, recent_titles)
        logger.info("Selected title: %s", title)

        # --- Step 2: Generate description opening ---
        ai_opening = self._generate_opening(filename, title)
        logger.info("AI opening: %s", ai_opening[:80])

        # --- Step 3: Build full YouTube description ---
        description = self._build_description(ai_opening)

        # --- Step 4: Generate YouTube tags ---
        tags = self._generate_tags(filename, title)
        logger.info("Generated %d tags.", len(tags))

        return VideoMetadata(
            title=title,
            title_candidates=candidates,
            description=description,
            ai_opening=ai_opening,
            tags=tags,
            provider_name=self.provider.provider_name,
        )

    # ---------------------------------------------------------------------------
    # Title Generation
    # ---------------------------------------------------------------------------

    def _generate_title(
        self, filename: str, recent_titles: List[str]
    ) -> Tuple[str, List[str]]:
        """Generate and score multiple title candidates, return the best."""
        prompt = AI_TITLE_PROMPT.format(
            brand_name=BRAND_NAME,
            num_titles=self.NUM_TITLE_CANDIDATES,
            filename=filename,
            recent_titles=", ".join(recent_titles[-10:]) if recent_titles else "none",
        )

        try:
            raw = self.provider.generate_json(prompt, max_tokens=400)
            candidates = self._parse_json_list(raw)

            if not candidates:
                raise ValueError("Empty title list returned")

            # Score and select the best title
            best = self._score_titles(candidates)
            return best, candidates

        except (AIProviderError, ValueError, json.JSONDecodeError) as e:
            logger.warning("Title generation failed: %s. Using filename as fallback.", e)
            fallback = self._filename_to_title(filename)
            return fallback, [fallback]

    def _score_titles(self, titles: List[str]) -> str:
        """
        Score title candidates and return the best one.

        Scoring criteria:
            - Optimal length (40-70 chars): +2
            - Contains emoji: +1
            - Contains power word: +2
            - Contains question: +1
            - Not too short (<20 chars): -2
            - Too long (>80 chars): -1
        """
        POWER_WORDS = {
            "hilarious", "epic", "impossible", "insane", "wait",
            "shocking", "viral", "omg", "lol", "best", "funniest",
            "can't stop", "when", "pov", "me when", "nobody",
        }

        best_title = titles[0]
        best_score = -999

        for title in titles:
            score = 0
            length = len(title)

            if 40 <= length <= 70:
                score += 2
            elif length < 20:
                score -= 2
            elif length > 80:
                score -= 1

            # Has emoji?
            if any(ord(c) > 127 for c in title):
                score += 1

            # Has power word?
            title_lower = title.lower()
            if any(pw in title_lower for pw in POWER_WORDS):
                score += 2

            # Is a question?
            if "?" in title:
                score += 1

            if score > best_score:
                best_score = score
                best_title = title

        return best_title

    def _filename_to_title(self, filename: str) -> str:
        """Convert a filename to a readable title as fallback."""
        stem = Path(filename).stem
        # Replace underscores/hyphens with spaces
        title = re.sub(r"[_\-]+", " ", stem).strip().title()
        return f"😂 {title} #TheMemeCanvas"

    # ---------------------------------------------------------------------------
    # Description
    # ---------------------------------------------------------------------------

    def _generate_opening(self, filename: str, title: str) -> str:
        """Generate the AI opening sentence for the YouTube description."""
        prompt = AI_DESCRIPTION_OPENING_PROMPT.format(
            brand_name=BRAND_NAME,
            filename=filename,
            title=title,
        )

        try:
            return self.provider.generate_text(prompt, max_tokens=100, temperature=0.9).strip()
        except AIProviderError as e:
            logger.warning("Opening generation failed: %s", e)
            return f"😂 Another hilarious meme from {BRAND_NAME}!"

    def _build_description(self, ai_opening: str) -> str:
        """Build the full YouTube description from the branded template."""
        # Collect all tags for the tags line in description
        tag_list = BASE_YOUTUBE_TAGS[:10]  # First 10 base tags in description
        tags_line = " • ".join(tag_list)

        return YOUTUBE_DESCRIPTION_TEMPLATE.format(
            ai_opening=ai_opening,
            brand_name=BRAND_NAME,
            youtube_url=settings.youtube_channel_url,
            tags_line=tags_line,
        )

    # ---------------------------------------------------------------------------
    # YouTube Tags
    # ---------------------------------------------------------------------------

    def _generate_tags(self, filename: str, title: str) -> List[str]:
        """Combine base brand tags with AI-generated specific tags."""
        prompt = AI_TAGS_PROMPT.format(
            num_tags=self.NUM_ADDITIONAL_TAGS,
            filename=filename,
            title=title,
            base_tags=", ".join(BASE_YOUTUBE_TAGS),
        )

        try:
            raw = self.provider.generate_json(prompt, max_tokens=300)
            ai_tags = self._parse_json_list(raw)
        except (AIProviderError, ValueError, json.JSONDecodeError) as e:
            logger.warning("Tag generation failed: %s", e)
            ai_tags = []

        # Combine: base tags first, then AI-specific tags (no duplicates)
        combined = list(BASE_YOUTUBE_TAGS)
        seen = {t.lower() for t in combined}

        for tag in ai_tags:
            if tag.lower() not in seen:
                combined.append(tag)
                seen.add(tag.lower())

        return combined[:settings.youtube_max_tags]



    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _parse_json_list(raw: str) -> List[str]:
        """
        Parse a JSON list from a raw string response.
        Handles both bare arrays and objects with a list value.
        """
        raw = raw.strip()

        # Try direct array parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
            # If it's an object, find the first list value
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        return [str(item) for item in v if item]
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON array from text using regex
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Cannot parse JSON list from: {raw[:200]}")
