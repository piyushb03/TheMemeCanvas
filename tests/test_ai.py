"""
Tests for AI metadata generator.
Run: pytest tests/test_ai.py -v
"""
import json
import pytest
from unittest.mock import MagicMock, patch


class TestMetadataGenerator:
    """Tests for the MetadataGenerator service."""

    def test_parse_json_list_array(self):
        """Test parsing a direct JSON array."""
        from app.services.ai.metadata_gen import MetadataGenerator
        gen = MetadataGenerator.__new__(MetadataGenerator)

        result = gen._parse_json_list('["title1", "title2", "title3"]')
        assert result == ["title1", "title2", "title3"]

    def test_parse_json_list_object(self):
        """Test parsing JSON object with list value."""
        from app.services.ai.metadata_gen import MetadataGenerator
        gen = MetadataGenerator.__new__(MetadataGenerator)

        result = gen._parse_json_list('{"titles": ["title1", "title2"]}')
        assert result == ["title1", "title2"]

    def test_parse_json_list_embedded(self):
        """Test extracting JSON array from surrounding text."""
        from app.services.ai.metadata_gen import MetadataGenerator
        gen = MetadataGenerator.__new__(MetadataGenerator)

        result = gen._parse_json_list('Here are the titles: ["title1", "title2"]')
        assert result == ["title1", "title2"]

    def test_score_titles_prefers_optimal_length(self):
        """Test that title scorer prefers titles of 40-70 chars."""
        from app.services.ai.metadata_gen import MetadataGenerator
        gen = MetadataGenerator.__new__(MetadataGenerator)

        titles = [
            "Short",                                                    # Too short
            "😂 This Is A Perfectly Sized YouTube Short Title Here!",   # Optimal
            "X" * 90,                                                   # Too long
        ]

        best = gen._score_titles(titles)
        assert best == titles[1]

    def test_filename_to_title(self):
        """Test filename → title fallback."""
        from app.services.ai.metadata_gen import MetadataGenerator
        gen = MetadataGenerator.__new__(MetadataGenerator)

        result = gen._filename_to_title("funny_anime_meme_001.mp4")
        assert "Funny Anime Meme 001" in result
        assert "#TheMemeCanvas" in result

    def test_generate_returns_metadata(self):
        """Test that generate() returns a complete VideoMetadata object."""
        from app.services.ai.metadata_gen import MetadataGenerator, VideoMetadata
        from app.services.ai.base import BaseAIProvider

        # Mock the AI provider
        mock_provider = MagicMock(spec=BaseAIProvider)
        mock_provider.provider_name = "MockAI"
        mock_provider.generate_json.return_value = '["Test Title One 😂", "Test Title Two"]'
        mock_provider.generate_text.return_value = "Funniest anime meme you'll see today!"

        gen = MetadataGenerator(provider=mock_provider)
        result = gen.generate("test_video.mp4")

        assert isinstance(result, VideoMetadata)
        assert result.title != ""
        assert "TheMemeCanvas" in result.tags
