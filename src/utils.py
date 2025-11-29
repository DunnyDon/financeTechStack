"""
Utility functions for HTTP requests, logging, and data operations.

This module provides common functionality used across the application including
HTTP request handling with exponential backoff, logging setup, and data validation.
"""

import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from .constants import (
    DEFAULT_TIMEOUT,
    INITIAL_BACKOFF_DELAY,
    REQUEST_MAX_RETRIES,
    USER_AGENTS,
)

__all__ = [
    "setup_logger",
    "get_logger",
    "make_request_with_backoff",
    "get_next_user_agent",
    "validate_ticker",
    "validate_cik",
]


# Module-level user agent index for rotation
_ua_index: int = 0
_logger: Optional[logging.Logger] = None


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: INFO).

    Returns:
        Configured logger instance.
    """
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)

    _logger = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def get_next_user_agent() -> str:
    """
    Rotate through available user agents.

    Returns:
        Next user agent string from the rotation list.
    """
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua


def make_request_with_backoff(
    url: str,
    max_retries: int = REQUEST_MAX_RETRIES,
    initial_delay: float = INITIAL_BACKOFF_DELAY,
    timeout: int = DEFAULT_TIMEOUT,
    headers: Optional[dict[str, str]] = None,
    rate_limit_delay: float = 0.1,
) -> Optional[dict[str, Any]]:
    """
    Make an HTTP GET request with exponential backoff retry strategy.

    Implements exponential backoff on 403/429 errors and general exceptions.
    Rotates user agents to avoid blocking. Respects SEC rate limiting requirements.

    Args:
        url: URL to request.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        timeout: Request timeout in seconds.
        headers: Custom headers to include in the request.
        rate_limit_delay: Delay between requests to respect rate limits (seconds).

    Returns:
        JSON response as dictionary, or None if all retries failed.

    Raises:
        requests.RequestException: For non-recoverable HTTP errors.
    """
    logger = get_logger(__name__)

    # Rate limiting: add delay before making request
    time.sleep(rate_limit_delay)

    default_headers = {
        "User-Agent": get_next_user_agent(),
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
    }

    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=default_headers, timeout=timeout)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                wait_time = initial_delay * (2**attempt)
                logger.warning(
                    f"403 Forbidden on attempt {attempt + 1}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
            elif response.status_code == 429:  # Rate limited
                wait_time = initial_delay * (2**attempt) * 10  # Longer backoff for 429
                logger.warning(
                    f"429 Too Many Requests on attempt {attempt + 1}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
            else:
                response.raise_for_status()

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = initial_delay * (2**attempt)
                logger.warning(
                    f"Request error on attempt {attempt + 1}: {e}. "
                    f"Waiting {wait_time}s before retry..."
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"Request failed after {max_retries} attempts: {e}"
                )
                return None

    logger.error(f"Failed to retrieve {url} after {max_retries} attempts")
    return None


def validate_ticker(ticker: str) -> bool:
    """
    Validate stock ticker symbol format.

    Args:
        ticker: Ticker symbol to validate.

    Returns:
        True if ticker is valid, False otherwise.
    """
    if not ticker or not isinstance(ticker, str):
        return False
    ticker = ticker.strip().upper()
    # Tickers are typically 1-5 alphanumeric characters
    return 1 <= len(ticker) <= 5 and ticker.isalpha()


def validate_cik(cik: str) -> bool:
    """
    Validate CIK (Central Index Key) format.

    Args:
        cik: CIK to validate.

    Returns:
        True if CIK is valid, False otherwise.
    """
    if not cik or not isinstance(cik, str):
        return False
    # CIK should be numeric (10 digits when zero-padded)
    return cik.isdigit() and len(cik) == 10


def safe_float_conversion(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a value to float with error handling.

    Args:
        value: Value to convert.
        default: Default value if conversion fails.

    Returns:
        Converted float or default value.
    """
    try:
        if value is None or (isinstance(value, str) and value.lower() == "n/a"):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def format_timestamp() -> str:
    """
    Get current timestamp in standard format (YYYYMMDD_HHMMSS).

    Returns:
        Formatted timestamp string.
    """
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")
