"""
Tests for Google Drive queue manager.
Run: pytest tests/test_drive.py -v
"""
import pytest
from unittest.mock import MagicMock, patch


class TestQueueManager:
    """Tests for the QueueManager service."""

    def test_apply_ordering_oldest_first(self):
        """Test that oldest_first ordering works correctly."""
        from app.services.drive.queue_manager import QueueManager
        qm = QueueManager.__new__(QueueManager)

        files = [
            {"id": "1", "name": "video_c.mp4", "createdTime": "2024-03-01T00:00:00Z"},
            {"id": "2", "name": "video_a.mp4", "createdTime": "2024-01-01T00:00:00Z"},
            {"id": "3", "name": "video_b.mp4", "createdTime": "2024-02-01T00:00:00Z"},
        ]

        with patch.object(type(qm), 'client', create=True):
            from app.config import settings as s
            with patch.object(s.settings, 'upload_order', 'oldest_first'):
                result = qm._apply_ordering(files)

        assert result[0]["id"] == "2"  # Oldest first

    def test_apply_ordering_newest_first(self):
        """Test that newest_first ordering works correctly."""
        from app.services.drive.queue_manager import QueueManager
        qm = QueueManager.__new__(QueueManager)

        files = [
            {"id": "1", "name": "video_a.mp4", "createdTime": "2024-01-01T00:00:00Z"},
            {"id": "2", "name": "video_c.mp4", "createdTime": "2024-03-01T00:00:00Z"},
        ]

        with patch.object(s.settings, 'upload_order', 'newest_first'):
            result = qm._apply_ordering(files)

        assert result[0]["id"] == "2"  # Newest first

    def test_find_thumbnail_match(self):
        """Test thumbnail detection by filename stem matching."""
        from app.services.drive.queue_manager import QueueManager
        qm = QueueManager.__new__(QueueManager)

        mock_client = MagicMock()
        mock_client.list_files.return_value = [
            {"id": "thumb1", "name": "video001.jpg"},
            {"id": "thumb2", "name": "other.jpg"},
        ]
        qm.client = mock_client

        result = qm.find_thumbnail("video001.mp4", "folder123")
        assert result is not None
        assert result["id"] == "thumb1"

    def test_find_thumbnail_no_match(self):
        """Test that no thumbnail is returned when none matches."""
        from app.services.drive.queue_manager import QueueManager
        qm = QueueManager.__new__(QueueManager)

        mock_client = MagicMock()
        mock_client.list_files.return_value = [
            {"id": "thumb1", "name": "different_video.jpg"},
        ]
        qm.client = mock_client

        result = qm.find_thumbnail("video001.mp4", "folder123")
        assert result is None
