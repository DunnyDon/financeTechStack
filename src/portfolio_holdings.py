"""
Portfolio holdings management and parsing.

Handles loading, parsing, and managing the portfolio holdings from CSV.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from prefect import get_run_logger, task

from .utils import get_logger

__all__ = [
    "load_holdings",
    "parse_holdings",
    "get_holdings_summary",
    "Holdings",
]

logger = get_logger(__name__)


class Holdings:
    """Portfolio holdings manager."""

    def __init__(self, holdings_file: str = "holdings.csv"):
        """
        Initialize holdings manager.

        Args:
            holdings_file: Path to holdings CSV file
        """
        self.holdings_file = holdings_file
        self.df: Optional[pd.DataFrame] = None
        self.load()

    def load(self):
        """Load holdings from CSV file."""
        if not os.path.exists(self.holdings_file):
            logger.error(f"Holdings file not found: {self.holdings_file}")
            self.df = pd.DataFrame()
            return

        try:
            self.df = pd.read_csv(self.holdings_file)
            # Clean up column names
            self.df.columns = self.df.columns.str.strip().str.lower()
            logger.info(f"Loaded {len(self.df)} holdings from {self.holdings_file}")
        except Exception as e:
            logger.error(f"Error loading holdings: {e}")
            self.df = pd.DataFrame()

    def get_by_symbol(self, symbol: str) -> Optional[pd.Series]:
        """
        Get holding by symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Holding as pandas Series or None
        """
        if self.df.empty:
            return None

        matches = self.df[self.df["sym"].str.upper() == symbol.upper()]
        if len(matches) > 0:
            return matches.iloc[0]
        return None

    def get_by_broker(self, broker: str) -> pd.DataFrame:
        """
        Get holdings by broker.

        Args:
            broker: Broker name (e.g., 'DEGIRO')

        Returns:
            DataFrame of holdings from that broker
        """
        if self.df.empty:
            return pd.DataFrame()

        return self.df[self.df["brokerid"].str.upper() == broker.upper()].copy()

    def get_by_asset_type(self, asset_type: str) -> pd.DataFrame:
        """
        Get holdings by asset type.

        Args:
            asset_type: Asset type (eq, fund, crypto, commodity)

        Returns:
            DataFrame of holdings of that type
        """
        if self.df.empty:
            return pd.DataFrame()

        return self.df[self.df["asset"] == asset_type].copy()

    def get_equities(self) -> pd.DataFrame:
        """Get all equity holdings."""
        return self.get_by_asset_type("eq")

    def get_funds(self) -> pd.DataFrame:
        """Get all fund holdings."""
        return self.get_by_asset_type("fund")

    def get_crypto(self) -> pd.DataFrame:
        """Get all crypto holdings."""
        return self.get_by_asset_type("crypto")

    def get_commodities(self) -> pd.DataFrame:
        """Get all commodity holdings."""
        return self.get_by_asset_type("commodity")

    def get_by_exchange(self, exchange: str) -> pd.DataFrame:
        """
        Get holdings by exchange.

        Args:
            exchange: Exchange name (nyse, nasdaq, lse, etc.)

        Returns:
            DataFrame of holdings on that exchange
        """
        if self.df.empty:
            return pd.DataFrame()

        return self.df[self.df["exchange"].str.lower() == exchange.lower()].copy()

    def get_unique_symbols(self) -> List[str]:
        """Get list of unique symbols in portfolio."""
        if self.df.empty:
            return []
        return self.df["sym"].unique().tolist()

    def get_unique_brokers(self) -> List[str]:
        """Get list of unique brokers."""
        if self.df.empty:
            return []
        return self.df["brokerid"].unique().tolist()

    def get_summary(self) -> Dict:
        """
        Get portfolio summary statistics.

        Returns:
            Dictionary with summary stats
        """
        if self.df.empty:
            return {
                "total_holdings": 0,
                "total_quantity": 0,
                "total_cost_basis": 0,
                "by_asset_type": {},
                "by_broker": {},
            }

        summary = {
            "total_holdings": len(self.df),
            "total_quantity": self.df["qty"].sum(),
            "total_cost_basis": (self.df["qty"] * self.df["bep"]).sum(),
            "by_asset_type": self.df["asset"].value_counts().to_dict(),
            "by_broker": self.df["brokerid"].value_counts().to_dict(),
            "by_currency": self.df["ccy"].value_counts().to_dict(),
        }

        return summary

    @property
    def all_holdings(self) -> pd.DataFrame:
        """Get all holdings."""
        return self.df.copy() if not self.df.empty else pd.DataFrame()


@task
def load_holdings(holdings_file: str = "holdings.csv") -> Holdings:
    """
    Load portfolio holdings.

    Args:
        holdings_file: Path to holdings CSV file

    Returns:
        Holdings object with loaded portfolio data
    """
    logger_instance = get_run_logger()
    logger_instance.info(f"Loading holdings from {holdings_file}")

    holdings = Holdings(holdings_file)

    if not holdings.df.empty:
        summary = holdings.get_summary()
        logger_instance.info(f"Portfolio summary: {summary['total_holdings']} holdings")
        logger_instance.info(f"Total cost basis: €{summary['total_cost_basis']:.2f}")

    return holdings


@task
def parse_holdings(holdings: Holdings) -> pd.DataFrame:
    """
    Parse holdings into analysis format.

    Args:
        holdings: Holdings object

    Returns:
        DataFrame ready for analysis
    """
    logger_instance = get_run_logger()

    df = holdings.all_holdings

    if df.empty:
        logger_instance.warning("No holdings to parse")
        return df

    # Ensure numeric columns
    numeric_cols = ["qty", "bep"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add derived columns
    df["cost_basis"] = df["qty"] * df["bep"]
    df["symbol_normalized"] = df["sym"].str.upper()

    logger_instance.info(f"Parsed {len(df)} holdings for analysis")

    return df
