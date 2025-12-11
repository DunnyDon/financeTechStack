"""Data loading utilities for backtesting from ParquetDB."""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BacktestDataLoader:
    """Loads and prepares data for backtesting."""

    def __init__(self, parquet_db=None):
        """
        Initialize data loader.

        Args:
            parquet_db: ParquetDB instance (lazy-loaded if None)
        """
        self.db = parquet_db

    def _get_db(self):
        """Get or create ParquetDB instance."""
        if self.db is None:
            from ..parquet_db import ParquetDB
            self.db = ParquetDB()
        return self.db

    def load_backtest_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        resample_freq: str = "D",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load all data needed for backtesting.

        Args:
            symbols: List of ticker symbols
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            resample_freq: Frequency to resample to ("D", "W", "M")

        Returns:
            Tuple of (prices_df, technical_df, fundamental_df)
        """
        db = self._get_db()

        logger.info(
            f"Loading backtest data for {len(symbols)} symbols "
            f"from {start_date} to {end_date}"
        )

        # Load prices using read_table
        prices_df = db.read_table(
            "prices",
            start_date=start_date,
            end_date=end_date
        )
        
        # Filter by symbols if data exists
        if prices_df is not None and "symbol" in prices_df.columns:
            prices_df = prices_df[prices_df["symbol"].isin(symbols)]

        # Load technical indicators
        try:
            technical_df = db.read_table(
                "technical_analysis",
                start_date=start_date,
                end_date=end_date
            )
            if technical_df is not None and "symbol" in technical_df.columns:
                technical_df = technical_df[technical_df["symbol"].isin(symbols)]
        except Exception as e:
            logger.warning(f"Technical data not available: {e}")
            technical_df = pd.DataFrame()

        # Load fundamental metrics
        try:
            fundamental_df = db.read_table(
                "fundamental_analysis",
                start_date=start_date,
                end_date=end_date
            )
            if fundamental_df is not None and "symbol" in fundamental_df.columns:
                fundamental_df = fundamental_df[fundamental_df["symbol"].isin(symbols)]
        except Exception as e:
            logger.warning(f"Fundamental data not available: {e}")
            fundamental_df = pd.DataFrame()

        # Validate data
        if prices_df is None or prices_df.empty:
            logger.warning(f"No price data found for symbols: {symbols}")
            prices_df = pd.DataFrame()
        else:
            logger.info(f"Loaded {len(prices_df)} price records")

        # Ensure DataFrames are not None
        if technical_df is None:
            technical_df = pd.DataFrame()
        if fundamental_df is None:
            fundamental_df = pd.DataFrame()

        # Set proper timestamp index if available
        if prices_df is not None and not prices_df.empty:
            if "timestamp" in prices_df.columns:
                prices_df = prices_df.set_index("timestamp")
            elif "date" in prices_df.columns:
                prices_df = prices_df.set_index("date")

        if technical_df is not None and not technical_df.empty:
            if "timestamp" in technical_df.columns:
                technical_df = technical_df.set_index("timestamp")
            elif "date" in technical_df.columns:
                technical_df = technical_df.set_index("date")

        if fundamental_df is not None and not fundamental_df.empty:
            if "timestamp" in fundamental_df.columns:
                fundamental_df = fundamental_df.set_index("timestamp")
            elif "date" in fundamental_df.columns:
                fundamental_df = fundamental_df.set_index("date")

        # Resample if needed
        if resample_freq != "D" and not prices_df.empty:
            prices_df = self._resample_ohlcv(prices_df, resample_freq)
            if not technical_df.empty:
                technical_df = technical_df.resample(resample_freq).mean()

        return prices_df, technical_df, fundamental_df

    def _resample_ohlcv(
        self, prices_df: pd.DataFrame, freq: str
    ) -> pd.DataFrame:
        """
        Resample OHLCV data to new frequency.

        Args:
            prices_df: Price data with OHLCV columns
            freq: Target frequency ("W", "M", etc.)

        Returns:
            Resampled price data
        """
        required_columns = [
            "symbol",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]

        if not all(col in prices_df.columns for col in required_columns):
            logger.warning(
                f"Missing required columns for resampling: {required_columns}"
            )
            return prices_df

        # Group by symbol and resample
        resampled_list = []

        for symbol, group in prices_df.groupby("symbol"):
            group = group.set_index("timestamp") if "timestamp" in group.columns else group

            resampled = group.resample(freq).agg({
                "open_price": "first",
                "high_price": "max",
                "low_price": "min",
                "close_price": "last",
                "volume": "sum",
            })

            resampled["symbol"] = symbol
            resampled_list.append(resampled)

        if resampled_list:
            result = pd.concat(resampled_list).reset_index()
            return result

        return prices_df

    def load_holdings(
        self, holdings_file: str = "holdings.csv"
    ) -> pd.DataFrame:
        """
        Load portfolio holdings.

        Args:
            holdings_file: Path to holdings CSV file

        Returns:
            Holdings DataFrame
        """
        try:
            holdings = pd.read_csv(holdings_file)
            logger.info(f"Loaded {len(holdings)} holdings from {holdings_file}")
            return holdings
        except Exception as e:
            logger.error(f"Failed to load holdings: {e}")
            raise

    def validate_data(
        self,
        prices_df: pd.DataFrame,
        symbols: List[str],
        min_records: int = 20,
    ) -> Dict[str, bool]:
        """
        Validate loaded data.

        Args:
            prices_df: Price data to validate
            symbols: Expected symbols
            min_records: Minimum records per symbol

        Returns:
            Dictionary of validation results
        """
        results = {}

        for symbol in symbols:
            sym_data = prices_df[prices_df["symbol"] == symbol]
            
            has_data = len(sym_data) >= min_records
            results[symbol] = has_data

            if not has_data:
                logger.warning(
                    f"Insufficient data for {symbol}: "
                    f"{len(sym_data)} records (need {min_records})"
                )

        return results

    def get_date_range(self, prices_df: pd.DataFrame) -> Tuple[str, str]:
        """
        Get available date range from price data.

        Args:
            prices_df: Price data

        Returns:
            Tuple of (start_date, end_date) as strings
        """
        if prices_df.empty:
            return None, None

        dates = pd.to_datetime(prices_df.index)
        start = dates.min().strftime("%Y-%m-%d")
        end = dates.max().strftime("%Y-%m-%d")

        return start, end
