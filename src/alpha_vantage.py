"""
Alpha Vantage integration for fundamental financial data.

Provides tasks and flows for fetching and analyzing company fundamentals.
"""

import os
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from prefect import flow, get_run_logger, task

from .config import config
from .constants import (
    ALPHA_VANTAGE_BASE_URL,
    ALPHA_VANTAGE_RATE_LIMIT_DELAY,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT,
)
from .exceptions import APIKeyError
from .utils import format_timestamp, get_logger, validate_ticker

__all__ = [
    "fetch_fundamental_data",
    "save_fundamentals_to_parquet",
    "fetch_fundamentals",
]

logger = get_logger(__name__)


# Fundamental data fields from Alpha Vantage API
FUNDAMENTAL_FIELDS = {
    "ticker": "ticker",
    "name": "Name",
    "sector": "Sector",
    "industry": "Industry",
    "market_cap": "MarketCapitalization",
    "pe_ratio": "PERatio",
    "eps": "EPS",
    "revenue": "RevenueTTM",
    "gross_profit_margin": "GrossProfitMargin",
    "profit_margin": "ProfitMargin",
    "operating_margin": "OperatingMarginTTM",
    "roe": "ReturnOnEquityTTM",
    "roa": "ReturnOnAssetsTTM",
    "debt_to_equity": "DebtToEquity",
    "book_value": "BookValue",
    "price_to_book": "PriceToBookRatio",
    "dividend_yield": "DividendYield",
}


@task(retries=3, retry_delay_seconds=5)
def fetch_fundamental_data(ticker: str) -> Optional[dict]:
    """
    Fetch fundamental financial data from Alpha Vantage.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dictionary containing fundamental financial metrics,
        or None if fetch fails.

    Raises:
        APIKeyError: If API key is not configured.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching fundamental data for {ticker}")

    if not validate_ticker(ticker):
        logger_instance.warning(f"Invalid ticker format: {ticker}")
        return None

    try:
        api_key = config.get_alpha_vantage_key()

        # Fetch overview data
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": api_key,
        }

        response = requests.get(
            ALPHA_VANTAGE_BASE_URL, params=params, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if "Error Message" in data:
            logger_instance.error(f"Alpha Vantage error: {data['Error Message']}")
            return None

        # Extract key fundamentals
        fundamentals: dict[str, str] = {"ticker": ticker}
        for key, field in FUNDAMENTAL_FIELDS.items():
            if key != "ticker":
                fundamentals[key] = data.get(field, "N/A")

        fundamentals["updated_at"] = datetime.now().isoformat()

        logger_instance.info(f"Retrieved fundamentals for {ticker}")
        return fundamentals

    except APIKeyError as e:
        logger_instance.error(f"API key error: {e}")
        raise
    except Exception as e:
        logger_instance.error(f"Error fetching fundamental data for {ticker}: {e}")
        return None


@task
def save_fundamentals_to_parquet(
    fundamentals_list: list[dict], output_dir: str = DEFAULT_OUTPUT_DIR
) -> str:
    """
    Save fundamental data to Parquet file.

    Args:
        fundamentals_list: List of fundamental data dictionaries.
        output_dir: Output directory.

    Returns:
        Path to saved Parquet file.

    Raises:
        IOError: If file cannot be written.
    """
    logger_instance = get_run_logger()
    logger_instance.info(
        f"Saving {len(fundamentals_list)} companies' fundamental data"
    )

    try:
        os.makedirs(output_dir, exist_ok=True)

        df = pd.DataFrame(fundamentals_list)
        timestamp = format_timestamp()
        output_file = f"{output_dir}/fundamentals_{timestamp}.parquet"

        df.to_parquet(
            output_file, engine="pyarrow", compression="snappy", index=False
        )
        logger_instance.info(f"Saved fundamentals to {output_file}")
        return output_file

    except Exception as e:
        logger_instance.error(f"Error saving fundamentals: {e}")
        raise


@flow(name="Fundamental Analysis Flow")
def fetch_fundamentals(tickers: list[str]) -> list[dict]:
    """
    Prefect flow to fetch fundamental data for multiple companies.

    Args:
        tickers: List of stock ticker symbols.

    Returns:
        List of fundamental data dictionaries.
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Starting fundamental analysis for tickers: {tickers}")

    fundamentals_list = []

    for ticker in tickers:
        logger_instance.info(f"Fetching fundamentals for {ticker}")
        fundamentals = fetch_fundamental_data(ticker)
        if fundamentals:
            fundamentals_list.append(fundamentals)

        # Respect API rate limits (5 requests/min for free tier)
        time.sleep(ALPHA_VANTAGE_RATE_LIMIT_DELAY)

    if fundamentals_list:
        output_file = save_fundamentals_to_parquet(fundamentals_list)
        logger_instance.info(f"Fundamental data saved to {output_file}")

    return fundamentals_list


def main() -> None:
    """Run fundamental analysis on example companies."""
    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = fetch_fundamentals(tickers)
    print(f"\nFetched fundamentals for {len(results)} companies!")


if __name__ == "__main__":
    main()

