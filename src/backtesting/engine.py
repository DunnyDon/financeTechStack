"""Core backtesting engine with order execution, position management, and metrics."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order execution types."""
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Trade:
    """Executed trade record."""
    trade_id: str
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    quantity: float
    entry_value: float
    commission: float = 0.0
    slippage: float = 0.0
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    direction: str = "long"  # "long" or "short"
    signal_type: str = ""
    reason: str = ""
    bars_held: int = 0

    def __post_init__(self):
        """Validate trade data."""
        if self.entry_price <= 0:
            raise ValueError(f"Entry price must be positive: {self.entry_price}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")


@dataclass
class PortfolioSnapshot:
    """Daily portfolio state snapshot."""
    date: pd.Timestamp
    cash: float
    total_value: float
    gross_value: float = 0.0
    net_exposure: float = 0.0
    num_positions: int = 0
    max_position_size: float = 0.0
    concentration: float = 0.0  # Herfindahl index
    leverage: float = 0.0
    daily_return: float = 0.0
    cumulative_return: float = 0.0


class BacktestEngine:
    """Core backtesting engine for strategy validation."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None,
        commission_pct: float = 0.001,
        slippage_bps: float = 5.0,
        max_position_pct: float = 0.10,
        rebalance_frequency: str = "daily",
        use_limit_orders: bool = False,
        name: str = "backtest",
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting cash
            start_date: Backtest start date
            end_date: Backtest end date
            commission_pct: Commission as % of trade value (0.001 = 0.1%)
            slippage_bps: Slippage in basis points
            max_position_pct: Max % of portfolio per position
            rebalance_frequency: How often to rebalance ("daily", "weekly", "monthly")
            use_limit_orders: Use limit orders instead of market orders
            name: Backtest name for logging
        """
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.commission_pct = commission_pct
        self.slippage_bps = slippage_bps
        self.max_position_pct = max_position_pct
        self.rebalance_frequency = rebalance_frequency
        self.use_limit_orders = use_limit_orders
        self.name = name

        # State tracking
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> {qty, entry_price, entry_date}
        self.trades: List[Trade] = []
        self.portfolio_history: List[PortfolioSnapshot] = []
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = [initial_capital]
        self.trade_counter = 0

    def run(
        self,
        strategies: List,
        prices_df: pd.DataFrame,
        technical_df: Optional[pd.DataFrame],
        holdings_df: pd.DataFrame,
        rebalance_dates: Optional[List[pd.Timestamp]] = None,
    ) -> Dict:
        """
        Run backtest over date range.

        Args:
            strategies: List of strategy objects
            prices_df: Historical price data (indexed by date, with symbol column)
            technical_df: Technical indicators (optional)
            holdings_df: Portfolio holdings (symbol, sector, etc.)
            rebalance_dates: Specific dates to rebalance (optional)

        Returns:
            Backtest results dictionary
        """
        if technical_df is None:
            technical_df = pd.DataFrame()

        # Generate date range
        unique_dates = sorted(prices_df.index.unique())
        
        # Handle None start/end dates
        start_date = self.start_date if self.start_date is not None else unique_dates[0]
        end_date = self.end_date if self.end_date is not None else unique_dates[-1]
        
        date_range = [d for d in unique_dates if start_date <= d <= end_date]

        if not date_range:
            logger.warning(f"No data in date range {start_date} to {end_date}")
            return self._get_empty_results()

        previous_value = self.initial_capital

        for date in date_range:
            # Get data up to this date
            prices_to_date = prices_df[prices_df.index <= date]
            technical_to_date = (
                technical_df[technical_df.index <= date]
                if not technical_df.empty
                else pd.DataFrame()
            )

            # Generate signals from all strategies
            all_signals = []
            for strategy in strategies:
                try:
                    signals = strategy.generate_signals(
                        prices_to_date, technical_to_date, holdings_df, date
                    )
                    all_signals.extend(signals)
                except Exception as e:
                    logger.warning(
                        f"Strategy {strategy.name} failed on {date}: {e}"
                    )
                    continue

            # Execute trades based on signals
            for signal in all_signals:
                self._execute_signal(signal, prices_df, date)

            # Update portfolio value
            portfolio_value = self._calculate_portfolio_value(prices_df, date)
            daily_return = (portfolio_value - previous_value) / previous_value
            self.daily_returns.append(daily_return)
            self.equity_curve.append(portfolio_value)

            # Take snapshot
            snapshot = self._create_snapshot(
                date, portfolio_value, previous_value, daily_return
            )
            self.portfolio_history.append(snapshot)

            previous_value = portfolio_value

        # Calculate performance metrics
        metrics = self._calculate_metrics()

        return {
            "equity_curve": self.equity_curve,
            "trades": self.trades,
            "portfolio_history": self.portfolio_history,
            "metrics": metrics,
            "parameters": {
                "initial_capital": self.initial_capital,
                "commission_pct": self.commission_pct,
                "slippage_bps": self.slippage_bps,
                "max_position_pct": self.max_position_pct,
            },
        }

    def _execute_signal(
        self, signal, prices_df: pd.DataFrame, date: pd.Timestamp
    ):
        """Execute a trading signal."""
        from .strategies import SignalAction

        # Get execution price (with slippage)
        symbol_prices = prices_df[
            (prices_df["symbol"] == signal.symbol) & (prices_df.index <= date)
        ].sort_index()

        if len(symbol_prices) == 0:
            return

        execution_price = symbol_prices.iloc[-1]["close_price"]
        slippage = execution_price * (self.slippage_bps / 10000)

        if signal.action == SignalAction.BUY:
            self._execute_buy(
                signal, execution_price, slippage, date, prices_df
            )
        elif signal.action == SignalAction.SELL:
            self._execute_sell(
                signal, execution_price, slippage, date, prices_df
            )
        elif signal.action in [SignalAction.REDUCE, SignalAction.INCREASE]:
            self._execute_reposition(
                signal, execution_price, slippage, date, prices_df
            )

    def _execute_buy(
        self,
        signal,
        execution_price: float,
        slippage: float,
        date: pd.Timestamp,
        prices_df: pd.DataFrame,
    ):
        """Execute buy signal."""
        max_position_value = self.initial_capital * self.max_position_pct
        position_qty = max_position_value / execution_price

        trade_value = position_qty * execution_price
        commission = trade_value * self.commission_pct

        if self.cash >= trade_value + commission:
            self.cash -= trade_value + commission
            self.positions[signal.symbol] = {
                "qty": position_qty,
                "entry_price": execution_price + slippage,
                "entry_date": date,
                "signal_type": signal.signal_type,
                "bars_held": 0,
            }

            # Record trade
            self.trade_counter += 1
            self.trades.append(
                Trade(
                    trade_id=f"{signal.symbol}_{self.trade_counter}",
                    symbol=signal.symbol,
                    entry_date=date,
                    entry_price=execution_price + slippage,
                    quantity=position_qty,
                    entry_value=trade_value,
                    commission=commission,
                    slippage=slippage * position_qty,
                    signal_type=signal.signal_type,
                    reason=signal.reason,
                )
            )

    def _execute_sell(
        self,
        signal,
        execution_price: float,
        slippage: float,
        date: pd.Timestamp,
        prices_df: pd.DataFrame,
    ):
        """Execute sell signal."""
        if signal.symbol in self.positions:
            position = self.positions[signal.symbol]
            exit_value = position["qty"] * execution_price
            commission = exit_value * self.commission_pct

            self.cash += exit_value - commission

            # Calculate P&L
            pnl = exit_value - (position["qty"] * position["entry_price"])
            pnl_pct = pnl / (position["qty"] * position["entry_price"])

            # Close trade
            bars_held = len(
                prices_df[
                    (prices_df["symbol"] == signal.symbol)
                    & (prices_df.index >= position["entry_date"])
                    & (prices_df.index <= date)
                ]
            )

            # Find and update trade record
            for trade in reversed(self.trades):
                if (
                    trade.symbol == signal.symbol
                    and trade.exit_date is None
                    and trade.entry_date == position["entry_date"]
                ):
                    trade.exit_date = date
                    trade.exit_price = execution_price - slippage
                    trade.exit_value = exit_value
                    trade.pnl = pnl - commission
                    trade.pnl_pct = pnl_pct
                    trade.bars_held = bars_held
                    break

            del self.positions[signal.symbol]

    def _execute_reposition(
        self,
        signal,
        execution_price: float,
        slippage: float,
        date: pd.Timestamp,
        prices_df: pd.DataFrame,
    ):
        """Execute position adjustment."""
        from .strategies import SignalAction

        if signal.action == SignalAction.REDUCE:
            if signal.symbol in self.positions:
                position = self.positions[signal.symbol]
                # Reduce position by percentage
                reduction_qty = position["qty"] * (1 - signal.target_position_pct)

                if reduction_qty > 0:
                    exit_value = reduction_qty * execution_price
                    commission = exit_value * self.commission_pct
                    self.cash += exit_value - commission

                    # Update position
                    position["qty"] -= reduction_qty

                    if position["qty"] <= 0:
                        del self.positions[signal.symbol]

        elif signal.action == SignalAction.INCREASE:
            if signal.symbol in self.positions:
                position = self.positions[signal.symbol]
                # Increase position
                current_value = position["qty"] * execution_price
                target_value = self.initial_capital * signal.target_position_pct
                increase_qty = (target_value - current_value) / execution_price

                trade_value = increase_qty * execution_price
                commission = trade_value * self.commission_pct

                if self.cash >= trade_value + commission:
                    self.cash -= trade_value + commission
                    position["qty"] += increase_qty

    def _calculate_portfolio_value(
        self, prices_df: pd.DataFrame, date: pd.Timestamp
    ) -> float:
        """Calculate total portfolio value at given date."""
        position_value = 0.0

        for symbol, position in self.positions.items():
            symbol_prices = prices_df[
                (prices_df["symbol"] == symbol) & (prices_df.index <= date)
            ].sort_index()

            if len(symbol_prices) > 0:
                current_price = symbol_prices.iloc[-1]["close_price"]
                position_value += position["qty"] * current_price

        return self.cash + position_value

    def _create_snapshot(
        self,
        date: pd.Timestamp,
        portfolio_value: float,
        previous_value: float,
        daily_return: float,
    ) -> PortfolioSnapshot:
        """Create portfolio state snapshot."""
        total_position_value = portfolio_value - self.cash
        cumulative_return = (
            (portfolio_value / self.initial_capital) - 1
        ) * 100

        return PortfolioSnapshot(
            date=date,
            cash=self.cash,
            total_value=portfolio_value,
            gross_value=total_position_value,
            net_exposure=sum(p["qty"] for p in self.positions.values()),
            num_positions=len(self.positions),
            max_position_size=max(
                [p["qty"] for p in self.positions.values()]
                if self.positions
                else [0]
            ),
            concentration=self._calculate_herfindahl(),
            leverage=total_position_value / (portfolio_value + 1e-6),
            daily_return=daily_return * 100,
            cumulative_return=cumulative_return,
        )

    def _calculate_herfindahl(self) -> float:
        """Calculate Herfindahl concentration index."""
        if not self.positions:
            return 0.0

        total_value = sum(p["qty"] for p in self.positions.values())
        if total_value == 0:
            return 0.0

        weights = [p["qty"] / total_value for p in self.positions.values()]
        return sum(w**2 for w in weights)

    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics."""
        if len(self.equity_curve) < 2:
            return self._get_empty_metrics()

        equity_array = np.array(self.equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]

        # Annual metrics (assuming 252 trading days)
        total_return = (equity_array[-1] / equity_array[0]) - 1
        days = len(returns)
        years = days / 252.0
        annual_return = (equity_array[-1] / equity_array[0]) ** (1 / years) - 1

        annual_std = np.std(returns) * np.sqrt(252)
        sharpe_ratio = (
            annual_return / (annual_std + 1e-6) if annual_std > 0 else 0
        )

        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_std = (
            np.std(downside_returns) * np.sqrt(252)
            if len(downside_returns) > 0
            else 0
        )
        sortino_ratio = (
            annual_return / (downside_std + 1e-6) if downside_std > 0 else 0
        )

        # Maximum Drawdown
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = np.min(drawdown)

        # Calmar Ratio
        calmar_ratio = (
            annual_return / (abs(max_drawdown) + 1e-6)
            if max_drawdown != 0
            else 0
        )

        # Win Rate
        winning_trades = len([t for t in self.trades if t.pnl and t.pnl > 0])
        total_trades = len(self.trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Profit Factor
        gross_profit = sum(
            [t.pnl for t in self.trades if t.pnl and t.pnl > 0]
        )
        gross_loss = abs(
            sum([t.pnl for t in self.trades if t.pnl and t.pnl < 0])
        )
        profit_factor = gross_profit / (gross_loss + 1e-6)

        # Trade statistics
        closed_trades = [t for t in self.trades if t.exit_date is not None]
        avg_bars_held = (
            np.mean([t.bars_held for t in closed_trades])
            if closed_trades
            else 0
        )

        return {
            "total_return_pct": total_return * 100,
            "annual_return_pct": annual_return * 100,
            "annual_volatility_pct": annual_std * 100,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "max_drawdown_pct": max_drawdown * 100,
            "win_rate_pct": win_rate * 100,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "avg_bars_held": avg_bars_held,
            "avg_win_pnl": gross_profit / winning_trades if winning_trades > 0 else 0,
            "avg_loss_pnl": gross_loss / (total_trades - winning_trades)
            if (total_trades - winning_trades) > 0
            else 0,
        }

    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            "total_return_pct": 0.0,
            "annual_return_pct": 0.0,
            "annual_volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_bars_held": 0.0,
            "avg_win_pnl": 0.0,
            "avg_loss_pnl": 0.0,
        }

    def _get_empty_results(self) -> Dict:
        """Return empty results structure."""
        return {
            "equity_curve": self.equity_curve,
            "trades": [],
            "portfolio_history": [],
            "metrics": self._get_empty_metrics(),
            "parameters": {
                "initial_capital": self.initial_capital,
                "commission_pct": self.commission_pct,
                "slippage_bps": self.slippage_bps,
                "max_position_pct": self.max_position_pct,
            },
        }
