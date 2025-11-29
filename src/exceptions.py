"""
Custom exceptions for the TechStack application.

Provides domain-specific exception classes for better error handling and reporting.
"""

__all__ = [
    "ConfigurationError",
    "APIKeyError",
    "CIKNotFoundError",
    "FilingNotFoundError",
    "DataParseError",
    "ValidationError",
]


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


class APIKeyError(ConfigurationError):
    """Raised when an API key is missing or invalid."""

    pass


class CIKNotFoundError(Exception):
    """Raised when a CIK (Central Index Key) cannot be found for a ticker."""

    pass


class FilingNotFoundError(Exception):
    """Raised when SEC filings cannot be found for a company."""

    pass


class DataParseError(Exception):
    """Raised when data parsing or extraction fails."""

    pass


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass
