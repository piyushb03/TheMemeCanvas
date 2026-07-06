"""
Tests for duplicate hash detection.
Run: pytest tests/test_hashing.py -v
"""
import pytest
import tempfile
from pathlib import Path


class TestHashing:
    def test_compute_sha256(self):
        """SHA256 should be consistent for same file content."""
        from app.utils.hashing import compute_sha256

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content for testing")
            tmp_path = Path(f.name)

        try:
            hash1 = compute_sha256(tmp_path)
            hash2 = compute_sha256(tmp_path)
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex = 64 chars
        finally:
            tmp_path.unlink()

    def test_compute_sha256_different_files(self):
        """Different content should produce different hashes."""
        from app.utils.hashing import compute_sha256

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f1:
            f1.write(b"content A")
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f2:
            f2.write(b"content B")
            path2 = Path(f2.name)

        try:
            assert compute_sha256(path1) != compute_sha256(path2)
        finally:
            path1.unlink()
            path2.unlink()

    def test_compute_sha256_file_not_found(self):
        """Should raise FileNotFoundError for missing files."""
        from app.utils.hashing import compute_sha256

        with pytest.raises(FileNotFoundError):
            compute_sha256(Path("/nonexistent/file.mp4"))
