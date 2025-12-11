"""Backtest analysis and reporting utilities."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from .metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_underwater_plot,
    calculate_monthly_returns,
    calculate_annual_returns,
)

logger = logging.getLogger(__name__)


class BacktestAnalyzer:
    """Analyze and report on backtest results."""

    def __init__(self, backtest_results: Dict):
        """
        Initialize analyzer.

        Args:
            backtest_results: Results dictionary from BacktestEngine.run()
        """
        self.results = backtest_results
        self.metrics = backtest_results.get("metrics", {})
        self.trades = backtest_results.get("trades", [])
        self.portfolio_history = backtest_results.get("portfolio_history", [])
        self.equity_curve = backtest_results.get("equity_curve", [])

    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            "=" * 60,
            "BACKTEST SUMMARY",
            "=" * 60,
            "",
            "RETURNS",
            f"  Total Return:          {self.metrics.get('total_return_pct', 0):.2f}%",
            f"  Annual Return:         {self.metrics.get('annual_return_pct', 0):.2f}%",
            f"  Annual Volatility:     {self.metrics.get('annual_volatility_pct', 0):.2f}%",
            "",
            "RISK METRICS",
            f"  Max Drawdown:          {self.metrics.get('max_drawdown_pct', 0):.2f}%",
            f"  Sharpe Ratio:          {self.metrics.get('sharpe_ratio', 0):.2f}",
            f"  Sortino Ratio:         {self.metrics.get('sortino_ratio', 0):.2f}",
            f"  Calmar Ratio:          {self.metrics.get('calmar_ratio', 0):.2f}",
            "",
            "TRADING STATISTICS",
            f"  Total Trades:          {self.metrics.get('total_trades', 0)}",
            f"  Winning Trades:        {self.metrics.get('winning_trades', 0)}",
            f"  Losing Trades:         {self.metrics.get('losing_trades', 0)}",
            f"  Win Rate:              {self.metrics.get('win_rate_pct', 0):.2f}%",
            f"  Profit Factor:         {self.metrics.get('profit_factor', 0):.2f}",
            f"  Avg Bars Held:         {self.metrics.get('avg_bars_held', 0):.0f}",
            f"  Avg Win:               ${self.metrics.get('avg_win_pnl', 0):.2f}",
            f"  Avg Loss:              ${self.metrics.get('avg_loss_pnl', 0):.2f}",
            "",
            "=" * 60,
        ]

        return "\n".join(lines)

    def trades_dataframe(self) -> pd.DataFrame:
        """Get trades as DataFrame."""
        if not self.trades:
            return pd.DataFrame()

        data = []
        for trade in self.trades:
            data.append(
                {
                    "symbol": trade.symbol,
                    "entry_date": trade.entry_date,
                    "exit_date": trade.exit_date,
                    "days_held": trade.bars_held,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "pnl": trade.pnl,
                    "pnl_pct": trade.pnl_pct,
                    "signal_type": trade.signal_type,
                }
            )

        return pd.DataFrame(data)

    def monthly_returns(self) -> pd.DataFrame:
        """Calculate monthly returns."""
        if not self.portfolio_history:
            return pd.DataFrame()

        dates = [s.date for s in self.portfolio_history]
        values = [s.total_value for s in self.portfolio_history]

        return calculate_monthly_returns(values, dates)

    def annual_returns(self) -> pd.DataFrame:
        """Calculate annual returns."""
        if not self.portfolio_history:
            return pd.DataFrame()

        dates = [s.date for s in self.portfolio_history]
        values = [s.total_value for s in self.portfolio_history]

        return calculate_annual_returns(values, dates)

    def underwater_plot_data(self) -> np.ndarray:
        """Get drawdown data for plotting."""
        if not self.equity_curve:
            return np.array([])

        equity_array = np.array(self.equity_curve)
        return calculate_underwater_plot(equity_array)

    def best_trades(self, n: int = 5) -> pd.DataFrame:
        """Get best performing trades."""
        trades_df = self.trades_dataframe()

        if trades_df.empty:
            return pd.DataFrame()

        # Filter out trades without P&L and convert to numeric
        trades_df = trades_df[trades_df["pnl"].notna()].copy()
        trades_df["pnl"] = pd.to_numeric(trades_df["pnl"], errors="coerce")
        trades_df = trades_df[trades_df["pnl"].notna()]
        
        if trades_df.empty:
            return pd.DataFrame()

        return trades_df.nlargest(n, "pnl")[
            ["symbol", "entry_date", "exit_date", "pnl", "pnl_pct", "signal_type"]
        ]

    def worst_trades(self, n: int = 5) -> pd.DataFrame:
        """Get worst performing trades."""
        trades_df = self.trades_dataframe()

        if trades_df.empty:
            return pd.DataFrame()

        # Filter out trades without P&L and convert to numeric
        trades_df = trades_df[trades_df["pnl"].notna()].copy()
        trades_df["pnl"] = pd.to_numeric(trades_df["pnl"], errors="coerce")
        trades_df = trades_df[trades_df["pnl"].notna()]
        
        if trades_df.empty:
            return pd.DataFrame()

        return trades_df.nsmallest(n, "pnl")[
            ["symbol", "entry_date", "exit_date", "pnl", "pnl_pct", "signal_type"]
        ]

    def by_symbol(self) -> pd.DataFrame:
        """Analyze trades by symbol."""
        trades_df = self.trades_dataframe()

        if trades_df.empty:
            return pd.DataFrame()

        grouped = trades_df.groupby("symbol").agg(
            {
                "pnl": ["count", "sum", "mean"],
                "pnl_pct": "mean",
            }
        )

        grouped.columns = ["trades", "total_pnl", "avg_pnl", "avg_return_pct"]
        return grouped.sort_values("total_pnl", ascending=False)

    def by_signal_type(self) -> pd.DataFrame:
        """Analyze trades by signal type."""
        trades_df = self.trades_dataframe()

        if trades_df.empty:
            return pd.DataFrame()

        grouped = trades_df.groupby("signal_type").agg(
            {
                "pnl": ["count", "sum", "mean"],
                "pnl_pct": "mean",
            }
        )

        grouped.columns = ["trades", "total_pnl", "avg_pnl", "avg_return_pct"]
        return grouped.sort_values("total_pnl", ascending=False)

    def consecutive_wins_losses(self) -> Dict:
        """Calculate longest win/loss streaks."""
        trades_df = self.trades_dataframe()

        if trades_df.empty:
            return {"max_wins": 0, "max_losses": 0}

        # Calculate streaks
        closed_trades = trades_df[trades_df["exit_date"].notna()]
        closed_trades = closed_trades.sort_values("exit_date")

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for _, trade in closed_trades.iterrows():
            if trade["pnl"] > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return {"max_consecutive_wins": max_wins, "max_consecutive_losses": max_losses}

    def equity_curve_data(self) -> pd.DataFrame:
        """Get equity curve as DataFrame."""
        if not self.portfolio_history:
            return pd.DataFrame()

        dates = [s.date for s in self.portfolio_history]
        values = [s.total_value for s in self.portfolio_history]

        return pd.DataFrame({"date": dates, "value": values})

    def comparison_to_benchmark(
        self, benchmark_returns: np.ndarray
    ) -> Dict:
        """Compare strategy to benchmark."""
        if not self.equity_curve:
            return {}

        equity_array = np.array(self.equity_curve)
        strategy_returns = np.diff(equity_array) / equity_array[:-1]

        if len(strategy_returns) != len(benchmark_returns):
            logger.warning(
                "Benchmark length doesn't match strategy returns"
            )
            return {}

        # Calculate metrics
        excess_return = (
            np.mean(strategy_returns) - np.mean(benchmark_returns)
        ) * 252
        tracking_error = np.std(
            strategy_returns - benchmark_returns
        ) * np.sqrt(252)
        information_ratio = excess_return / (tracking_error + 1e-6)

        return {
            "strategy_return": np.mean(strategy_returns) * 252,
            "benchmark_return": np.mean(benchmark_returns) * 252,
            "excess_return": excess_return,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
        }

    def risk_analysis(self) -> Dict:
        """Detailed risk analysis."""
        if not self.equity_curve:
            return {}

        equity_array = np.array(self.equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]

        underwater = self.underwater_plot_data()

        return {
            "var_95": np.percentile(returns, 5),  # 95% VaR
            "var_99": np.percentile(returns, 1),  # 99% VaR
            "cvar_95": np.mean(returns[returns < np.percentile(returns, 5)]),  # CVaR
            "current_drawdown": underwater[-1] if len(underwater) > 0 else 0,
            "longest_drawdown_days": self._longest_drawdown_period(underwater),
            "skewness": self._calculate_skewness(returns),
            "kurtosis": self._calculate_kurtosis(returns),
        }

    def _longest_drawdown_period(self, underwater: np.ndarray) -> int:
        """Calculate longest continuous drawdown period."""
        if len(underwater) == 0:
            return 0

        in_dd = False
        current_dd = 0
        max_dd = 0

        for value in underwater:
            if value < 0:
                current_dd += 1
                max_dd = max(max_dd, current_dd)
            else:
                current_dd = 0

        return max_dd

    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return 0.0

        mean = np.mean(returns)
        std = np.std(returns)

        if std == 0:
            return 0.0

        return np.mean(((returns - mean) / std) ** 3)

    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate excess kurtosis of returns."""
        if len(returns) < 4:
            return 0.0

        mean = np.mean(returns)
        std = np.std(returns)

        if std == 0:
            return 0.0

        return np.mean(((returns - mean) / std) ** 4) - 3
