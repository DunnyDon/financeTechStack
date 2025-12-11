"""
Portfolio Risk Analytics Module

Comprehensive risk metrics for portfolio analysis:
- Value at Risk (VaR)
- Correlation analysis
- Portfolio beta
- Stress testing
- Maximum drawdown
- Volatility metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class RiskAnalytics:
    """Calculate comprehensive risk metrics for portfolios."""

    def __init__(self, prices_df: pd.DataFrame, risk_free_rate: float = 0.04):
        """
        Initialize risk analytics.

        Args:
            prices_df: DataFrame with date index and ticker columns (close prices)
            risk_free_rate: Annual risk-free rate (default 4%)
        """
        self.prices_df = prices_df
        self.risk_free_rate = risk_free_rate
        self.returns_df = prices_df.pct_change().dropna()

    def calculate_var(self, confidence: float = 0.95, days: int = 1) -> Dict[str, float]:
        """
        Calculate Value at Risk using historical simulation.

        Args:
            confidence: Confidence level (0.95 = 95% VaR)
            days: Time horizon in days

        Returns:
            Dict with VaR per asset and portfolio
        """
        daily_returns = self.returns_df
        scaled_returns = daily_returns * np.sqrt(days)

        var_dict = {}
        for ticker in scaled_returns.columns:
            var_value = scaled_returns[ticker].quantile(1 - confidence)
            var_dict[ticker] = var_value

        # Portfolio VaR (simple average)
        if len(var_dict) > 0:
            var_dict["portfolio"] = np.mean(list(var_dict.values()))

        return var_dict

    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        Calculate correlation matrix of returns.

        Returns:
            DataFrame with correlation matrix
        """
        return self.returns_df.corr()

    def calculate_portfolio_beta(
        self, weights: Dict[str, float], market_ticker: str = "SPY"
    ) -> float:
        """
        Calculate portfolio beta against market benchmark.

        Args:
            weights: Dict of ticker -> weight
            market_ticker: Market benchmark ticker

        Returns:
            Portfolio beta
        """
        # Calculate covariance between each asset and market
        betas = {}
        for ticker, weight in weights.items():
            if ticker not in self.returns_df.columns or market_ticker not in self.returns_df.columns:
                continue

            asset_returns = self.returns_df[ticker]
            market_returns = self.returns_df[market_ticker]

            covariance = asset_returns.cov(market_returns)
            market_variance = market_returns.var()
            beta = covariance / market_variance if market_variance > 0 else 0

            betas[ticker] = beta

        # Weighted portfolio beta
        portfolio_beta = sum(betas.get(t, 0) * w for t, w in weights.items())
        return portfolio_beta

    def calculate_portfolio_volatility(self, weights: Dict[str, float]) -> float:
        """
        Calculate annualized portfolio volatility.

        Args:
            weights: Dict of ticker -> weight

        Returns:
            Annualized volatility (%)
        """
        cov_matrix = self.returns_df.cov()
        weight_array = np.array([weights.get(t, 0) for t in self.returns_df.columns])

        # Only use tickers that exist in correlation matrix
        valid_tickers = [t for t in weights.keys() if t in cov_matrix.columns]
        if not valid_tickers:
            return 0.0

        valid_cov = cov_matrix.loc[valid_tickers, valid_tickers]
        valid_weights = np.array([weights[t] for t in valid_tickers])
        valid_weights = valid_weights / valid_weights.sum()  # Normalize

        variance = np.dot(valid_weights, np.dot(valid_cov.values, valid_weights))
        volatility = np.sqrt(variance) * np.sqrt(252)  # Annualize

        return float(volatility * 100)

    def calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """
        Calculate maximum drawdown from peak.

        Args:
            portfolio_values: List of portfolio values over time

        Returns:
            Max drawdown as percentage
        """
        if len(portfolio_values) < 2:
            return 0.0

        values = np.array(portfolio_values)
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max

        return float(np.min(drawdown) * 100)

    def calculate_sharpe_ratio(self, returns: List[float], excess_returns: bool = True) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            returns: List of portfolio returns
            excess_returns: If True, subtract risk-free rate

        Returns:
            Sharpe ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if excess_returns:
            mean_return -= self.risk_free_rate / 252  # Daily risk-free rate

        if std_return == 0:
            return 0.0

        sharpe = (mean_return * 252) / (std_return * np.sqrt(252))
        return float(sharpe)

    def stress_test(
        self, base_prices: Dict[str, float], shock_percentages: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Stress test portfolio with price shocks.

        Args:
            base_prices: Current prices by ticker
            shock_percentages: Shock % by ticker (e.g., {"AAPL": -0.10} = -10%)

        Returns:
            Portfolio impact per scenario
        """
        scenarios = {}
        for ticker, shock in shock_percentages.items():
            if ticker not in base_prices:
                continue

            new_price = base_prices[ticker] * (1 + shock)
            pnl_impact = new_price - base_prices[ticker]
            scenarios[ticker] = {"shock": shock * 100, "pnl_impact": pnl_impact}

        return scenarios

    def calculate_concentration_risk(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio concentration metrics.

        Args:
            weights: Dict of ticker -> weight

        Returns:
            Concentration metrics (HHI index, top-3 concentration, etc.)
        """
        weights_array = np.array(list(weights.values()))
        weights_array = weights_array / weights_array.sum()  # Normalize

        # Herfindahl-Hirschman Index (HHI)
        hhi = np.sum(weights_array**2)

        # Top holdings
        sorted_weights = sorted(weights.values(), reverse=True)
        top_3_concentration = sum(sorted_weights[:3])

        return {
            "hhi": float(hhi),  # 1.0 = completely concentrated, low = diversified
            "top_3_concentration": float(top_3_concentration),
            "num_holdings": len(weights),
            "diversification_ratio": float(1.0 / hhi),  # Higher = more diversified
        }


def calculate_var_simple(returns: pd.Series, confidence: float = 0.95) -> float:
    """Quick VaR calculation for a single asset."""
    return float(returns.quantile(1 - confidence))


def calculate_portfolio_return(prices_dict: Dict[str, float], holdings: Dict[str, float]) -> float:
    """Calculate simple portfolio return given prices and holdings."""
    total_value = sum(price * quantity for price, quantity in zip(prices_dict.values(), holdings.values()))
    return float(total_value) if total_value > 0 else 0.0
