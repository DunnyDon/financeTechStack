"""
Comprehensive test suite for CIK caching functionality.

Tests the CIKCache class to ensure:
- Cache hit/miss scenarios work correctly
- Expiry logic prevents stale data
- Cache persistence works
- Statistics tracking is accurate
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.cache import CIKCache


class TestCIKCacheBasicOperations:
    """Test basic set/get operations."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_set_and_get_ticker_cik(self):
        """Test setting and retrieving a CIK for a ticker."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                retrieved_cik = CIKCache.get("AAPL")
                assert retrieved_cik == "0000320193"

    def test_get_nonexistent_ticker(self):
        """Test retrieving CIK for non-existent ticker returns None."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                result = CIKCache.get("NONEXISTENT")
                assert result is None

    def test_set_multiple_tickers(self):
        """Test setting and retrieving multiple tickers."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                tickers_data = {
                    "AAPL": "0000320193",
                    "MSFT": "0000789019",
                    "GOOGL": "0001652044",
                }

                for ticker, cik in tickers_data.items():
                    CIKCache.set(ticker, cik)

                for ticker, expected_cik in tickers_data.items():
                    assert CIKCache.get(ticker) == expected_cik

    def test_overwrite_existing_cik(self):
        """Test that setting a CIK multiple times overwrites previous value."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("AAPL", "0000320194")
                assert CIKCache.get("AAPL") == "0000320194"

    def test_get_all_tickers(self):
        """Test retrieving all cached tickers."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("MSFT", "0000789019")

                all_cache = CIKCache.get_all()
                assert len(all_cache) == 2
                assert all_cache["AAPL"]["cik"] == "0000320193"
                assert all_cache["MSFT"]["cik"] == "0000789019"

    def test_case_insensitivity_in_ticker(self):
        """Test that ticker lookup is case-insensitive."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("aapl", "0000320193")
                # Should find it with uppercase
                assert CIKCache.get("AAPL") == "0000320193"


class TestCIKCacheExpiry:
    """Test cache expiry logic."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_cache_expiry_not_expired(self):
        """Test that recently cached entries are not expired."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")

                # Should still be valid
                retrieved = CIKCache.get("AAPL")
                assert retrieved == "0000320193"

    def test_cache_expiry_is_expired(self):
        """Test that old cached entries are considered expired."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")

                # Manually set timestamp to 31 days ago
                cache_data = CIKCache.get_all()
                old_timestamp = (datetime.now() - timedelta(days=31)).isoformat()
                cache_data["AAPL"]["timestamp"] = old_timestamp

                # Write modified cache back
                os.makedirs(self.temp_dir, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f)

                # Should return None (expired)
                retrieved = CIKCache.get("AAPL")
                assert retrieved is None

    def test_is_cache_expired_method(self):
        """Test the _is_cache_expired method directly."""
        # Recent timestamp should not be expired
        recent_timestamp = datetime.now().isoformat()
        assert not CIKCache._is_cache_expired(recent_timestamp)

        # Old timestamp should be expired
        old_timestamp = (datetime.now() - timedelta(days=31)).isoformat()
        assert CIKCache._is_cache_expired(old_timestamp)

    def test_cache_expiry_boundary(self):
        """Test cache expiry at 30-day boundary."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")

                # Set to exactly 30 days - 1 second (should NOT be expired)
                cache_data = CIKCache.get_all()
                boundary_timestamp = (
                    datetime.now() - timedelta(days=30, seconds=-1)
                ).isoformat()
                cache_data["AAPL"]["timestamp"] = boundary_timestamp

                os.makedirs(self.temp_dir, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f)

                retrieved = CIKCache.get("AAPL")
                assert retrieved == "0000320193"


class TestCIKCacheClear:
    """Test cache clearing functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_clear_all_cache(self):
        """Test clearing all cache entries."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("MSFT", "0000789019")

                CIKCache.clear()

                assert CIKCache.get("AAPL") is None
                assert CIKCache.get("MSFT") is None
                all_cache = CIKCache.get_all()
                assert len(all_cache) == 0

    def test_clear_empty_cache(self):
        """Test clearing an empty cache doesn't raise errors."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                # Should not raise any exception
                CIKCache.clear()
                all_cache = CIKCache.get_all()
                assert len(all_cache) == 0


class TestCIKCacheStats:
    """Test cache statistics functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_stats_empty_cache(self):
        """Test statistics for empty cache."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                stats = CIKCache.stats()

                assert stats["total_entries"] == 0
                assert stats["expired_entries"] == 0
                assert stats["valid_entries"] == 0

    def test_stats_with_entries(self):
        """Test statistics with multiple cache entries."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("MSFT", "0000789019")
                CIKCache.set("GOOGL", "0001652044")

                stats = CIKCache.stats()
                assert stats["total_entries"] == 3
                assert stats["valid_entries"] == 3
                assert stats["expired_entries"] == 0

    def test_stats_with_expired_entries(self):
        """Test statistics with mixed valid and expired entries."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("MSFT", "0000789019")

                # Expire one entry
                cache_data = CIKCache.get_all()
                old_timestamp = (datetime.now() - timedelta(days=31)).isoformat()
                cache_data["MSFT"]["timestamp"] = old_timestamp

                os.makedirs(self.temp_dir, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f)

                stats = CIKCache.stats()
                assert stats["total_entries"] == 2
                assert stats["valid_entries"] == 1
                assert stats["expired_entries"] == 1

    def test_stats_includes_cache_file_info(self):
        """Test that stats includes cache file path information."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")

                stats = CIKCache.stats()
                assert "cache_file" in stats
                assert self.cache_file in stats["cache_file"]


class TestCIKCachePersistence:
    """Test that cache persists across operations."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_cache_file_contains_json(self):
        """Test that cache file is valid JSON."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")
                CIKCache.set("MSFT", "0000789019")

                # Read and parse cache file
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                assert isinstance(data, dict)
                assert "AAPL" in data
                assert "MSFT" in data
                assert data["AAPL"]["cik"] == "0000320193"

    def test_cache_file_has_timestamp(self):
        """Test that cache entries include timestamps."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "0000320193")

                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                assert "timestamp" in data["AAPL"]
                assert "cik" in data["AAPL"]
                # Verify timestamp is valid ISO format
                datetime.fromisoformat(data["AAPL"]["timestamp"])


class TestCIKCacheEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_set_with_empty_cik(self):
        """Test setting an empty CIK string."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("AAPL", "")
                retrieved = CIKCache.get("AAPL")
                assert retrieved == ""

    def test_set_with_special_characters_in_ticker(self):
        """Test handling tickers with special characters."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                CIKCache.set("BRK.B", "0001018724")
                retrieved = CIKCache.get("BRK.B")
                assert retrieved == "0001018724"

    def test_large_cache(self):
        """Test cache with many entries."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                # Add 100 entries
                for i in range(100):
                    ticker = f"TICK{i:03d}"
                    cik = f"00000{i:05d}"
                    CIKCache.set(ticker, cik)

                # Verify all entries
                all_cache = CIKCache.get_all()
                assert len(all_cache) == 100

                # Spot check some entries
                assert CIKCache.get("TICK000") == "0000000000"
                assert CIKCache.get("TICK099") == "0000000099"


class TestCIKCacheIntegration:
    """Integration tests for cache functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "cik_cache.json")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        CIKCache.clear()

    def test_cache_avoids_repeated_lookups(self):
        """Test that cache avoids repeated lookups."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                # First lookup - cache miss
                cached = CIKCache.get("AAPL")
                assert cached is None

                # After setting (simulating API call), cache is used
                cik_from_api = "0000320193"
                CIKCache.set("AAPL", cik_from_api)

                # Second lookup - cache hit
                cached = CIKCache.get("AAPL")
                assert cached == cik_from_api

                # Verify stats show cached entry
                stats = CIKCache.stats()
                assert stats["valid_entries"] == 1

    def test_cache_multiple_tickers_performance(self):
        """Test cache performance with multiple tickers."""
        with patch("src.cache.CIK_CACHE_FILE", self.cache_file):
            with patch("src.cache.CACHE_DIR", self.temp_dir):
                # Add multiple tickers
                tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
                ciks = [
                    "0000320193",
                    "0000789019",
                    "0001652044",
                    "0001018724",
                    "0001318605",
                ]

                for ticker, cik in zip(tickers, ciks):
                    CIKCache.set(ticker, cik)

                # Retrieve all and verify
                for ticker, cik in zip(tickers, ciks):
                    assert CIKCache.get(ticker) == cik

                stats = CIKCache.stats()
                assert stats["valid_entries"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
