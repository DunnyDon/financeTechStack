"""Strategy base classes and implementations for backtesting."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd
import numpy as np


class SignalAction(Enum):
    """Trading signal actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    INCREASE = "INCREASE"


@dataclass
class Signal:
    """Trading signal for a position."""
    symbol: str
    timestamp: pd.Timestamp
    action: SignalAction
    signal_type: str  # "momentum", "mean_reversion", "sector_rotation", "beta"
    strength: float  # 0.0-1.0 confidence
    target_position_pct: float  # Desired position size as % of portfolio
    reason: str  # Explanation for signal
    parameters: Dict = field(default_factory=dict)  # Strategy parameters used


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, parameters: Dict = None):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            parameters: Strategy parameters dictionary
        """
        self.name = name
        self.parameters = parameters or {}

    @abstractmethod
    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp,
    ) -> List[Signal]:
        """
        Generate trading signals for given date.

        Args:
            prices_df: Historical OHLCV data indexed by symbol/date
            technical_df: Technical indicators indexed by symbol/date
            holdings_df: Current holdings (symbol, quantity, sector, etc.)
            date: Current backtest date

        Returns:
            List of Signal objects
        """
        pass

    def set_parameters(self, **kwargs):
        """Update strategy parameters."""
        self.parameters.update(kwargs)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.parameters})"


class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy using n-day returns."""

    def __init__(
        self,
        lookback: int = 20,
        threshold: float = 0.10,
        name: str = "momentum",
    ):
        """
        Initialize momentum strategy.

        Args:
            lookback: Period for momentum calculation (days)
            threshold: Return threshold for signal generation
            name: Strategy name
        """
        params = {"lookback": lookback, "threshold": threshold}
        super().__init__(name, params)

    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp,
    ) -> List[Signal]:
        """Generate momentum signals based on n-day returns."""
        signals = []

        for _, holding in holdings_df.iterrows():
            symbol = holding["sym"]

            # Get price data for symbol up to current date
            sym_prices = prices_df[
                (prices_df["symbol"] == symbol) & (prices_df.index <= date)
            ].sort_index()

            if len(sym_prices) < self.parameters["lookback"]:
                continue

            try:
                # Calculate momentum
                current_price = sym_prices.iloc[-1]["close_price"]
                past_price = sym_prices.iloc[-self.parameters["lookback"]][
                    "close_price"
                ]

                if past_price == 0:
                    continue

                momentum = (current_price - past_price) / past_price
                threshold = self.parameters["threshold"]

                # Generate signals
                if momentum > threshold:
                    strength = min(
                        momentum / (2 * threshold), 1.0
                    )  # Cap at 1.0
                    signals.append(
                        Signal(
                            symbol=symbol,
                            timestamp=date,
                            action=SignalAction.BUY,
                            signal_type="momentum_strong",
                            strength=strength,
                            target_position_pct=1.0,
                            reason=f"Strong uptrend momentum: {momentum:.2%}",
                            parameters=self.parameters,
                        )
                    )
                elif momentum < -threshold:
                    strength = min(abs(momentum) / (2 * threshold), 1.0)
                    signals.append(
                        Signal(
                            symbol=symbol,
                            timestamp=date,
                            action=SignalAction.SELL,
                            signal_type="momentum_weak",
                            strength=strength,
                            target_position_pct=0.5,
                            reason=f"Negative momentum: {momentum:.2%}",
                            parameters=self.parameters,
                        )
                    )
            except (IndexError, KeyError, ValueError):
                continue

        return signals


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using z-score signals."""

    def __init__(
        self,
        lookback: int = 20,
        z_threshold: float = 2.0,
        name: str = "mean_reversion",
    ):
        """
        Initialize mean reversion strategy.

        Args:
            lookback: Period for mean/std calculation (days)
            z_threshold: Z-score threshold for signals
            name: Strategy name
        """
        params = {"lookback": lookback, "z_threshold": z_threshold}
        super().__init__(name, params)

    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp,
    ) -> List[Signal]:
        """Generate mean reversion signals based on z-scores."""
        signals = []

        for _, holding in holdings_df.iterrows():
            symbol = holding["sym"]

            sym_prices = prices_df[
                (prices_df["symbol"] == symbol) & (prices_df.index <= date)
            ].sort_index()

            if len(sym_prices) < self.parameters["lookback"]:
                continue

            try:
                # Calculate z-score
                prices_window = sym_prices.iloc[-self.parameters["lookback"] :][
                    "close_price"
                ]
                mean_price = prices_window.mean()
                std_price = prices_window.std()
                current_price = prices_window.iloc[-1]

                if std_price == 0:
                    continue

                z_score = (current_price - mean_price) / std_price
                threshold = self.parameters["z_threshold"]

                # Generate signals
                if z_score < -threshold:
                    strength = min(abs(z_score) / (2 * threshold), 1.0)
                    signals.append(
                        Signal(
                            symbol=symbol,
                            timestamp=date,
                            action=SignalAction.BUY,
                            signal_type="reversion_oversold",
                            strength=strength,
                            target_position_pct=1.0,
                            reason=f"Oversold: {z_score:.2f}σ below mean",
                            parameters=self.parameters,
                        )
                    )
                elif z_score > threshold:
                    strength = min(abs(z_score) / (2 * threshold), 1.0)
                    signals.append(
                        Signal(
                            symbol=symbol,
                            timestamp=date,
                            action=SignalAction.SELL,
                            signal_type="reversion_overbought",
                            strength=strength,
                            target_position_pct=0.5,
                            reason=f"Overbought: {z_score:.2f}σ above mean",
                            parameters=self.parameters,
                        )
                    )
            except (IndexError, KeyError, ValueError, ZeroDivisionError):
                continue

        return signals


class SectorRotationStrategy(BaseStrategy):
    """Rotate between best and worst performing sectors."""

    def __init__(
        self,
        lookback: int = 60,
        name: str = "sector_rotation",
    ):
        """
        Initialize sector rotation strategy.

        Args:
            lookback: Period for sector performance calculation
            name: Strategy name
        """
        params = {"lookback": lookback}
        super().__init__(name, params)

    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp,
    ) -> List[Signal]:
        """Generate sector rotation signals."""
        signals = []

        try:
            # Group holdings by sector
            if "sector" not in holdings_df.columns:
                return signals

            sector_groups = holdings_df.groupby("sector")

            # Calculate sector returns
            sector_returns = {}
            for sector, group in sector_groups:
                sector_symbols = group["sym"].tolist()
                sector_prices = prices_df[
                    (prices_df["symbol"].isin(sector_symbols))
                    & (prices_df.index <= date)
                ].sort_index()

                if len(sector_prices) > 0:
                    # Calculate average return for sector
                    sector_prices_grouped = sector_prices.groupby("symbol")
                    returns = []

                    for sym, sym_data in sector_prices_grouped:
                        if len(sym_data) >= self.parameters["lookback"]:
                            first_price = sym_data.iloc[-self.parameters["lookback"]][
                                "close_price"
                            ]
                            last_price = sym_data.iloc[-1]["close_price"]
                            if first_price != 0:
                                ret = (last_price - first_price) / first_price
                                returns.append(ret)

                    if returns:
                        sector_returns[sector] = np.mean(returns)

            # Find best and worst sectors
            if len(sector_returns) >= 2:
                best_sector = max(sector_returns, key=sector_returns.get)
                worst_sector = min(sector_returns, key=sector_returns.get)

                # Generate signals
                for sector, group in sector_groups:
                    if sector == worst_sector:
                        for _, holding in group.iterrows():
                            signals.append(
                                Signal(
                                    symbol=holding["sym"],
                                    timestamp=date,
                                    action=SignalAction.REDUCE,
                                    signal_type="sector_rotation_exit",
                                    strength=0.7,
                                    target_position_pct=0.25,
                                    reason=f"Exit {sector} (worst: {sector_returns[sector]:.2%})",
                                    parameters=self.parameters,
                                )
                            )
                    elif sector == best_sector:
                        for _, holding in group.iterrows():
                            signals.append(
                                Signal(
                                    symbol=holding["sym"],
                                    timestamp=date,
                                    action=SignalAction.INCREASE,
                                    signal_type="sector_rotation_enter",
                                    strength=0.7,
                                    target_position_pct=1.0,
                                    reason=f"Increase {sector} (best: {sector_returns[sector]:.2%})",
                                    parameters=self.parameters,
                                )
                            )
        except Exception:
            pass

        return signals


class PortfolioBetaStrategy(BaseStrategy):
    """Adjust portfolio positioning based on target beta."""

    def __init__(
        self,
        target_beta: float = 1.0,
        lookback: int = 60,
        name: str = "portfolio_beta",
    ):
        """
        Initialize portfolio beta strategy.

        Args:
            target_beta: Target portfolio beta
            lookback: Period for beta calculation
            name: Strategy name
        """
        params = {"target_beta": target_beta, "lookback": lookback}
        super().__init__(name, params)

    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp,
    ) -> List[Signal]:
        """Generate beta-adjustment signals."""
        signals = []

        try:
            # Calculate portfolio beta
            portfolio_returns = []
            betas = {}

            for _, holding in holdings_df.iterrows():
                symbol = holding["sym"]
                sym_prices = prices_df[
                    (prices_df["symbol"] == symbol) & (prices_df.index <= date)
                ].sort_index()

                if len(sym_prices) < self.parameters["lookback"]:
                    continue

                # Calculate returns
                sym_returns = sym_prices["close_price"].pct_change().dropna()
                if len(sym_returns) > 0:
                    portfolio_returns.append(sym_returns.values)

                    # Estimate beta (vs equal-weight market proxy)
                    if len(sym_returns) >= self.parameters["lookback"]:
                        recent_returns = sym_returns.tail(
                            self.parameters["lookback"]
                        )
                        if len(recent_returns) > 1:
                            market_proxy = np.mean(portfolio_returns)
                            cov = np.cov(recent_returns, market_proxy)[0, 1]
                            var = np.var(market_proxy)
                            beta = cov / (var + 1e-6)
                            betas[symbol] = beta

            # Find high beta holdings to reduce
            if betas:
                avg_beta = np.mean(list(betas.values()))
                target = self.parameters["target_beta"]

                for symbol, beta in betas.items():
                    if beta > target + 0.2:  # High beta
                        signals.append(
                            Signal(
                                symbol=symbol,
                                timestamp=date,
                                action=SignalAction.REDUCE,
                                signal_type="beta_high",
                                strength=min((beta - target) / target, 1.0),
                                target_position_pct=0.5,
                                reason=f"High beta ({beta:.2f}) vs target ({target:.2f})",
                                parameters=self.parameters,
                            )
                        )
                    elif beta < target - 0.2:  # Low beta
                        signals.append(
                            Signal(
                                symbol=symbol,
                                timestamp=date,
                                action=SignalAction.INCREASE,
                                signal_type="beta_low",
                                strength=min((target - beta) / target, 1.0),
                                target_position_pct=1.0,
                                reason=f"Low beta ({beta:.2f}) vs target ({target:.2f})",
                                parameters=self.parameters,
                            )
                        )
        except Exception:
            pass

        return signals
