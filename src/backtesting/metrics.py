"""Performance metrics calculation for backtesting."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def calculate_sharpe_ratio(
    returns: np.ndarray, risk_free_rate: float = 0.0, periods_per_year: int = 252
) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year

    Returns:
        Sharpe ratio
    """
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0

    excess_returns = returns - (risk_free_rate / periods_per_year)
    annual_return = np.mean(excess_returns) * periods_per_year
    annual_std = np.std(excess_returns) * np.sqrt(periods_per_year)

    return annual_return / (annual_std + 1e-6)


def calculate_sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    target_return: float = 0.0,
) -> float:
    """
    Calculate Sortino ratio (penalizes downside volatility only).

    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year
        target_return: Target return threshold

    Returns:
        Sortino ratio
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - (risk_free_rate / periods_per_year)
    annual_return = np.mean(excess_returns) * periods_per_year

    # Calculate downside deviation
    downside_returns = np.where(excess_returns < target_return, excess_returns, 0)
    downside_std = np.std(downside_returns) * np.sqrt(periods_per_year)

    return annual_return / (downside_std + 1e-6)


def calculate_max_drawdown(equity_curve: np.ndarray) -> float:
    """
    Calculate maximum drawdown.

    Args:
        equity_curve: Array of portfolio values

    Returns:
        Maximum drawdown as decimal (negative)
    """
    if len(equity_curve) < 2:
        return 0.0

    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max

    return np.min(drawdown)


def calculate_calmar_ratio(
    returns: np.ndarray,
    equity_curve: np.ndarray,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate Calmar ratio (return / max drawdown).

    Args:
        returns: Array of returns
        equity_curve: Array of portfolio values
        periods_per_year: Trading periods per year

    Returns:
        Calmar ratio
    """
    annual_return = np.mean(returns) * periods_per_year
    max_dd = calculate_max_drawdown(equity_curve)

    return annual_return / (abs(max_dd) + 1e-6)


def calculate_information_ratio(
    strategy_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate information ratio (excess return / tracking error).

    Args:
        strategy_returns: Array of strategy returns
        benchmark_returns: Array of benchmark returns
        periods_per_year: Trading periods per year

    Returns:
        Information ratio
    """
    if len(strategy_returns) < 2 or len(benchmark_returns) < 2:
        return 0.0

    excess_return = np.mean(strategy_returns - benchmark_returns) * periods_per_year
    tracking_error = np.std(strategy_returns - benchmark_returns) * np.sqrt(
        periods_per_year
    )

    return excess_return / (tracking_error + 1e-6)


def calculate_win_rate(trades: List) -> float:
    """
    Calculate percentage of profitable trades.

    Args:
        trades: List of Trade objects

    Returns:
        Win rate as decimal (0.0-1.0)
    """
    if not trades:
        return 0.0

    closed_trades = [t for t in trades if t.pnl is not None]
    if not closed_trades:
        return 0.0

    winning = len([t for t in closed_trades if t.pnl > 0])
    return winning / len(closed_trades)


def calculate_profit_factor(trades: List) -> float:
    """
    Calculate profit factor (gross profit / gross loss).

    Args:
        trades: List of Trade objects

    Returns:
        Profit factor
    """
    if not trades:
        return 0.0

    closed_trades = [t for t in trades if t.pnl is not None]
    if not closed_trades:
        return 0.0

    gross_profit = sum([t.pnl for t in closed_trades if t.pnl > 0])
    gross_loss = abs(sum([t.pnl for t in closed_trades if t.pnl < 0]))

    return gross_profit / (gross_loss + 1e-6)


def calculate_payoff_ratio(trades: List) -> float:
    """
    Calculate average win / average loss.

    Args:
        trades: List of Trade objects

    Returns:
        Payoff ratio
    """
    if not trades:
        return 0.0

    closed_trades = [t for t in trades if t.pnl is not None]
    if not closed_trades:
        return 0.0

    winning_trades = [t for t in closed_trades if t.pnl > 0]
    losing_trades = [t for t in closed_trades if t.pnl < 0]

    if not winning_trades or not losing_trades:
        return 0.0

    avg_win = np.mean([t.pnl for t in winning_trades])
    avg_loss = abs(np.mean([t.pnl for t in losing_trades]))

    return avg_win / (avg_loss + 1e-6)


def calculate_recovery_factor(
    total_pnl: float, max_drawdown: float
) -> float:
    """
    Calculate recovery factor (total profit / max drawdown).

    Args:
        total_pnl: Total profit/loss
        max_drawdown: Maximum drawdown amount

    Returns:
        Recovery factor
    """
    return total_pnl / (abs(max_drawdown) + 1e-6)


def calculate_underwater_plot(equity_curve: np.ndarray) -> np.ndarray:
    """
    Calculate drawdown at each point.

    Args:
        equity_curve: Array of portfolio values

    Returns:
        Array of drawdown values
    """
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max

    return drawdown * 100  # Convert to percentage


def calculate_monthly_returns(
    equity_curve: List[float], dates: List[pd.Timestamp]
) -> pd.DataFrame:
    """
    Calculate monthly returns.

    Args:
        equity_curve: List of portfolio values
        dates: List of corresponding dates

    Returns:
        DataFrame with monthly returns
    """
    if not equity_curve or not dates:
        return pd.DataFrame()

    df = pd.DataFrame({"value": equity_curve, "date": dates})
    df = df.set_index("date")

    monthly = df.resample("M").last()
    monthly["return"] = monthly["value"].pct_change() * 100

    return monthly[["return"]].dropna()


def calculate_annual_returns(
    equity_curve: List[float], dates: List[pd.Timestamp]
) -> pd.DataFrame:
    """
    Calculate annual returns.

    Args:
        equity_curve: List of portfolio values
        dates: List of corresponding dates

    Returns:
        DataFrame with annual returns
    """
    if not equity_curve or not dates:
        return pd.DataFrame()

    df = pd.DataFrame({"value": equity_curve, "date": dates})
    df = df.set_index("date")

    annual = df.resample("A").last()
    annual["return"] = annual["value"].pct_change() * 100

    return annual[["return"]].dropna()
