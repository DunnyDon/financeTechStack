"""
Technical analysis indicators for portfolio securities.

Implements:
- Bollinger Bands
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Moving Averages (SMA, EMA)
- Volume analysis
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from prefect import get_run_logger, task

from .utils import get_logger

__all__ = [
    "bollinger_bands",
    "rsi",
    "macd",
    "moving_averages",
    "calculate_technical_indicators",
    "TechnicalAnalyzer",
]

logger = get_logger(__name__)


class TechnicalAnalyzer:
    """Calculate technical analysis indicators."""

    @staticmethod
    def bollinger_bands(
        prices: pd.Series, period: int = 20, num_std: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: Series of prices
            period: Period for moving average (default 20)
            num_std: Number of standard deviations (default 2.0)

        Returns:
            Dict with 'middle', 'upper', 'lower', 'bb_width', 'bb_pct'
        """
        if len(prices) < period:
            return {}

        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper = middle + (std * num_std)
        lower = middle - (std * num_std)

        bb_width = upper - lower
        bb_pct = (prices - lower) / (upper - lower)

        return {
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
            "bb_width": bb_width,
            "bb_pct": bb_pct,  # 0-1, where 1 = at upper, 0 = at lower
        }

    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: Series of prices
            period: Period for RSI calculation (default 14)

        Returns:
            Series with RSI values (0-100)
        """
        if len(prices) < period + 1:
            return pd.Series(index=prices.index, dtype=float)

        # Calculate price changes
        deltas = prices.diff()

        # Separate gains and losses
        gains = deltas.where(deltas > 0, 0.0)
        losses = -deltas.where(deltas < 0, 0.0)

        # Calculate averages
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()

        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, 1e-10)

        # Calculate RSI
        rsi_values = 100 - (100 / (1 + rs))

        return rsi_values

    @staticmethod
    def macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Series of prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)

        Returns:
            Dict with 'macd', 'signal', 'histogram'
        """
        if len(prices) < slow_period + signal_period:
            return {}

        # Calculate EMAs
        ema_fast = prices.ewm(span=fast_period).mean()
        ema_slow = prices.ewm(span=slow_period).mean()

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal = macd_line.ewm(span=signal_period).mean()

        # Histogram
        histogram = macd_line - signal

        return {
            "macd": macd_line,
            "signal": signal,
            "histogram": histogram,
        }

    @staticmethod
    def moving_averages(
        prices: pd.Series, short_period: int = 20, long_period: int = 50
    ) -> Dict[str, pd.Series]:
        """
        Calculate moving averages.

        Args:
            prices: Series of prices
            short_period: Short MA period (default 20)
            long_period: Long MA period (default 50)

        Returns:
            Dict with 'sma_short', 'sma_long', 'ema_short', 'ema_long'
        """
        return {
            "sma_short": prices.rolling(window=short_period).mean(),
            "sma_long": prices.rolling(window=long_period).mean(),
            "ema_short": prices.ewm(span=short_period).mean(),
            "ema_long": prices.ewm(span=long_period).mean(),
        }

    @staticmethod
    def volume_indicators(
        ohlcv_df: pd.DataFrame, period: int = 20
    ) -> Dict[str, pd.Series]:
        """
        Calculate volume-based indicators.

        Args:
            ohlcv_df: DataFrame with Open, High, Low, Close, Volume columns
            period: Period for calculations

        Returns:
            Dict with volume indicators
        """
        if "Volume" not in ohlcv_df.columns or "Close" not in ohlcv_df.columns:
            return {}

        close = ohlcv_df["Close"]
        volume = ohlcv_df["Volume"]

        # On-Balance Volume (OBV)
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        # Volume Moving Average
        vol_ma = volume.rolling(window=period).mean()

        # Relative Volume
        rel_vol = volume / vol_ma

        return {
            "obv": obv,
            "volume_ma": vol_ma,
            "relative_volume": rel_vol,
        }

    @staticmethod
    def calculate_all(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators.

        Args:
            ohlcv_df: DataFrame with OHLCV data

        Returns:
            DataFrame with original + technical indicator columns
        """
        if ohlcv_df.empty or "Close" not in ohlcv_df.columns:
            return ohlcv_df

        result_df = ohlcv_df.copy()

        close_prices = ohlcv_df["Close"]

        # Bollinger Bands
        bb = TechnicalAnalyzer.bollinger_bands(close_prices)
        for key, series in bb.items():
            result_df[key] = series

        # RSI
        result_df["rsi"] = TechnicalAnalyzer.rsi(close_prices)

        # MACD
        macd = TechnicalAnalyzer.macd(close_prices)
        for key, series in macd.items():
            result_df[key] = series

        # Moving Averages
        ma = TechnicalAnalyzer.moving_averages(close_prices)
        for key, series in ma.items():
            result_df[key] = series

        # Volume Indicators
        if "Volume" in ohlcv_df.columns:
            vol = TechnicalAnalyzer.volume_indicators(ohlcv_df)
            for key, series in vol.items():
                result_df[key] = series

        return result_df


@task
def bollinger_bands(
    prices: pd.Series, period: int = 20, num_std: float = 2.0
) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        prices: Series of prices
        period: Period for moving average
        num_std: Number of standard deviations

    Returns:
        Dict with Bollinger Band components
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Calculating Bollinger Bands (period={period}, std={num_std})")

    return TechnicalAnalyzer.bollinger_bands(prices, period, num_std)


@task
def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI indicator.

    Args:
        prices: Series of prices
        period: Period for calculation

    Returns:
        Series with RSI values
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Calculating RSI (period={period})")

    return TechnicalAnalyzer.rsi(prices, period)


@task
def macd(prices: pd.Series) -> Dict[str, pd.Series]:
    """
    Calculate MACD indicator.

    Args:
        prices: Series of prices

    Returns:
        Dict with MACD, Signal, and Histogram
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating MACD")

    return TechnicalAnalyzer.macd(prices)


@task
def moving_averages(prices: pd.Series) -> Dict[str, pd.Series]:
    """
    Calculate moving averages.

    Args:
        prices: Series of prices

    Returns:
        Dict with MA values
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating moving averages")

    return TechnicalAnalyzer.moving_averages(prices)


@task
def calculate_technical_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators for a security.

    Args:
        ohlcv_df: DataFrame with OHLCV data

    Returns:
        DataFrame with technical indicators added
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Calculating all technical indicators ({len(ohlcv_df)} rows)")

    return TechnicalAnalyzer.calculate_all(ohlcv_df)
