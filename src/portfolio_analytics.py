"""
Portfolio analytics and P&L tracking.

Calculates portfolio performance metrics including:
- Unrealized P&L
- Realized P&L
- Position weights
- Returns (absolute and percentage)
- Performance by sector/asset class
- All values converted to EUR using FX rates
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from prefect import get_run_logger, task

from .fx_rates import FXRateManager
from .utils import get_logger

__all__ = [
    "calculate_pnl",
    "calculate_portfolio_metrics",
    "PortfolioAnalytics",
]

logger = get_logger(__name__)


class PortfolioAnalytics:
    """Calculate portfolio performance and P&L."""

    def __init__(
        self,
        holdings_df: pd.DataFrame,
        prices_dict: Dict[str, Dict],
        fx_rates: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize portfolio analytics.

        Args:
            holdings_df: DataFrame with holdings (sym, qty, bep, ccy)
            prices_dict: Dict of symbol to price data
            fx_rates: Optional dict of FX rates (fetched if not provided)
        """
        self.holdings_df = holdings_df.copy()
        self.prices_dict = prices_dict
        self.fx_rates = fx_rates or FXRateManager.get_rates()
        self.current_prices = self._extract_prices()

    def _extract_prices(self) -> Dict[str, float]:
        """Extract current prices from price dictionary."""
        prices = {}

        for symbol, price_data in self.prices_dict.items():
            if isinstance(price_data, dict):
                if "price" in price_data:
                    prices[symbol] = float(price_data["price"])
                elif "price_usd" in price_data:
                    prices[symbol] = float(price_data["price_usd"])
                elif "price_eur" in price_data:
                    prices[symbol] = float(price_data["price_eur"])

        return prices

    def calculate_unrealized_pnl(self) -> pd.DataFrame:
        """
        Calculate unrealized P&L for each position in EUR.

        Returns:
            DataFrame with P&L calculations (all values in EUR)
        """
        result = self.holdings_df.copy()

        # Get current prices for each symbol
        result["current_price"] = result["sym"].map(self.current_prices)

        # Skip rows without current price
        result = result[result["current_price"].notna()].copy()

        # Convert BEP to EUR if not already
        result["bep_eur"] = result.apply(
            lambda row: FXRateManager.convert(
                row["bep"], row.get("ccy", "EUR"), "EUR"
            ),
            axis=1,
        )

        # Convert current price to EUR (prices are typically in the security's native currency or USD)
        # We assume prices are in USD for international stocks, so convert accordingly
        result["current_price_eur"] = result.apply(
            lambda row: FXRateManager.convert(
                row["current_price"], "USD", "EUR"
            ),  # Most prices are in USD, adjust logic if needed
            axis=1,
        )

        # Calculate values in EUR
        result["cost_basis_eur"] = result["qty"] * result["bep_eur"]
        result["current_value_eur"] = result["qty"] * result["current_price_eur"]
        result["unrealized_pnl_eur"] = result["current_value_eur"] - result["cost_basis_eur"]
        result["pnl_percent"] = (
            (result["unrealized_pnl_eur"] / result["cost_basis_eur"]) * 100
        )

        # Calculate return (in %)
        result["return_pct"] = (
            ((result["current_price_eur"] - result["bep_eur"]) / result["bep_eur"]) * 100
        )

        return result

    def portfolio_summary(self) -> Dict:
        """
        Calculate portfolio-level metrics in EUR.

        Returns:
            Dict with portfolio metrics (all values in EUR)
        """
        pnl_df = self.calculate_unrealized_pnl()

        if pnl_df.empty:
            return {
                "total_cost_basis_eur": 0,
                "total_current_value_eur": 0,
                "total_unrealized_pnl_eur": 0,
                "total_pnl_percent": 0,
                "num_positions": 0,
                "currency": "EUR",
                "timestamp": datetime.now().isoformat(),
            }

        total_cost = pnl_df["cost_basis_eur"].sum()
        total_value = pnl_df["current_value_eur"].sum()
        total_pnl = pnl_df["unrealized_pnl_eur"].sum()
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

        return {
            "total_cost_basis_eur": float(total_cost),
            "total_current_value_eur": float(total_value),
            "total_unrealized_pnl_eur": float(total_pnl),
            "total_pnl_percent": float(total_pnl_pct),
            "num_positions": len(pnl_df),
            "num_profitable": int((pnl_df["unrealized_pnl_eur"] > 0).sum()),
            "num_loss": int((pnl_df["unrealized_pnl_eur"] < 0).sum()),
            "win_rate": (
                ((pnl_df["unrealized_pnl_eur"] > 0).sum() / len(pnl_df)) * 100
                if len(pnl_df) > 0
                else 0
            ),
            "currency": "EUR",
            "timestamp": datetime.now().isoformat(),
        }

    def pnl_by_asset_type(self) -> Dict[str, Dict]:
        """
        Calculate P&L by asset type in EUR.

        Returns:
            Dict with metrics by asset type (all values in EUR)
        """
        pnl_df = self.calculate_unrealized_pnl()

        if pnl_df.empty or "asset" not in pnl_df.columns:
            return {}

        result = {}

        for asset_type in pnl_df["asset"].unique():
            subset = pnl_df[pnl_df["asset"] == asset_type]

            cost_basis = subset["cost_basis_eur"].sum()
            current_value = subset["current_value_eur"].sum()
            pnl = subset["unrealized_pnl_eur"].sum()

            result[asset_type] = {
                "cost_basis_eur": float(cost_basis),
                "current_value_eur": float(current_value),
                "unrealized_pnl_eur": float(pnl),
                "pnl_percent": float((pnl / cost_basis) * 100) if cost_basis > 0 else 0,
                "currency": "EUR",
                "num_positions": len(subset),
            }

        return result

    def pnl_by_broker(self) -> Dict[str, Dict]:
        """
        Calculate P&L by broker.

        Returns:
            Dict with metrics by broker
        """
        pnl_df = self.calculate_unrealized_pnl()

        if pnl_df.empty or "brokerid" not in pnl_df.columns:
            return {}

        result = {}

        for broker in pnl_df["brokerid"].unique():
            subset = pnl_df[pnl_df["brokerid"] == broker]

            cost_basis = subset["cost_basis"].sum()
            current_value = subset["current_value"].sum()
            pnl = subset["unrealized_pnl"].sum()

            result[broker] = {
                "cost_basis": float(cost_basis),
                "current_value": float(current_value),
                "unrealized_pnl": float(pnl),
                "pnl_percent": float((pnl / cost_basis) * 100) if cost_basis > 0 else 0,
                "num_positions": len(subset),
            }

        return result

    def top_performers(self, n: int = 10) -> pd.DataFrame:
        """
        Get top N performing positions.

        Args:
            n: Number of positions to return

        Returns:
            DataFrame with top performers
        """
        pnl_df = self.calculate_unrealized_pnl()

        return (
            pnl_df[["sym", "secname", "qty", "current_price", "unrealized_pnl", "pnl_percent"]]
            .sort_values("unrealized_pnl", ascending=False)
            .head(n)
        )

    def worst_performers(self, n: int = 10) -> pd.DataFrame:
        """
        Get worst N performing positions.

        Args:
            n: Number of positions to return

        Returns:
            DataFrame with worst performers
        """
        pnl_df = self.calculate_unrealized_pnl()

        return (
            pnl_df[["sym", "secname", "qty", "current_price", "unrealized_pnl", "pnl_percent"]]
            .sort_values("unrealized_pnl", ascending=True)
            .head(n)
        )

    def position_weights(self) -> pd.DataFrame:
        """
        Calculate portfolio position weights.

        Returns:
            DataFrame with position allocation weights
        """
        pnl_df = self.calculate_unrealized_pnl()

        if pnl_df.empty:
            return pd.DataFrame()

        total_value = pnl_df["current_value"].sum()

        result = pnl_df.copy()
        result["weight_pct"] = (result["current_value"] / total_value) * 100
        result = result.sort_values("weight_pct", ascending=False)

        return result[["sym", "secname", "current_value", "weight_pct"]]


@task
def calculate_pnl(
    holdings_df: pd.DataFrame, prices_dict: Dict[str, Dict]
) -> Dict:
    """
    Calculate portfolio P&L.

    Args:
        holdings_df: DataFrame with holdings
        prices_dict: Dict of current prices

    Returns:
        Dict with P&L data
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating portfolio P&L")

    analytics = PortfolioAnalytics(holdings_df, prices_dict)

    pnl_summary = analytics.portfolio_summary()
    logger_instance.info(
        f"Portfolio: €{pnl_summary['total_current_value']:.2f}, "
        f"P&L: €{pnl_summary['total_unrealized_pnl']:.2f} "
        f"({pnl_summary['total_pnl_percent']:.2f}%)"
    )

    return {
        "summary": pnl_summary,
        "by_asset_type": analytics.pnl_by_asset_type(),
        "by_broker": analytics.pnl_by_broker(),
        "top_performers": analytics.top_performers().to_dict("records"),
        "worst_performers": analytics.worst_performers().to_dict("records"),
    }


@task
def calculate_portfolio_metrics(
    holdings_df: pd.DataFrame, prices_dict: Dict[str, Dict]
) -> Dict:
    """
    Calculate comprehensive portfolio metrics.

    Args:
        holdings_df: DataFrame with holdings
        prices_dict: Dict of current prices

    Returns:
        Dict with portfolio metrics
    """
    logger_instance = get_run_logger()
    logger_instance.info("Calculating portfolio metrics")

    analytics = PortfolioAnalytics(holdings_df, prices_dict)

    pnl_df = analytics.calculate_unrealized_pnl()

    metrics = {
        "summary": analytics.portfolio_summary(),
        "by_asset_type": analytics.pnl_by_asset_type(),
        "by_broker": analytics.pnl_by_broker(),
        "position_weights": analytics.position_weights().to_dict("records"),
        "top_performers": analytics.top_performers().to_dict("records"),
        "worst_performers": analytics.worst_performers().to_dict("records"),
        "positions_with_prices": pnl_df.to_dict("records"),
    }

    return metrics
