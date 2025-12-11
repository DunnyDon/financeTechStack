"""
Portfolio Optimization Module

Mean-variance optimization and portfolio management:
- Efficient Frontier calculation
- Optimal weight allocation
- Rebalancing recommendations
- Tax-loss harvesting suggestions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float


class PortfolioOptimizer:
    """Optimize portfolio weights using mean-variance analysis."""

    def __init__(self, returns_df: pd.DataFrame, risk_free_rate: float = 0.04):
        """
        Initialize optimizer.

        Args:
            returns_df: DataFrame with date index and ticker columns (returns)
            risk_free_rate: Annual risk-free rate
        """
        self.returns_df = returns_df
        self.risk_free_rate = risk_free_rate
        self.mean_returns = returns_df.mean() * 252  # Annualize
        self.cov_matrix = returns_df.cov() * 252

    def calculate_portfolio_metrics(
        self, weights: np.ndarray, tickers: List[str]
    ) -> Tuple[float, float, float]:
        """
        Calculate expected return, volatility, and Sharpe ratio.

        Args:
            weights: Array of weights
            tickers: List of ticker symbols

        Returns:
            Tuple of (return, volatility, sharpe_ratio)
        """
        # Filter to existing tickers
        valid_tickers = [t for t in tickers if t in self.mean_returns.index]
        if len(valid_tickers) != len(tickers):
            # Missing tickers - return zeros
            return 0.0, 0.0, 0.0

        valid_cov = self.cov_matrix.loc[valid_tickers, valid_tickers]
        valid_returns = self.mean_returns[valid_tickers].values

        portfolio_return = np.sum(weights * valid_returns)
        portfolio_volatility = np.sqrt(np.dot(weights, np.dot(valid_cov.values, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0

        return float(portfolio_return), float(portfolio_volatility), float(sharpe)

    def minimum_variance_portfolio(self, tickers: List[str]) -> OptimizationResult:
        """
        Calculate minimum variance portfolio.

        Args:
            tickers: List of ticker symbols

        Returns:
            OptimizationResult with optimal weights
        """
        valid_tickers = [t for t in tickers if t in self.mean_returns.index]
        if not valid_tickers:
            return OptimizationResult(weights={}, expected_return=0.0, expected_volatility=0.0, sharpe_ratio=0.0)

        n = len(valid_tickers)
        weights = np.array([1.0 / n] * n)  # Equal weight as starting point

        # For simplicity, use equal weight or inverse volatility weighting
        volatilities = self.returns_df[valid_tickers].std() * np.sqrt(252)
        inv_vols = 1.0 / volatilities.values
        weights = inv_vols / np.sum(inv_vols)

        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, valid_tickers)
        weight_dict = {ticker: float(w) for ticker, w in zip(valid_tickers, weights)}

        return OptimizationResult(
            weights=weight_dict, expected_return=ret, expected_volatility=vol, sharpe_ratio=sharpe
        )

    def maximum_sharpe_ratio_portfolio(self, tickers: List[str]) -> OptimizationResult:
        """
        Calculate portfolio with maximum Sharpe ratio (not exact, uses heuristic).

        Args:
            tickers: List of ticker symbols

        Returns:
            OptimizationResult with optimal weights
        """
        valid_tickers = [t for t in tickers if t in self.mean_returns.index]
        if not valid_tickers:
            return OptimizationResult(weights={}, expected_return=0.0, expected_volatility=0.0, sharpe_ratio=0.0)

        # Simple heuristic: weight by return-to-volatility ratio
        returns = self.mean_returns[valid_tickers].values
        vols = self.returns_df[valid_tickers].std().values * np.sqrt(252)

        # Avoid division by zero
        risk_adjusted = returns / (vols + 1e-6)
        weights = np.maximum(risk_adjusted, 0)  # No short selling
        weights = weights / np.sum(weights)

        ret, vol, sharpe = self.calculate_portfolio_metrics(weights, valid_tickers)
        weight_dict = {ticker: float(w) for ticker, w in zip(valid_tickers, weights)}

        return OptimizationResult(
            weights=weight_dict, expected_return=ret, expected_volatility=vol, sharpe_ratio=sharpe
        )

    def efficient_frontier(self, tickers: List[str], num_points: int = 20) -> Dict[str, list]:
        """
        Calculate points on the efficient frontier.

        Args:
            tickers: List of ticker symbols
            num_points: Number of points to calculate

        Returns:
            Dict with volatilities and returns
        """
        valid_tickers = [t for t in tickers if t in self.mean_returns.index]
        if not valid_tickers:
            return {"volatilities": [], "returns": [], "sharpes": []}

        n = len(valid_tickers)
        results = {"volatilities": [], "returns": [], "sharpes": []}

        # Generate random portfolios to approximate frontier
        np.random.seed(42)
        for _ in range(num_points * 5):  # Generate more to find best
            weights = np.random.dirichlet(np.ones(n))
            ret, vol, sharpe = self.calculate_portfolio_metrics(weights, valid_tickers)

            results["returns"].append(ret)
            results["volatilities"].append(vol)
            results["sharpes"].append(sharpe)

        return results

    def rebalancing_recommendations(
        self, current_weights: Dict[str, float], target_weights: Dict[str, float], threshold: float = 0.05
    ) -> Dict[str, Dict[str, float]]:
        """
        Recommend rebalancing actions.

        Args:
            current_weights: Current allocation
            target_weights: Target allocation
            threshold: Only recommend if drift > threshold

        Returns:
            Dict with rebalancing actions
        """
        recommendations = {}

        for ticker in set(current_weights.keys()) | set(target_weights.keys()):
            current = current_weights.get(ticker, 0.0)
            target = target_weights.get(ticker, 0.0)
            drift = abs(current - target)

            if drift > threshold:
                action = "buy" if current < target else "sell"
                recommendations[ticker] = {
                    "action": action,
                    "current_weight": current,
                    "target_weight": target,
                    "drift": drift,
                    "current_pct": current * 100,
                    "target_pct": target * 100,
                }

        return recommendations

    def tax_loss_harvesting_opportunities(
        self, current_prices: Dict[str, float], cost_basis: Dict[str, float], min_loss: float = 0.05
    ) -> Dict[str, Dict[str, float]]:
        """
        Identify tax-loss harvesting opportunities.

        Args:
            current_prices: Current prices by ticker
            cost_basis: Original purchase prices by ticker
            min_loss: Minimum loss threshold (5%)

        Returns:
            Dict of positions with unrealized losses
        """
        opportunities = {}

        for ticker in current_prices:
            if ticker not in cost_basis:
                continue

            current = current_prices[ticker]
            basis = cost_basis[ticker]
            loss_pct = (current - basis) / basis if basis > 0 else 0

            if loss_pct < -min_loss:  # Negative = loss
                opportunities[ticker] = {
                    "current_price": current,
                    "cost_basis": basis,
                    "unrealized_loss_pct": loss_pct * 100,
                    "loss_per_share": current - basis,
                }

        return opportunities


def equal_weight_portfolio(tickers: List[str]) -> Dict[str, float]:
    """Create equal-weight portfolio."""
    weight = 1.0 / len(tickers) if tickers else 0.0
    return {ticker: weight for ticker in tickers}


def market_cap_weight_portfolio(market_caps: Dict[str, float]) -> Dict[str, float]:
    """Create market-cap weighted portfolio."""
    total_cap = sum(market_caps.values())
    if total_cap == 0:
        return {}
    return {ticker: cap / total_cap for ticker, cap in market_caps.items()}
