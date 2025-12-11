"""
Quick Wins Analytics Module

Easy-to-implement, high-value analytics:
- Sector/asset class breakdown
- Portfolio volatility tracking
- Dividend income projection
- Winners/losers daily report
- Correlation heatmap
- Sharpe ratio calculation
- Concentration risk metrics
- Portfolio beta visualization
- Sector rotation strategy
- Momentum screening
- Mean reversion signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class QuickWinsAnalytics:
    """High-value, easy-to-implement portfolio analytics."""

    @staticmethod
    def sector_allocation(holdings: Dict[str, Dict]) -> Dict[str, float]:
        """
        Calculate portfolio allocation by sector.

        Args:
            holdings: Dict with ticker -> {'quantity': int, 'price': float, 'sector': str}

        Returns:
            Dict of sector -> allocation percentage
        """
        sector_values = {}
        total_value = 0.0

        for ticker, data in holdings.items():
            value = data.get("quantity", 0) * data.get("price", 0)
            sector = data.get("sector", "Unknown")

            if sector not in sector_values:
                sector_values[sector] = 0.0

            sector_values[sector] += value
            total_value += value

        # Convert to percentages
        if total_value == 0:
            return {}

        return {sector: (value / total_value * 100) for sector, value in sector_values.items()}

    @staticmethod
    def asset_class_breakdown(holdings: Dict[str, Dict]) -> Dict[str, float]:
        """
        Calculate portfolio by asset class (equity, crypto, bond, etc.).

        Args:
            holdings: Dict with ticker -> {'quantity': int, 'price': float, 'asset_class': str}

        Returns:
            Dict of asset_class -> allocation percentage
        """
        class_values = {}
        total_value = 0.0

        for ticker, data in holdings.items():
            value = data.get("quantity", 0) * data.get("price", 0)
            asset_class = data.get("asset_class", "equity")

            if asset_class not in class_values:
                class_values[asset_class] = 0.0

            class_values[asset_class] += value
            total_value += value

        if total_value == 0:
            return {}

        return {ac: (value / total_value * 100) for ac, value in class_values.items()}

    @staticmethod
    def portfolio_volatility(returns: List[float], annualized: bool = True) -> float:
        """
        Calculate portfolio volatility.

        Args:
            returns: List of daily returns
            annualized: If True, annualize the volatility

        Returns:
            Volatility as percentage
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        std_dev = np.std(returns_array)

        if annualized:
            std_dev *= np.sqrt(252)

        return float(std_dev * 100)

    @staticmethod
    def dividend_income_projection(holdings: Dict[str, Dict], annual_projection: bool = True) -> Dict[str, float]:
        """
        Project dividend income.

        Args:
            holdings: Dict with ticker -> {'quantity': int, 'dividend_yield': float}
            annual_projection: If True, project annual; else monthly

        Returns:
            Dict with projection and breakdown by holding
        """
        total_dividend = 0.0
        breakdown = {}

        for ticker, data in holdings.items():
            quantity = data.get("quantity", 0)
            price = data.get("price", 0)
            div_yield = data.get("dividend_yield", 0)

            position_value = quantity * price
            annual_dividend = position_value * div_yield

            breakdown[ticker] = annual_dividend
            total_dividend += annual_dividend

        if annual_projection:
            projection_period = "annual"
            projected = total_dividend
        else:
            projection_period = "monthly"
            projected = total_dividend / 12

        return {
            "projection_period": projection_period,
            "projected_income": float(projected),
            "annual_equivalent": float(total_dividend),
            "breakdown": {k: float(v) for k, v in breakdown.items()},
        }

    @staticmethod
    def winners_losers_report(positions: Dict[str, Dict], top_n: int = 5) -> Dict[str, List]:
        """
        Generate winners and losers report.

        Args:
            positions: Dict with ticker -> {'entry_price': float, 'current_price': float}
            top_n: Number of top winners/losers to show

        Returns:
            Dict with top performers
        """
        performance = []

        for ticker, data in positions.items():
            entry = data.get("entry_price", 0)
            current = data.get("current_price", 0)

            if entry == 0:
                continue

            pnl_pct = (current - entry) / entry * 100
            pnl_dollars = current - entry

            performance.append(
                {
                    "ticker": ticker,
                    "entry_price": entry,
                    "current_price": current,
                    "pnl_pct": pnl_pct,
                    "pnl_dollars": pnl_dollars,
                }
            )

        # Sort by performance
        performance.sort(key=lambda x: x["pnl_pct"], reverse=True)

        winners = performance[:top_n]
        losers = performance[-top_n:][::-1]  # Reverse to show worst first

        return {
            "winners": [
                {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in w.items()} for w in winners
            ],
            "losers": [{k: (float(v) if isinstance(v, (int, float)) else v) for k, v in l.items()} for l in losers],
        }

    @staticmethod
    def correlation_matrix_summary(price_df: pd.DataFrame, top_correlations: int = 5) -> Dict[str, any]:
        """
        Calculate and summarize correlation matrix.

        Args:
            price_df: DataFrame with date index, ticker columns
            top_correlations: Number of top correlations to show

        Returns:
            Dict with correlation summary
        """
        returns_df = price_df.pct_change().dropna()
        corr_matrix = returns_df.corr()

        # Find top positive and negative correlations
        correlation_pairs = []

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                ticker_i = corr_matrix.columns[i]
                ticker_j = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]

                correlation_pairs.append(
                    {"ticker_1": ticker_i, "ticker_2": ticker_j, "correlation": corr_value}
                )

        # Sort by absolute correlation
        correlation_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        top_positive = [p for p in correlation_pairs if p["correlation"] > 0][:top_correlations]
        top_negative = [p for p in correlation_pairs if p["correlation"] < 0][:top_correlations]

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "top_positive_correlations": top_positive,
            "top_negative_correlations": top_negative,
            "num_assets": len(corr_matrix.columns),
        }

    @staticmethod
    def sharpe_ratio_calculation(
        returns: List[float], risk_free_rate: float = 0.04, periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            returns: List of returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: 252 for daily, 12 for monthly

        Returns:
            Sharpe ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        excess_return = np.mean(returns_array) - (risk_free_rate / periods_per_year)
        std_return = np.std(returns_array)

        if std_return == 0:
            return 0.0

        sharpe = (excess_return / std_return) * np.sqrt(periods_per_year)
        return float(sharpe)

    @staticmethod
    def concentration_risk_metrics(weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio concentration metrics.

        Args:
            weights: Dict of ticker -> weight

        Returns:
            Concentration risk metrics
        """
        weights_array = np.array(list(weights.values()))

        if len(weights_array) == 0:
            return {}

        weights_array = weights_array / weights_array.sum()

        # Herfindahl-Hirschman Index
        hhi = np.sum(weights_array**2)

        # Top-N concentration
        sorted_weights = sorted(weights_array, reverse=True)
        top_1 = sorted_weights[0] if len(sorted_weights) > 0 else 0
        top_3 = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)
        top_5 = sum(sorted_weights[:5]) if len(sorted_weights) >= 5 else sum(sorted_weights)

        return {
            "hhi_index": float(hhi),  # 0.1-1.0, higher = more concentrated
            "top_1_concentration": float(top_1 * 100),
            "top_3_concentration": float(top_3 * 100),
            "top_5_concentration": float(top_5 * 100),
            "num_holdings": len(weights),
            "diversification_score": float(1.0 / hhi if hhi > 0 else 0),  # Higher = better
            "is_concentrated": hhi > 0.25,  # HHI > 0.25 = moderately concentrated
        }

    @staticmethod
    def portfolio_summary_statistics(holdings: Dict[str, Dict], prices: Dict[str, float]) -> Dict[str, any]:
        """
        Generate comprehensive portfolio summary.

        Args:
            holdings: Dict with ticker -> quantity
            prices: Dict with ticker -> current_price

        Returns:
            Summary statistics
        """
        total_value = 0.0
        weights = {}

        for ticker, quantity in holdings.items():
            price = prices.get(ticker, 0)
            value = quantity * price
            total_value += value

        if total_value == 0:
            return {}

        for ticker, quantity in holdings.items():
            price = prices.get(ticker, 0)
            value = quantity * price
            weights[ticker] = value / total_value

        concentration = QuickWinsAnalytics.concentration_risk_metrics(weights)

        return {
            "total_portfolio_value": float(total_value),
            "num_holdings": len(holdings),
            "largest_holding": max(weights.values()) * 100 if weights else 0,
            "smallest_holding": min(weights.values()) * 100 if weights else 0,
            "concentration_metrics": concentration,
            "weights": {k: float(v * 100) for k, v in weights.items()},
        }

    @staticmethod
    def portfolio_beta_visualization(returns_df: pd.DataFrame, market_returns: pd.Series) -> Dict[str, any]:
        """
        Calculate portfolio beta for each holding.
        
        Args:
            returns_df: DataFrame with ticker columns and date index (returns)
            market_returns: Series with market returns
        
        Returns:
            Dict with beta values and visualization data
        """
        betas = {}
        
        for ticker in returns_df.columns:
            # Calculate covariance between ticker and market
            covariance = np.cov(returns_df[ticker], market_returns)[0, 1]
            market_variance = np.var(market_returns)
            
            if market_variance != 0:
                beta = covariance / market_variance
            else:
                beta = 0.0
            
            betas[ticker] = float(beta)
        
        portfolio_beta = float(np.mean(list(betas.values()))) if betas else 1.0
        
        return {
            "portfolio_beta": portfolio_beta,
            "individual_betas": betas,
            "beta_interpretation": (
                "Aggressive" if portfolio_beta > 1.2 else
                "Moderate" if portfolio_beta > 0.8 else
                "Conservative" if portfolio_beta > 0 else
                "Inverse/Hedge"
            ),
            "high_beta_holdings": sorted(
                [(t, b) for t, b in betas.items() if b > 1.2],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "low_beta_holdings": sorted(
                [(t, b) for t, b in betas.items() if b < 0.8],
                key=lambda x: x[1]
            )[:5],
        }

    @staticmethod
    def sector_rotation_strategy(sector_returns: Dict[str, float], holding_sectors: Dict[str, str]) -> Dict[str, any]:
        """
        Identify sector rotation opportunities.
        
        Args:
            sector_returns: Dict of sector -> recent return %
            holding_sectors: Dict of ticker -> sector
        
        Returns:
            Rotation recommendations
        """
        if not sector_returns:
            return {}
        
        sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
        best_sectors = [s[0] for s in sorted_sectors[:3]]
        worst_sectors = [s[0] for s in sorted_sectors[-3:]]
        
        # Find holdings in underperforming sectors
        holdings_in_worst = {}
        for ticker, sector in holding_sectors.items():
            if sector in worst_sectors:
                if sector not in holdings_in_worst:
                    holdings_in_worst[sector] = []
                holdings_in_worst[sector].append(ticker)
        
        return {
            "best_performing_sectors": [
                {"sector": s[0], "return": float(s[1])} for s in sorted_sectors[:3]
            ],
            "worst_performing_sectors": [
                {"sector": s[0], "return": float(s[1])} for s in sorted_sectors[-3:]
            ],
            "candidates_for_rotation": holdings_in_worst,
            "rotation_potential": f"Consider rotating from {', '.join(worst_sectors)} to {', '.join(best_sectors)}",
        }

    @staticmethod
    def momentum_screening(returns_df: pd.DataFrame, period: int = 20) -> Dict[str, any]:
        """
        Screen for momentum signals using price momentum and RSI-like calculations.
        
        Args:
            returns_df: DataFrame with ticker columns (daily returns)
            period: Lookback period for momentum
        
        Returns:
            Momentum signals and screening results
        """
        momentum_scores = {}
        
        for ticker in returns_df.columns:
            # Calculate price momentum (cumulative return over period)
            recent_returns = returns_df[ticker].tail(period)
            momentum = (1 + recent_returns).prod() - 1
            
            # Calculate momentum strength (consistency)
            positive_days = (recent_returns > 0).sum()
            strength = positive_days / len(recent_returns) if len(recent_returns) > 0 else 0
            
            # Composite score
            score = momentum * 100 + strength * 20  # Weighted composite
            
            momentum_scores[ticker] = {
                "momentum_pct": float(momentum * 100),
                "positive_day_ratio": float(strength),
                "score": float(score),
                "signal": "Strong Uptrend" if score > 10 else "Uptrend" if score > 0 else "Downtrend"
            }
        
        sorted_momentum = sorted(momentum_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        return {
            "all_scores": momentum_scores,
            "top_momentum": [
                {**{"ticker": t}, **v} for t, v in sorted_momentum[:5]
            ],
            "bottom_momentum": [
                {**{"ticker": t}, **v} for t, v in sorted_momentum[-5:]
            ],
        }

    @staticmethod
    def mean_reversion_signals(prices_df: pd.DataFrame, period: int = 20, std_dev_threshold: float = 2.0) -> Dict[str, any]:
        """
        Identify mean reversion signals using deviation from moving average.
        
        Args:
            prices_df: DataFrame with ticker columns (prices)
            period: Period for moving average
            std_dev_threshold: Number of standard deviations for signal
        
        Returns:
            Mean reversion signals and candidates
        """
        signals = {}
        
        for ticker in prices_df.columns:
            prices = prices_df[ticker].dropna()
            
            if len(prices) < period:
                continue
            
            # Calculate moving average and standard deviation
            ma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            # Get current deviation
            current_price = prices.iloc[-1]
            current_ma = ma.iloc[-1]
            current_std = std.iloc[-1]
            
            if current_std == 0 or pd.isna(current_ma):
                continue
            
            # Calculate z-score (deviation in standard deviations)
            z_score = (current_price - current_ma) / current_std
            
            # Determine signal
            if z_score > std_dev_threshold:
                signal = "Overbought - Potential Sell"
                strength = "Strong"
            elif z_score > std_dev_threshold * 0.5:
                signal = "Overbought - Light Sell"
                strength = "Moderate"
            elif z_score < -std_dev_threshold:
                signal = "Oversold - Potential Buy"
                strength = "Strong"
            elif z_score < -std_dev_threshold * 0.5:
                signal = "Oversold - Light Buy"
                strength = "Moderate"
            else:
                signal = "Normal Range"
                strength = "None"
            
            signals[ticker] = {
                "current_price": float(current_price),
                "moving_average": float(current_ma),
                "z_score": float(z_score),
                "signal": signal,
                "strength": strength,
                "deviation_pct": float((current_price - current_ma) / current_ma * 100),
            }
        
        # Filter for actionable signals
        buy_signals = {t: v for t, v in signals.items() if "Buy" in v["signal"]}
        sell_signals = {t: v for t, v in signals.items() if "Sell" in v["signal"]}
        
        return {
            "all_signals": signals,
            "buy_candidates": sorted(
                [{**{"ticker": t}, **v} for t, v in buy_signals.items()],
                key=lambda x: abs(x["z_score"]),
                reverse=True
            )[:5],
            "sell_candidates": sorted(
                [{**{"ticker": t}, **v} for t, v in sell_signals.items()],
                key=lambda x: abs(x["z_score"]),
                reverse=True
            )[:5],
        }
