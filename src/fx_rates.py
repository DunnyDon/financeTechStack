"""
Foreign exchange rate management and currency conversion.

Handles fetching, caching, and applying FX rates to convert all portfolio
values to EUR for consistent reporting.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import requests
from prefect import get_run_logger, task

from .constants import DEFAULT_OUTPUT_DIR, DEFAULT_TIMEOUT
from .utils import get_logger

__all__ = [
    "FXRateManager",
    "fetch_fx_rates",
    "convert_to_eur",
    "save_fx_rates_to_parquet",
]

logger = get_logger(__name__)

# Cache configuration
FX_CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
FX_CACHE_FILE = os.path.join(FX_CACHE_DIR, "fx_rates.json")
FX_CACHE_EXPIRY_DAYS = 1  # FX rates expire after 1 day

# Common currency codes
SUPPORTED_CURRENCIES = {
    "EUR": 1.0,  # Base currency
    "USD": None,
    "GBP": None,
    "JPY": None,
    "CHF": None,
    "AUD": None,
    "CAD": None,
    "SEK": None,
    "NZD": None,
    "AED": None,
}


class FXRateManager:
    """Manages FX rate fetching, caching, and conversion."""

    @staticmethod
    def _ensure_cache_dir() -> None:
        """Ensure cache directory exists."""
        os.makedirs(FX_CACHE_DIR, exist_ok=True)

    @staticmethod
    def _is_cache_expired(timestamp: str) -> bool:
        """Check if FX cache entry has expired.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            True if cache is expired, False otherwise
        """
        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(days=FX_CACHE_EXPIRY_DAYS)
            return datetime.now() > expiry_time
        except (ValueError, TypeError):
            return True

    @staticmethod
    def get_cached_rates() -> Optional[Dict[str, float]]:
        """Get FX rates from cache if valid.

        Returns:
            Dict with currency codes as keys and rates as values, or None if expired/missing
        """
        if not os.path.exists(FX_CACHE_FILE):
            logger.debug("FX cache file not found")
            return None

        try:
            with open(FX_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            timestamp = cache_data.get("timestamp")

            if FXRateManager._is_cache_expired(timestamp):
                logger.info("FX cache expired")
                return None

            rates = cache_data.get("rates")
            logger.debug(f"Retrieved FX rates from cache with {len(rates)} currencies")
            return rates

        except Exception as e:
            logger.error(f"Error reading FX cache: {e}")
            return None

    @staticmethod
    def save_rates_to_cache(rates: Dict[str, float]) -> None:
        """Save FX rates to cache file.

        Args:
            rates: Dict mapping currency codes to rates (EUR = 1.0 base)
        """
        try:
            FXRateManager._ensure_cache_dir()

            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "rates": rates,
            }

            with open(FX_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(f"FX rates cached for {len(rates)} currencies")
        except Exception as e:
            logger.error(f"Error saving FX cache: {e}")

    @staticmethod
    def fetch_from_api() -> Optional[Dict[str, float]]:
        """Fetch FX rates from Open Exchange Rates API (free tier).

        Uses fixer.io as fallback if primary source fails.

        Returns:
            Dict mapping currency codes to exchange rates (EUR base), or None if failed
        """
        try:
            # Try using exchangerate-api.com (free tier allows requests)
            url = "https://api.exchangerate-api.com/v4/latest/EUR"

            response = requests.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            rates = data.get("rates", {})

            # Ensure EUR is 1.0
            rates["EUR"] = 1.0

            # Filter to supported currencies
            filtered_rates = {
                curr: rates.get(curr) for curr in SUPPORTED_CURRENCIES
                if rates.get(curr) is not None
            }

            logger.info(f"Fetched FX rates for {len(filtered_rates)} currencies from API")
            return filtered_rates

        except Exception as e:
            logger.warning(f"Error fetching FX rates from API: {e}")
            return None

    @staticmethod
    def get_rates(force_refresh: bool = False) -> Dict[str, float]:
        """Get FX rates with automatic cache handling.

        Args:
            force_refresh: If True, always fetch from API

        Returns:
            Dict mapping currency codes to exchange rates (EUR base)
        """
        # Try cache first
        if not force_refresh:
            cached_rates = FXRateManager.get_cached_rates()
            if cached_rates:
                return cached_rates

        # Fetch from API
        rates = FXRateManager.fetch_from_api()

        if rates:
            FXRateManager.save_rates_to_cache(rates)
            return rates

        # Fallback to cached rates even if expired
        cached_rates = FXRateManager.get_cached_rates()
        if cached_rates:
            logger.warning("Using expired FX rates as fallback")
            return cached_rates

        # Final fallback with hardcoded rates
        logger.error("Could not fetch FX rates - using fallback values")
        return {
            "EUR": 1.0,
            "USD": 0.92,
            "GBP": 1.17,
            "JPY": 0.0067,
            "CHF": 1.04,
            "AUD": 0.61,
            "CAD": 0.68,
            "SEK": 0.092,
            "NZD": 0.56,
            "AED": 0.25,
        }

    @staticmethod
    def convert(amount: float, from_ccy: str, to_ccy: str = "EUR") -> float:
        """Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_ccy: Source currency code
            to_ccy: Target currency code (default EUR)

        Returns:
            Converted amount
        """
        if from_ccy == to_ccy:
            return amount

        if from_ccy.upper() not in SUPPORTED_CURRENCIES:
            logger.warning(f"Unsupported currency: {from_ccy}, using as-is")
            return amount

        rates = FXRateManager.get_rates()

        from_rate = rates.get(from_ccy.upper(), 1.0)
        to_rate = rates.get(to_ccy.upper(), 1.0)

        if from_rate == 0 or to_rate == 0:
            logger.error(f"Invalid rate for conversion: {from_ccy} or {to_ccy}")
            return amount

        # Convert: amount * (1 / from_rate) * to_rate
        converted = (amount / from_rate) * to_rate

        return round(converted, 2)

    @staticmethod
    def stats() -> Dict:
        """Get FX cache statistics.

        Returns:
            Dict with cache information
        """
        if not os.path.exists(FX_CACHE_FILE):
            return {
                "cache_file": FX_CACHE_FILE,
                "status": "empty",
                "rate_count": 0,
                "timestamp": None,
            }

        try:
            with open(FX_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            timestamp = cache_data.get("timestamp")
            rates = cache_data.get("rates", {})

            is_expired = FXRateManager._is_cache_expired(timestamp)

            return {
                "cache_file": FX_CACHE_FILE,
                "status": "expired" if is_expired else "valid",
                "rate_count": len(rates),
                "timestamp": timestamp,
                "is_expired": is_expired,
            }
        except Exception as e:
            logger.error(f"Error getting FX stats: {e}")
            return {
                "cache_file": FX_CACHE_FILE,
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def clear_cache() -> None:
        """Clear FX rate cache."""
        try:
            if os.path.exists(FX_CACHE_FILE):
                os.remove(FX_CACHE_FILE)
                logger.info("FX cache cleared")
        except Exception as e:
            logger.error(f"Error clearing FX cache: {e}")


@task(retries=3, retry_delay_seconds=5)
def fetch_fx_rates(force_refresh: bool = False) -> Dict[str, float]:
    """Prefect task to fetch FX rates.

    Args:
        force_refresh: If True, always fetch from API

    Returns:
        Dict mapping currency codes to exchange rates (EUR base)
    """
    logger_instance = get_run_logger()
    logger_instance.info("Fetching FX rates")

    rates = FXRateManager.get_rates(force_refresh=force_refresh)
    logger_instance.info(f"Fetched rates for {len(rates)} currencies")

    return rates


@task
def convert_to_eur(
    amount: float,
    currency: str,
    fx_rates: Optional[Dict[str, float]] = None,
) -> Tuple[float, str]:
    """Prefect task to convert amount to EUR.

    Args:
        amount: Amount to convert
        currency: Source currency code
        fx_rates: Optional FX rates dict (fetched if not provided)

    Returns:
        Tuple of (converted_amount, EUR)
    """
    logger_instance = get_run_logger()

    if currency.upper() == "EUR":
        logger_instance.debug(f"Amount already in EUR: {amount}")
        return amount, "EUR"

    if fx_rates is None:
        fx_rates = FXRateManager.get_rates()

    converted = FXRateManager.convert(amount, currency, "EUR")
    logger_instance.info(f"Converted {amount} {currency} to {converted} EUR")

    return converted, "EUR"


@task
def save_fx_rates_to_parquet(
    fx_rates: Dict[str, float],
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> str:
    """Save FX rates to Parquet file for record-keeping.

    Args:
        fx_rates: Dict of FX rates
        output_dir: Output directory for parquet file

    Returns:
        Path to saved parquet file
    """
    logger_instance = get_run_logger()

    try:
        from .parquet_db import ParquetDB
        
        # Create DataFrame with proper schema for FX_RATES table
        df = pd.DataFrame(
            [
                {
                    "from_currency": curr,
                    "to_currency": "EUR",
                    "rate": rate,
                    "timestamp": pd.Timestamp.now(),
                    "source": "Alpha Vantage",
                    "created_at": pd.Timestamp.now(),
                    "updated_at": pd.Timestamp.now(),
                }
                for curr, rate in fx_rates.items()
            ]
        )

        # Use ParquetDB for optimized storage with partitioning
        db = ParquetDB(output_dir)
        inserted, updated = db.upsert_fx_rates(df)
        
        logger_instance.info(f"FX rates saved: {inserted} new, {updated} updated")
        return f"fx_rates_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"

    except Exception as e:
        logger_instance.error(f"Error saving FX rates to parquet: {e}")
        raise


def convert_holdings_to_eur(
    holdings_df: pd.DataFrame,
    fx_rates: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Convert all break-even prices and values in holdings to EUR.

    Args:
        holdings_df: DataFrame with holdings (must have 'bep' and 'ccy' columns)
        fx_rates: Optional FX rates dict (fetched if not provided)

    Returns:
        DataFrame with new columns for EUR values
    """
    result = holdings_df.copy()

    if fx_rates is None:
        fx_rates = FXRateManager.get_rates()

    # Convert BEP to EUR
    result["bep_eur"] = result.apply(
        lambda row: FXRateManager.convert(
            row["bep"], row.get("ccy", "EUR"), "EUR"
        ),
        axis=1,
    )

    # Calculate cost basis in EUR
    result["cost_basis_eur"] = result["qty"] * result["bep_eur"]

    return result
