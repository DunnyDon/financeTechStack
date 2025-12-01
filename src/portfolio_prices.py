"""
Price fetching from multiple sources.

Fetches current and historical price quotes for securities using:
- yfinance for stocks, ETFs, commodities
- Alpha Vantage for additional sources
- CoinGecko for cryptocurrencies
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from prefect import get_run_logger, task

from .constants import DEFAULT_TIMEOUT
from .utils import get_logger, make_request_with_backoff

__all__ = [
    "fetch_current_price",
    "fetch_historical_prices",
    "fetch_multiple_prices",
    "PriceFetcher",
]

logger = get_logger(__name__)

# Try to import yfinance, but don't fail if it's not available
try:
    import yfinance as yf

    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    logger.warning("yfinance not installed - install with: pip install yfinance")


class PriceFetcher:
    """Fetch security prices from multiple sources."""

    def __init__(self):
        """Initialize price fetcher."""
        self.cache: Dict[str, Dict] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=5)

    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cache entry is still valid."""
        if symbol not in self.cache_timestamp:
            return False

        age = datetime.now() - self.cache_timestamp[symbol]
        return age < self.cache_duration

    def fetch_from_yfinance(self, symbol: str) -> Optional[Dict]:
        """
        Fetch price from yfinance.

        Args:
            symbol: Security symbol (e.g., 'AAPL')

        Returns:
            Dict with price data or None if fetch failed
        """
        if not HAS_YFINANCE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")

            if data.empty:
                logger.warning(f"No data from yfinance for {symbol}")
                return None

            latest = data.iloc[-1]
            return {
                "symbol": symbol,
                "price": float(latest["Close"]),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "volume": int(latest["Volume"]),
                "timestamp": datetime.now().isoformat(),
                "source": "yfinance",
            }
        except Exception as e:
            logger.error(f"Error fetching {symbol} from yfinance: {e}")
            return None

    def fetch_from_alpha_vantage(
        self, symbol: str, api_key: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Fetch price from Alpha Vantage.

        Args:
            symbol: Security symbol
            api_key: Alpha Vantage API key (uses env var if not provided)

        Returns:
            Dict with price data or None if fetch failed
        """
        if not api_key:
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

        if not api_key:
            logger.debug("Alpha Vantage API key not configured")
            return None

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": api_key,
            }

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" not in data or not data["Global Quote"].get("05. price"):
                logger.warning(f"No price data from Alpha Vantage for {symbol}")
                return None

            quote = data["Global Quote"]
            return {
                "symbol": symbol,
                "price": float(quote["05. price"]),
                "open": float(quote.get("02. open", 0)),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "timestamp": datetime.now().isoformat(),
                "source": "alpha_vantage",
            }
        except Exception as e:
            logger.error(f"Error fetching {symbol} from Alpha Vantage: {e}")
            return None

    def fetch_crypto_price(self, symbol: str) -> Optional[Dict]:
        """
        Fetch cryptocurrency price from CoinGecko.

        Args:
            symbol: Crypto symbol (Bitcoin, Ethereum, XRP, etc.)

        Returns:
            Dict with price data or None if fetch failed
        """
        try:
            # Map common symbols to CoinGecko IDs
            symbol_map = {
                "BTC": "bitcoin",
                "BITCOIN": "bitcoin",
                "ETH": "ethereum",
                "ETHEREUM": "ethereum",
                "XRP": "ripple",
                "RIPPLE": "ripple",
                "BNB": "binancecoin",
                "ADA": "cardano",
                "SOL": "solana",
            }

            coin_id = symbol_map.get(symbol.upper(), symbol.lower())

            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd,eur",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            }

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if coin_id not in data:
                logger.warning(f"Crypto symbol {symbol} not found on CoinGecko")
                return None

            prices = data[coin_id]
            return {
                "symbol": symbol,
                "price_usd": float(prices.get("usd", 0)),
                "price_eur": float(prices.get("eur", 0)),
                "market_cap_usd": prices.get("usd_market_cap"),
                "volume_24h_usd": prices.get("usd_24h_vol"),
                "timestamp": datetime.now().isoformat(),
                "source": "coingecko",
            }
        except Exception as e:
            logger.error(f"Error fetching crypto {symbol}: {e}")
            return None

    def fetch_price(self, symbol: str, asset_type: str = "eq") -> Optional[Dict]:
        """
        Fetch price for any security type.

        Args:
            symbol: Security symbol
            asset_type: Type of asset (eq, fund, crypto, commodity)

        Returns:
            Dict with price data or None if fetch failed
        """
        # Check cache first
        if self._is_cache_valid(symbol):
            logger.debug(f"Using cached price for {symbol}")
            return self.cache[symbol]

        # Fetch based on asset type
        if asset_type == "crypto":
            result = self.fetch_crypto_price(symbol)
        elif asset_type == "commodity":
            result = self.fetch_from_yfinance(symbol)
        else:
            # Try yfinance first, then Alpha Vantage
            result = self.fetch_from_yfinance(symbol)
            if not result:
                result = self.fetch_from_alpha_vantage(symbol)

        # Cache successful results
        if result:
            self.cache[symbol] = result
            self.cache_timestamp[symbol] = datetime.now()

        return result

    def fetch_historical(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data.

        Args:
            symbol: Security symbol
            start_date: Start date (YYYY-MM-DD) - overrides period
            end_date: End date (YYYY-MM-DD)
            period: Period if start_date not specified (1d, 5d, 1mo, 3mo, 6mo, 1y, etc.)

        Returns:
            DataFrame with OHLCV data or None if fetch failed
        """
        if not HAS_YFINANCE:
            logger.error("yfinance required for historical data")
            return None

        try:
            ticker = yf.Ticker(symbol)

            if start_date:
                data = ticker.history(start=start_date, end=end_date or datetime.now())
            else:
                data = ticker.history(period=period)

            if data.empty:
                logger.warning(f"No historical data for {symbol}")
                return None

            # Add technical indicators columns
            data["symbol"] = symbol

            return data.reset_index()

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None


@task
def fetch_current_price(symbol: str, asset_type: str = "eq") -> Optional[Dict]:
    """
    Fetch current price for a security.

    Args:
        symbol: Security symbol
        asset_type: Type of asset (eq, fund, crypto, commodity)

    Returns:
        Dict with current price data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching price for {symbol} (type: {asset_type})")

    fetcher = PriceFetcher()
    price_data = fetcher.fetch_price(symbol, asset_type)

    if price_data:
        logger_instance.info(f"Price for {symbol}: {price_data.get('price', price_data.get('price_usd'))}")

    return price_data


@task
def fetch_historical_prices(
    symbol: str,
    start_date: Optional[str] = None,
    period: str = "1y",
) -> Optional[pd.DataFrame]:
    """
    Fetch historical prices for a security.

    Args:
        symbol: Security symbol
        start_date: Start date (YYYY-MM-DD)
        period: Period if start_date not specified

    Returns:
        DataFrame with OHLCV data or None
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching {period} historical prices for {symbol}")

    fetcher = PriceFetcher()
    return fetcher.fetch_historical(symbol, start_date, period=period)


@task
def fetch_multiple_prices(symbols: List[str], asset_types: Dict[str, str]) -> Dict[str, Dict]:
    """
    Fetch prices for multiple securities.

    Args:
        symbols: List of security symbols
        asset_types: Dict mapping symbol to asset type

    Returns:
        Dict with price data for each symbol
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Fetching prices for {len(symbols)} securities")

    fetcher = PriceFetcher()
    results = {}

    for symbol in symbols:
        asset_type = asset_types.get(symbol, "eq")
        price_data = fetcher.fetch_price(symbol, asset_type)

        if price_data:
            results[symbol] = price_data

    logger_instance.info(f"Successfully fetched {len(results)} prices")

    return results
