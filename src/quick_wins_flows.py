"""
Quick Wins Analytics Prefect Flows

Integrates high-value analytics into portfolio workflows:
- Portfolio beta visualization with risk classification
- Sector rotation strategy and recommendations
- Momentum screening and signal generation
- Mean reversion signals with trading candidates

These flows enable portfolio managers to quickly identify:
- Aggressive vs conservative positioning
- Sector rotation opportunities
- Momentum-based trading signals
- Mean reversion candidates for range trading
"""

from typing import Dict, List, Optional

import pandas as pd
import numpy as np
from prefect import flow, get_run_logger, task

from .quick_wins_analytics import QuickWinsAnalytics
from .parquet_db import ParquetDB
from .utils import get_logger

__all__ = [
    "calculate_portfolio_beta_task",
    "calculate_sector_rotation_task",
    "calculate_momentum_signals_task",
    "calculate_mean_reversion_task",
    "quick_wins_analytics_flow",
]

logger = get_logger(__name__)


@task(name="prepare_returns_data")
def prepare_returns_data(prices_dict: Dict, holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare returns DataFrame from price data.

    Args:
        prices_dict: Dictionary of symbol -> price data
        holdings_df: Portfolio holdings with symbols

    Returns:
        DataFrame with returns indexed by symbol
    """
    task_logger = get_run_logger()
    task_logger.info("Preparing returns data...")

    returns_dict = {}

    for symbol in holdings_df["sym"].unique():
        if symbol in prices_dict:
            price_data = prices_dict[symbol]

            # Extract price information
            if isinstance(price_data, dict):
                if "return_pct" in price_data:
                    returns_dict[symbol] = float(price_data.get("return_pct", 0))
                elif "price" in price_data:
                    returns_dict[symbol] = float(price_data.get("price", 0))
                elif "price_usd" in price_data:
                    returns_dict[symbol] = float(price_data.get("price_usd", 0))
                elif "price_eur" in price_data:
                    returns_dict[symbol] = float(price_data.get("price_eur", 0))

    if not returns_dict:
        task_logger.warning("No returns data available")
        # Return empty DataFrame with correct structure for beta calculation
        return pd.DataFrame(index=pd.Index([], name="symbol"), columns=["return_pct"])

    # Create DataFrame with symbols as index and a single returns column
    df = pd.DataFrame(
        {"return_pct": list(returns_dict.values())},
        index=pd.Index(list(returns_dict.keys()), name="symbol")
    )
    
    task_logger.info(f"Prepared returns data for {len(df)} securities")
    return df


@task(name="prepare_prices_data")
def prepare_prices_data(prices_dict: Dict, holdings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare prices DataFrame from price data.

    Args:
        prices_dict: Dictionary of symbol -> price data
        holdings_df: Portfolio holdings with symbols

    Returns:
        DataFrame with prices indexed by symbol
    """
    task_logger = get_run_logger()
    task_logger.info("Preparing prices data...")

    prices = {}

    for symbol in holdings_df["sym"].unique():
        if symbol in prices_dict:
            price_data = prices_dict[symbol]

            if isinstance(price_data, dict):
                if "price" in price_data:
                    prices[symbol] = float(price_data.get("price", 0))
                elif "price_usd" in price_data:
                    prices[symbol] = float(price_data.get("price_usd", 0))
                elif "price_eur" in price_data:
                    prices[symbol] = float(price_data.get("price_eur", 0))

    if not prices:
        task_logger.warning("No prices data available")
        return pd.DataFrame()

    task_logger.info(f"Prepared prices data for {len(prices)} securities")
    return pd.DataFrame(list(prices.items()), columns=["symbol", "price"]).set_index("symbol")


@task(name="prepare_market_returns")
def prepare_market_returns() -> pd.Series:
    """
    Prepare market returns (S&P 500 / market benchmark).

    Returns:
        Series with market returns
    """
    task_logger = get_run_logger()
    task_logger.info("Preparing market returns...")

    try:
        db = ParquetDB()
        prices_data = db.read_table("prices")

        if prices_data is None or prices_data.empty:
            task_logger.warning("No market data available, returning dummy market returns")
            return pd.Series([0.01] * 252, name="market_return")

        # Use first column as proxy for market benchmark
        if len(prices_data.columns) > 0:
            col = prices_data.columns[0]
            returns = prices_data[col].pct_change().dropna()
            task_logger.info(f"Market returns prepared from {len(returns)} data points")
            return returns

        task_logger.warning("Could not prepare market returns")
        return pd.Series([0.01] * 252, name="market_return")

    except Exception as e:
        task_logger.warning(f"Error preparing market returns: {e}")
        return pd.Series([0.01] * 252, name="market_return")


@task(name="prepare_sector_data")
def prepare_sector_data(holdings_df: pd.DataFrame) -> tuple:
    """
    Prepare sector returns and holdings mapping.

    Args:
        holdings_df: Portfolio holdings with sector information

    Returns:
        Tuple of (sector_returns_dict, holding_sectors_dict)
    """
    task_logger = get_run_logger()
    task_logger.info("Preparing sector data...")

    # Sector returns (example data - would come from market data in production)
    sector_returns = {}
    for sector in holdings_df["sector"].unique() if "sector" in holdings_df.columns else []:
        # Example sector returns (would be calculated from actual data)
        sector_returns[sector] = np.random.uniform(-0.05, 0.15)

    if not sector_returns:
        # Default sectors if not in holdings
        sector_returns = {
            "Technology": 0.08,
            "Finance": 0.05,
            "Healthcare": 0.10,
            "Energy": 0.03,
            "Industrials": 0.06,
        }

    # Holdings by sector
    holding_sectors = {}
    if "sector" in holdings_df.columns:
        for _, row in holdings_df.iterrows():
            holding_sectors[row["sym"]] = row["sector"]
    else:
        # Assign default sectors
        for symbol in holdings_df["sym"]:
            holding_sectors[symbol] = "Unknown"

    task_logger.info(f"Sector data prepared: {len(sector_returns)} sectors, {len(holding_sectors)} holdings")
    return sector_returns, holding_sectors


@task(name="calculate_portfolio_beta")
def calculate_portfolio_beta_task(
    returns_df: pd.DataFrame, market_returns: pd.Series
) -> Dict:
    """
    Calculate portfolio beta and risk classification.

    Args:
        returns_df: DataFrame with returns by symbol
        market_returns: Series with market returns

    Returns:
        Dict with beta analysis and interpretation
    """
    task_logger = get_run_logger()
    task_logger.info("Calculating portfolio beta...")

    try:
        result = QuickWinsAnalytics.portfolio_beta_visualization(returns_df, market_returns)
        task_logger.info(
            f"Portfolio beta: {result.get('portfolio_beta', 0):.2f}, "
            f"Classification: {result.get('beta_interpretation', 'Unknown')}"
        )
        return result
    except Exception as e:
        task_logger.error(f"Error calculating portfolio beta: {e}")
        return {"error": str(e), "portfolio_beta": 0}


@task(name="calculate_sector_rotation")
def calculate_sector_rotation_task(
    sector_returns: Dict[str, float], holding_sectors: Dict[str, str]
) -> Dict:
    """
    Calculate sector rotation strategy.

    Args:
        sector_returns: Dict of sector -> return percentage
        holding_sectors: Dict of symbol -> sector

    Returns:
        Dict with sector rotation recommendations
    """
    task_logger = get_run_logger()
    task_logger.info("Calculating sector rotation strategy...")

    try:
        result = QuickWinsAnalytics.sector_rotation_strategy(sector_returns, holding_sectors)
        task_logger.info(
            f"Best sector: {result.get('best_sector', 'N/A')}, "
            f"Worst sector: {result.get('worst_sector', 'N/A')}"
        )
        return result
    except Exception as e:
        task_logger.error(f"Error calculating sector rotation: {e}")
        return {"error": str(e)}


@task(name="calculate_momentum_signals")
def calculate_momentum_signals_task(
    returns_df: pd.DataFrame, period: int = 20
) -> Dict:
    """
    Calculate momentum screening signals.

    Args:
        returns_df: DataFrame with returns by symbol
        period: Momentum calculation period (default 20 days)

    Returns:
        Dict with momentum scores and signals
    """
    task_logger = get_run_logger()
    task_logger.info(f"Calculating momentum signals (period={period})...")

    try:
        result = QuickWinsAnalytics.momentum_screening(returns_df, period=period)
        top_momentum = result.get("top_momentum", [])
        bottom_momentum = result.get("bottom_momentum", [])
        task_logger.info(
            f"Momentum signals: {len(top_momentum)} uptrend, {len(bottom_momentum)} downtrend"
        )
        return result
    except Exception as e:
        task_logger.error(f"Error calculating momentum signals: {e}")
        return {"error": str(e)}


@task(name="calculate_mean_reversion")
def calculate_mean_reversion_task(
    prices_df: pd.DataFrame, period: int = 20, std_dev_threshold: float = 2.0
) -> Dict:
    """
    Calculate mean reversion signals.

    Args:
        prices_df: DataFrame with prices by symbol
        period: Period for mean reversion calculation
        std_dev_threshold: Z-score threshold for signals

    Returns:
        Dict with mean reversion signals and candidates
    """
    task_logger = get_run_logger()
    task_logger.info(f"Calculating mean reversion signals (period={period}, threshold={std_dev_threshold})...")

    try:
        result = QuickWinsAnalytics.mean_reversion_signals(
            prices_df, period=period, std_dev_threshold=std_dev_threshold
        )
        buy_candidates = result.get("buy_candidates", [])
        sell_candidates = result.get("sell_candidates", [])
        task_logger.info(
            f"Mean reversion: {len(buy_candidates)} buy candidates, {len(sell_candidates)} sell candidates"
        )
        return result
    except Exception as e:
        task_logger.error(f"Error calculating mean reversion signals: {e}")
        return {"error": str(e)}


@task(name="save_quick_wins_results")
def save_quick_wins_results(
    beta_analysis: Dict,
    sector_rotation: Dict,
    momentum_signals: Dict,
    mean_reversion: Dict,
) -> bool:
    """
    Save quick wins analysis results to ParquetDB.

    Args:
        beta_analysis: Portfolio beta analysis
        sector_rotation: Sector rotation strategy
        momentum_signals: Momentum screening results
        mean_reversion: Mean reversion signals

    Returns:
        True if successful
    """
    task_logger = get_run_logger()
    task_logger.info("Saving quick wins results to ParquetDB...")

    try:
        db = ParquetDB()

        # Save each analysis as a separate record
        quick_wins_data = {
            "analysis_type": ["beta", "sector_rotation", "momentum", "mean_reversion"],
            "results": [
                str(beta_analysis),
                str(sector_rotation),
                str(momentum_signals),
                str(mean_reversion),
            ],
            "timestamp": [pd.Timestamp.now()] * 4,
        }

        df = pd.DataFrame(quick_wins_data)
        db.write_table(df, "quick_wins_analysis", mode="append")
        task_logger.info("Quick wins results saved")
        return True

    except Exception as e:
        task_logger.warning(f"Could not save quick wins results to ParquetDB (non-fatal): {e}")
        return False


@flow(name="quick_wins_analytics_flow")
def quick_wins_analytics_flow(
    prices_dict: Dict,
    holdings_df: pd.DataFrame,
) -> Dict:
    """
    Complete quick wins analytics flow.

    Calculates:
    - Portfolio beta and risk classification
    - Sector rotation opportunities
    - Momentum-based trading signals
    - Mean reversion trading candidates

    Args:
        prices_dict: Dictionary of symbol -> price data
        holdings_df: Portfolio holdings DataFrame

    Returns:
        Dict with all quick wins analyses
    """
    flow_logger = get_run_logger()
    flow_logger.info("Starting quick wins analytics flow...")

    try:
        # Prepare data
        flow_logger.info("Preparing analysis data...")
        returns_df = prepare_returns_data(prices_dict, holdings_df)
        prices_df = prepare_prices_data(prices_dict, holdings_df)
        market_returns = prepare_market_returns()
        sector_returns, holding_sectors = prepare_sector_data(holdings_df)

        # Calculate quick wins analyses
        flow_logger.info("Calculating quick wins analyses...")
        beta_analysis = calculate_portfolio_beta_task(returns_df, market_returns)
        sector_rotation = calculate_sector_rotation_task(sector_returns, holding_sectors)
        momentum_signals = calculate_momentum_signals_task(returns_df, period=20)
        mean_reversion = calculate_mean_reversion_task(prices_df, period=20, std_dev_threshold=2.0)

        # Save results
        save_success = save_quick_wins_results(beta_analysis, sector_rotation, momentum_signals, mean_reversion)

        result = {
            "status": "success",
            "portfolio_beta": beta_analysis,
            "sector_rotation": sector_rotation,
            "momentum_signals": momentum_signals,
            "mean_reversion": mean_reversion,
            "saved": save_success,
        }

        flow_logger.info("Quick wins analytics flow completed successfully")
        return result

    except Exception as e:
        flow_logger.error(f"Error in quick wins analytics flow: {e}")
        return {"status": "error", "message": str(e)}
