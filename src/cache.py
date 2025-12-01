"""
Caching utilities for SEC API data.

Implements disk-based caching for CIK lookups to avoid hitting SEC API rate limits.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from .constants import DEFAULT_OUTPUT_DIR
from .utils import get_logger

logger = get_logger(__name__)

# Cache configuration
CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
CIK_CACHE_FILE = os.path.join(CACHE_DIR, "cik_cache.json")
CACHE_EXPIRY_DAYS = 30  # Cache expires after 30 days


class CIKCache:
    """Manages CIK caching to disk."""

    @staticmethod
    def _ensure_cache_dir() -> None:
        """Ensure cache directory exists."""
        os.makedirs(CACHE_DIR, exist_ok=True)

    @staticmethod
    def _is_cache_expired(timestamp: str) -> bool:
        """Check if cache entry has expired.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            True if cache is expired, False otherwise
        """
        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(days=CACHE_EXPIRY_DAYS)
            return datetime.now() > expiry_time
        except (ValueError, TypeError):
            return True

    @staticmethod
    def get(ticker: str) -> Optional[str]:
        """Get CIK from cache.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string if found in valid cache, None otherwise
        """
        if not os.path.exists(CIK_CACHE_FILE):
            logger.debug(f"CIK cache file not found")
            return None

        try:
            with open(CIK_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)

            ticker_upper = ticker.upper()

            if ticker_upper not in cache:
                logger.debug(f"CIK not in cache for ticker: {ticker}")
                return None

            entry = cache[ticker_upper]
            timestamp = entry.get("timestamp")

            if CIKCache._is_cache_expired(timestamp):
                logger.info(f"CIK cache expired for ticker: {ticker}")
                return None

            cik = entry.get("cik")
            logger.debug(f"CIK cache hit for {ticker}: {cik}")
            return cik

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading CIK cache: {e}")
            return None

    @staticmethod
    def set(ticker: str, cik: str) -> None:
        """Save CIK to cache.

        Args:
            ticker: Stock ticker symbol
            cik: SEC CIK number
        """
        CIKCache._ensure_cache_dir()

        try:
            # Load existing cache
            cache = {}
            if os.path.exists(CIK_CACHE_FILE):
                with open(CIK_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)

            # Update with new entry
            ticker_upper = ticker.upper()
            cache[ticker_upper] = {
                "cik": cik,
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
            }

            # Write back to file
            with open(CIK_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)

            logger.debug(f"Cached CIK for {ticker}: {cik}")

        except IOError as e:
            logger.warning(f"Error writing CIK cache: {e}")

    @staticmethod
    def clear() -> None:
        """Clear the CIK cache."""
        try:
            if os.path.exists(CIK_CACHE_FILE):
                os.remove(CIK_CACHE_FILE)
                logger.info("CIK cache cleared")
        except IOError as e:
            logger.warning(f"Error clearing CIK cache: {e}")

    @staticmethod
    def get_all() -> Dict[str, Dict]:
        """Get all cached entries.

        Returns:
            Dictionary of all cached CIK entries
        """
        if not os.path.exists(CIK_CACHE_FILE):
            return {}

        try:
            with open(CIK_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading CIK cache: {e}")
            return {}

    @staticmethod
    def stats() -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        all_entries = CIKCache.get_all()
        valid_entries = sum(
            1 for entry in all_entries.values()
            if not CIKCache._is_cache_expired(entry.get("timestamp", ""))
        )

        return {
            "total_entries": len(all_entries),
            "valid_entries": valid_entries,
            "expired_entries": len(all_entries) - valid_entries,
            "cache_file": CIK_CACHE_FILE,
            "cache_expiry_days": CACHE_EXPIRY_DAYS,
        }
