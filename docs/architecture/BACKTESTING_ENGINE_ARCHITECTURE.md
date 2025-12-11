# Backtesting Engine Architecture

## Overview

A production-ready backtesting engine designed to validate quick wins analytics (momentum, mean reversion, sector rotation, portfolio beta) and other trading strategies against historical portfolio data. The engine leverages your existing ParquetDB infrastructure and integrates seamlessly with Prefect workflows.

**Key Features:**
- Event-based backtesting with realistic portfolio mechanics
- Multi-strategy support (momentum, mean reversion, sector rotation, beta-based)
- Walk-forward validation and parameter optimization
- Commission, slippage, and cash management simulation
- Comprehensive performance metrics and tearsheets
- Parallel backtesting for multiple strategies

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Backtesting Engine                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Strategy Layer                                             │ │
│  │ ├─ MomentumStrategy (20-day momentum screening)            │ │
│  │ ├─ MeanReversionStrategy (z-score based)                   │ │
│  │ ├─ SectorRotationStrategy (sector allocation)              │ │
│  │ ├─ PortfolioBetaStrategy (beta targeting)                  │ │
│  │ └─ CustomStrategy (user-defined signals)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ Backtest Engine (Core)                                     │ │
│  │ ├─ Signal Generation (daily)                               │ │
│  │ ├─ Position Management                                      │ │
│  │ ├─ Order Execution                                          │ │
│  │ ├─ P&L Tracking                                             │ │
│  │ ├─ Risk Metrics (drawdown, Sharpe, etc.)                    │ │
│  │ └─ Portfolio State Snapshots                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ Data Pipeline                                              │ │
│  │ ├─ Load Historical Prices (ParquetDB)                       │ │
│  │ ├─ Load Historical Fundamentals                             │ │
│  │ ├─ Load Historical Technical Indicators                     │ │
│  │ ├─ Resample to Target Frequency                             │ │
│  │ └─ Data Validation & Gaps                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ Output & Analysis                                          │ │
│  │ ├─ Performance Metrics (Sharpe, Sortino, max DD)            │ │
│  │ ├─ Trade Tearsheets                                         │ │
│  │ ├─ Equity Curves & Drawdown Charts                          │ │
│  │ ├─ Monthly/Quarterly Returns Breakdown                      │ │
│  │ ├─ Attribution Analysis                                     │ │
│  │ └─ Parameter Sensitivity Analysis                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │ Storage Layer (ParquetDB)                                  │ │
│  │ ├─ backtest_runs (metadata)                                │ │
│  │ ├─ backtest_signals (daily signals)                        │ │
│  │ ├─ backtest_trades (executed trades)                       │ │
│  │ ├─ backtest_metrics (portfolio metrics)                    │ │
│  │ └─ backtest_results (summary statistics)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Strategy Base Class

**File:** `src/backtesting/strategies.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd

@dataclass
class Signal:
    """Trading signal for a position."""
    symbol: str
    timestamp: pd.Timestamp
    action: str  # "BUY", "SELL", "HOLD"
    signal_type: str  # "momentum", "mean_reversion", etc.
    strength: float  # 0.0-1.0 confidence
    target_position: float  # Desired quantity
    reason: str  # Explanation
    parameters: Dict  # Strategy parameters used

class BaseStrategy(ABC):
    """Abstract base class for all strategies."""
    
    def __init__(self, name: str, parameters: Dict):
        self.name = name
        self.parameters = parameters
    
    @abstractmethod
    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> List[Signal]:
        """
        Generate trading signals for given date.
        
        Args:
            prices_df: Historical OHLCV data
            technical_df: Technical indicators
            holdings_df: Current holdings
            date: Current backtest date
            
        Returns:
            List of trading signals
        """
        pass
    
    def set_parameters(self, **kwargs):
        """Update strategy parameters."""
        self.parameters.update(kwargs)
```

**Concrete Implementations:**

```python
class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy."""
    
    def __init__(self, lookback: int = 20, threshold: float = 0.10):
        super().__init__("momentum", {"lookback": lookback, "threshold": threshold})
    
    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> List[Signal]:
        """
        Generate momentum signals.
        
        Logic:
        - Calculate returns over lookback period
        - Buy if momentum > threshold
        - Sell if momentum < -threshold
        """
        signals = []
        
        for symbol in holdings_df["sym"]:
            # Get price data for symbol
            sym_prices = prices_df[prices_df["symbol"] == symbol].sort_index()
            
            if len(sym_prices) < self.parameters["lookback"]:
                continue
            
            # Calculate momentum
            current_price = sym_prices.iloc[-1]["close_price"]
            past_price = sym_prices.iloc[-self.parameters["lookback"]]["close_price"]
            momentum = (current_price - past_price) / past_price
            
            # Generate signal
            if momentum > self.parameters["threshold"]:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=date,
                    action="BUY",
                    signal_type="momentum_strong",
                    strength=min(momentum / (2 * self.parameters["threshold"]), 1.0),
                    target_position=1.0,  # Buy signal
                    reason=f"Momentum: {momentum:.2%}",
                    parameters=self.parameters
                ))
            elif momentum < -self.parameters["threshold"]:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=date,
                    action="SELL",
                    signal_type="momentum_weak",
                    strength=min(abs(momentum) / (2 * self.parameters["threshold"]), 1.0),
                    target_position=0.5,  # Reduce position
                    reason=f"Negative momentum: {momentum:.2%}",
                    parameters=self.parameters
                ))
        
        return signals


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy."""
    
    def __init__(self, lookback: int = 20, z_threshold: float = 2.0):
        super().__init__("mean_reversion", {
            "lookback": lookback,
            "z_threshold": z_threshold
        })
    
    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> List[Signal]:
        """
        Generate mean reversion signals based on z-scores.
        
        Logic:
        - Calculate z-score of current price
        - Buy if z-score < -threshold (oversold)
        - Sell if z-score > threshold (overbought)
        """
        signals = []
        
        for symbol in holdings_df["sym"]:
            sym_prices = prices_df[prices_df["symbol"] == symbol].sort_index()
            
            if len(sym_prices) < self.parameters["lookback"]:
                continue
            
            # Calculate z-score
            prices_window = sym_prices.iloc[-self.parameters["lookback"]:]["close_price"]
            mean_price = prices_window.mean()
            std_price = prices_window.std()
            current_price = prices_window.iloc[-1]
            
            z_score = (current_price - mean_price) / (std_price + 1e-6)
            
            # Generate signal
            threshold = self.parameters["z_threshold"]
            if z_score < -threshold:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=date,
                    action="BUY",
                    signal_type="reversion_oversold",
                    strength=min(abs(z_score) / (2 * threshold), 1.0),
                    target_position=1.0,
                    reason=f"Oversold: {z_score:.2f}σ below mean",
                    parameters=self.parameters
                ))
            elif z_score > threshold:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=date,
                    action="SELL",
                    signal_type="reversion_overbought",
                    strength=min(abs(z_score) / (2 * threshold), 1.0),
                    target_position=0.5,
                    reason=f"Overbought: {z_score:.2f}σ above mean",
                    parameters=self.parameters
                ))
        
        return signals


class SectorRotationStrategy(BaseStrategy):
    """Sector rotation strategy."""
    
    def __init__(self, lookback: int = 60, rotation_freq: int = 5):
        super().__init__("sector_rotation", {
            "lookback": lookback,
            "rotation_freq": rotation_freq
        })
    
    def generate_signals(
        self,
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> List[Signal]:
        """Generate sector rotation signals."""
        signals = []
        
        # Group holdings by sector
        sector_groups = holdings_df.groupby("sector")
        
        # Calculate sector returns
        sector_returns = {}
        for sector, group in sector_groups:
            sector_prices = prices_df[prices_df["symbol"].isin(group["sym"])]
            if len(sector_prices) > 0:
                sector_returns[sector] = sector_prices.groupby("symbol")["return_pct"].mean().mean()
        
        # Find best and worst sectors
        if sector_returns:
            best_sector = max(sector_returns, key=sector_returns.get)
            worst_sector = min(sector_returns, key=sector_returns.get)
            
            # Generate signals to rotate from worst to best
            for sector, group in sector_groups:
                if sector == worst_sector:
                    for _, holding in group.iterrows():
                        signals.append(Signal(
                            symbol=holding["sym"],
                            timestamp=date,
                            action="REDUCE",
                            signal_type="sector_rotation_exit",
                            strength=0.7,
                            target_position=0.25,
                            reason=f"Exit {sector} sector (worst performer)",
                            parameters=self.parameters
                        ))
                elif sector == best_sector:
                    for _, holding in group.iterrows():
                        signals.append(Signal(
                            symbol=holding["sym"],
                            timestamp=date,
                            action="INCREASE",
                            signal_type="sector_rotation_enter",
                            strength=0.7,
                            target_position=1.0,
                            reason=f"Increase {sector} sector (best performer)",
                            parameters=self.parameters
                        ))
        
        return signals
```

### 2. Backtest Engine

**File:** `src/backtesting/engine.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from enum import Enum

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
    exit_date: Optional[pd.Timestamp] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    entry_value: float = 0.0
    exit_value: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    direction: str = "long"  # "long" or "short"
    signal_type: str = ""
    reason: str = ""

@dataclass
class PortfolioSnapshot:
    """Daily portfolio state snapshot."""
    date: pd.Timestamp
    cash: float
    total_value: float
    gross_value: float
    net_exposure: float
    num_positions: int
    max_position_size: float
    concentration: float  # Herfindahl index
    leverage: float

class BacktestEngine:
    """Core backtesting engine."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        start_date: pd.Timestamp = None,
        end_date: pd.Timestamp = None,
        commission_pct: float = 0.001,
        slippage_bps: float = 5.0,
        max_position_pct: float = 0.10,
        rebalance_frequency: str = "daily",
        use_limit_orders: bool = False
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting cash
            start_date: Backtest start date
            end_date: Backtest end date
            commission_pct: Commission as % of trade value
            slippage_bps: Slippage in basis points
            max_position_pct: Max % of portfolio per position
            rebalance_frequency: How often to rebalance ("daily", "weekly", "monthly")
            use_limit_orders: Use limit orders instead of market orders
        """
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.commission_pct = commission_pct
        self.slippage_bps = slippage_bps
        self.max_position_pct = max_position_pct
        self.rebalance_frequency = rebalance_frequency
        self.use_limit_orders = use_limit_orders
        
        # State tracking
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> {qty, entry_price, entry_date}
        self.trades: List[Trade] = []
        self.portfolio_history: List[PortfolioSnapshot] = []
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = []
        
    def run(
        self,
        strategies: List[BaseStrategy],
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
        rebalance_dates: Optional[List[pd.Timestamp]] = None
    ) -> Dict:
        """
        Run backtest over date range.
        
        Args:
            strategies: List of strategy objects to run
            prices_df: Historical price data
            technical_df: Technical indicators
            holdings_df: Portfolio holdings
            rebalance_dates: Specific dates to rebalance
            
        Returns:
            Backtest results dictionary
        """
        
        # Generate date range
        date_range = pd.date_range(
            start=self.start_date,
            end=self.end_date,
            freq="B"  # Business days
        )
        
        equity_curve = [self.initial_capital]
        
        for date in date_range:
            # Get data up to this date
            prices_to_date = prices_df[prices_df.index <= date]
            technical_to_date = technical_df[technical_df.index <= date]
            
            # Generate signals from all strategies
            all_signals = []
            for strategy in strategies:
                signals = strategy.generate_signals(
                    prices_to_date,
                    technical_to_date,
                    holdings_df,
                    date
                )
                all_signals.extend(signals)
            
            # Execute trades based on signals
            for signal in all_signals:
                self._execute_signal(signal, prices_df, date)
            
            # Update portfolio value
            portfolio_value = self._calculate_portfolio_value(prices_df, date)
            equity_curve.append(portfolio_value)
            
            # Take snapshot
            self.portfolio_history.append(self._create_snapshot(date, portfolio_value))
        
        self.equity_curve = equity_curve
        
        # Calculate performance metrics
        metrics = self._calculate_metrics()
        
        return {
            "equity_curve": equity_curve,
            "trades": self.trades,
            "portfolio_history": self.portfolio_history,
            "metrics": metrics,
            "parameters": {
                "initial_capital": self.initial_capital,
                "commission_pct": self.commission_pct,
                "slippage_bps": self.slippage_bps,
            }
        }
    
    def _execute_signal(self, signal: Signal, prices_df: pd.DataFrame, date: pd.Timestamp):
        """Execute a trading signal."""
        
        # Get execution price (with slippage)
        symbol_prices = prices_df[
            (prices_df["symbol"] == signal.symbol) & 
            (prices_df.index <= date)
        ].sort_index()
        
        if len(symbol_prices) == 0:
            return
        
        execution_price = symbol_prices.iloc[-1]["close_price"]
        slippage = execution_price * (self.slippage_bps / 10000)
        
        if signal.action == "BUY":
            # Calculate position size
            max_position_value = self.initial_capital * self.max_position_pct
            position_qty = max_position_value / execution_price
            
            # Adjust for available cash
            trade_value = position_qty * execution_price
            commission = trade_value * self.commission_pct
            
            if self.cash >= trade_value + commission:
                self.cash -= (trade_value + commission)
                self.positions[signal.symbol] = {
                    "qty": position_qty,
                    "entry_price": execution_price,
                    "entry_date": date,
                    "signal_type": signal.signal_type
                }
                
                # Record trade
                self.trades.append(Trade(
                    trade_id=f"{signal.symbol}_{len(self.trades)}",
                    symbol=signal.symbol,
                    entry_date=date,
                    entry_price=execution_price + slippage,
                    quantity=position_qty,
                    entry_value=trade_value,
                    commission=commission,
                    slippage=slippage * position_qty,
                    signal_type=signal.signal_type,
                    reason=signal.reason
                ))
        
        elif signal.action == "SELL":
            # Close position
            if signal.symbol in self.positions:
                position = self.positions[signal.symbol]
                exit_value = position["qty"] * execution_price
                commission = exit_value * self.commission_pct
                
                self.cash += (exit_value - commission)
                
                # Calculate P&L
                pnl = exit_value - (position["qty"] * position["entry_price"])
                pnl_pct = pnl / (position["qty"] * position["entry_price"])
                
                # Update trade record (close)
                if len(self.trades) > 0:
                    self.trades[-1].exit_date = date
                    self.trades[-1].exit_price = execution_price - slippage
                    self.trades[-1].exit_value = exit_value
                    self.trades[-1].pnl = pnl - commission
                    self.trades[-1].pnl_pct = pnl_pct
                
                del self.positions[signal.symbol]
    
    def _calculate_portfolio_value(
        self,
        prices_df: pd.DataFrame,
        date: pd.Timestamp
    ) -> float:
        """Calculate total portfolio value at given date."""
        position_value = 0.0
        
        for symbol, position in self.positions.items():
            symbol_prices = prices_df[
                (prices_df["symbol"] == symbol) & 
                (prices_df.index <= date)
            ].sort_index()
            
            if len(symbol_prices) > 0:
                current_price = symbol_prices.iloc[-1]["close_price"]
                position_value += position["qty"] * current_price
        
        return self.cash + position_value
    
    def _create_snapshot(self, date: pd.Timestamp, portfolio_value: float) -> PortfolioSnapshot:
        """Create portfolio state snapshot."""
        total_position_value = portfolio_value - self.cash
        
        return PortfolioSnapshot(
            date=date,
            cash=self.cash,
            total_value=portfolio_value,
            gross_value=total_position_value,
            net_exposure=sum(p["qty"] for p in self.positions.values()),
            num_positions=len(self.positions),
            max_position_size=max([p["qty"] for p in self.positions.values()]) if self.positions else 0,
            concentration=self._calculate_herfindahl(),
            leverage=total_position_value / (portfolio_value + 1e-6)
        )
    
    def _calculate_herfindahl(self) -> float:
        """Calculate Herfindahl concentration index."""
        total_value = sum(p["qty"] for p in self.positions.values())
        if total_value == 0:
            return 0.0
        
        weights = [p["qty"] / total_value for p in self.positions.values()]
        return sum(w**2 for w in weights)
    
    def _calculate_metrics(self) -> Dict:
        """Calculate performance metrics."""
        
        if len(self.equity_curve) < 2:
            return {}
        
        equity_array = np.array(self.equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]
        
        # Sharpe Ratio (assuming 252 trading days, 0% risk-free rate)
        annual_return = (equity_array[-1] / equity_array[0]) ** (252 / len(returns)) - 1
        annual_std = np.std(returns) * np.sqrt(252)
        sharpe_ratio = annual_return / (annual_std + 1e-6)
        
        # Sortino Ratio (penalize only downside)
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = annual_return / (downside_std + 1e-6)
        
        # Maximum Drawdown
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # Win Rate
        winning_trades = len([t for t in self.trades if t.pnl and t.pnl > 0])
        total_trades = len(self.trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit Factor
        gross_profit = sum([t.pnl for t in self.trades if t.pnl and t.pnl > 0])
        gross_loss = abs(sum([t.pnl for t in self.trades if t.pnl and t.pnl < 0]))
        profit_factor = gross_profit / (gross_loss + 1e-6)
        
        return {
            "total_return_pct": ((equity_array[-1] / equity_array[0]) - 1) * 100,
            "annual_return_pct": annual_return * 100,
            "annual_volatility_pct": annual_std * 100,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown_pct": max_drawdown * 100,
            "win_rate_pct": win_rate * 100,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "avg_win_pnl": gross_profit / winning_trades if winning_trades > 0 else 0,
            "avg_loss_pnl": gross_loss / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0,
        }
```

### 3. Data Pipeline

**File:** `src/backtesting/data_loader.py`

```python
import pandas as pd
from typing import Dict, Optional
from src.parquet_db import ParquetDB

class BacktestDataLoader:
    """Loads and prepares data for backtesting."""
    
    def __init__(self, parquet_db: ParquetDB = None):
        self.db = parquet_db or ParquetDB()
    
    def load_backtest_data(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        resample_freq: str = "D"  # Daily
    ) -> tuple:
        """
        Load all data needed for backtesting.
        
        Args:
            symbols: List of ticker symbols
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            resample_freq: Frequency to resample to ("D", "W", "M")
            
        Returns:
            Tuple of (prices_df, technical_df, fundamental_df)
        """
        
        # Load prices
        prices_df = self.db.read_prices(symbols=symbols, start_date=start_date, end_date=end_date)
        
        # Load technical indicators
        technical_df = self.db.read_technical_analysis(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        
        # Load fundamental metrics
        fundamental_df = self.db.read_fundamental_analysis(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        
        # Resample if needed
        if resample_freq != "D":
            prices_df = self._resample_ohlcv(prices_df, resample_freq)
            technical_df = technical_df.resample(resample_freq).mean()
        
        return prices_df, technical_df, fundamental_df
    
    def _resample_ohlcv(self, prices_df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """Resample OHLCV data to new frequency."""
        
        resampled = prices_df.groupby([pd.Grouper(freq=freq), "symbol"]).agg({
            "open_price": "first",
            "high_price": "max",
            "low_price": "min",
            "close_price": "last",
            "volume": "sum"
        }).reset_index()
        
        return resampled
```

### 4. Prefect Flow Integration

**File:** `src/backtesting_flows.py`

```python
from prefect import flow, task, get_run_logger
from typing import Dict, List
import pandas as pd
from datetime import datetime, timedelta

from .backtesting.engine import BacktestEngine
from .backtesting.strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    SectorRotationStrategy,
    PortfolioBetaStrategy
)
from .backtesting.data_loader import BacktestDataLoader
from .parquet_db import ParquetDB

@task(name="load_backtest_data")
def load_backtest_data_task(
    symbols: List[str],
    start_date: str,
    end_date: str
) -> tuple:
    """Load historical data for backtesting."""
    loader = BacktestDataLoader()
    prices_df, technical_df, fundamental_df = loader.load_backtest_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )
    return prices_df, technical_df, fundamental_df

@task(name="run_momentum_backtest")
def run_momentum_backtest(
    prices_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    lookback: int = 20,
    threshold: float = 0.10
) -> Dict:
    """Run momentum strategy backtest."""
    
    engine = BacktestEngine(
        initial_capital=100000.0,
        commission_pct=0.001,
        slippage_bps=5.0
    )
    
    strategy = MomentumStrategy(lookback=lookback, threshold=threshold)
    
    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df
    )
    
    return results

@task(name="save_backtest_results")
def save_backtest_results_task(
    backtest_results: Dict,
    strategy_name: str,
    run_id: str
) -> str:
    """Save backtest results to ParquetDB."""
    
    db = ParquetDB()
    
    # Save metadata
    run_metadata = pd.DataFrame([{
        "run_id": run_id,
        "strategy": strategy_name,
        "timestamp": datetime.now(),
        "total_return": backtest_results["metrics"]["total_return_pct"],
        "sharpe_ratio": backtest_results["metrics"]["sharpe_ratio"],
        "max_drawdown": backtest_results["metrics"]["max_drawdown_pct"],
        "total_trades": backtest_results["metrics"]["total_trades"],
        "win_rate": backtest_results["metrics"]["win_rate_pct"]
    }])
    
    # Save trades
    trades_df = pd.DataFrame([
        {
            "run_id": run_id,
            "trade_id": t.trade_id,
            "symbol": t.symbol,
            "entry_date": t.entry_date,
            "exit_date": t.exit_date,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "signal_type": t.signal_type
        } for t in backtest_results["trades"]
    ])
    
    # Save portfolio snapshots
    portfolio_df = pd.DataFrame([
        {
            "run_id": run_id,
            "date": p.date,
            "total_value": p.total_value,
            "cash": p.cash,
            "leverage": p.leverage,
            "num_positions": p.num_positions,
            "concentration": p.concentration
        } for p in backtest_results["portfolio_history"]
    ])
    
    # Write to DB
    db.upsert_backtest_runs(run_metadata)
    db.upsert_backtest_trades(trades_df)
    db.upsert_backtest_metrics(portfolio_df)
    
    return run_id

@flow(name="backtest_quick_wins_strategies")
def backtest_quick_wins_flow(
    symbols: List[str],
    start_date: str = None,
    end_date: str = None,
    strategies: List[str] = None
) -> Dict:
    """
    Main flow to backtest quick wins strategies.
    
    Args:
        symbols: List of tickers to backtest
        start_date: Backtest start (default: 1 year ago)
        end_date: Backtest end (default: today)
        strategies: List of strategy names to run (default: all)
    
    Returns:
        Results for all tested strategies
    """
    
    # Default dates
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    # Load data
    prices_df, technical_df, fundamental_df = load_backtest_data_task(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date
    )
    
    # Create holdings DataFrame
    holdings_df = pd.DataFrame({"sym": symbols, "sector": ["Tech"] * len(symbols)})
    
    # Default strategies
    if strategies is None:
        strategies = ["momentum", "mean_reversion", "sector_rotation", "beta"]
    
    results = {}
    
    if "momentum" in strategies:
        mom_results = run_momentum_backtest(prices_df, technical_df, holdings_df)
        run_id = save_backtest_results_task(mom_results, "momentum", "backtest_mom_001")
        results["momentum"] = mom_results
    
    # Similar for other strategies...
    
    return results
```

---

## Database Schema Extensions

Add to `ParquetDB` for backtesting data:

```python
# Backtesting tables
BACKTEST_RUNS_SCHEMA = pa.schema([
    ('run_id', pa.string()),
    ('strategy', pa.string()),
    ('timestamp', pa.timestamp('us')),
    ('initial_capital', pa.float64()),
    ('total_return_pct', pa.float64()),
    ('sharpe_ratio', pa.float64()),
    ('sortino_ratio', pa.float64()),
    ('max_drawdown_pct', pa.float64()),
    ('total_trades', pa.int64()),
    ('win_rate_pct', pa.float64()),
    ('profit_factor', pa.float64()),
])

BACKTEST_TRADES_SCHEMA = pa.schema([
    ('run_id', pa.string()),
    ('trade_id', pa.string()),
    ('symbol', pa.string()),
    ('entry_date', pa.timestamp('us')),
    ('exit_date', pa.timestamp('us')),
    ('entry_price', pa.float64()),
    ('exit_price', pa.float64()),
    ('quantity', pa.float64()),
    ('pnl', pa.float64()),
    ('pnl_pct', pa.float64()),
    ('signal_type', pa.string()),
])

BACKTEST_METRICS_SCHEMA = pa.schema([
    ('run_id', pa.string()),
    ('date', pa.timestamp('us')),
    ('total_value', pa.float64()),
    ('cash', pa.float64()),
    ('leverage', pa.float64()),
    ('num_positions', pa.int64()),
    ('concentration', pa.float64()),
])
```

---

## Usage Examples

### Basic Momentum Backtest

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.strategies import MomentumStrategy
from src.backtesting.data_loader import BacktestDataLoader

# Load data
loader = BacktestDataLoader()
prices_df, technical_df, fundamental_df = loader.load_backtest_data(
    symbols=["AAPL", "MSFT", "GOOGL"],
    start_date="2023-01-01",
    end_date="2024-12-31"
)

# Create strategy
strategy = MomentumStrategy(lookback=20, threshold=0.10)

# Run backtest
engine = BacktestEngine(
    initial_capital=100000.0,
    commission_pct=0.001,
    slippage_bps=5.0
)

results = engine.run(
    strategies=[strategy],
    prices_df=prices_df,
    technical_df=technical_df,
    holdings_df=pd.DataFrame({"sym": ["AAPL", "MSFT", "GOOGL"]})
)

# Analyze
print(f"Total Return: {results['metrics']['total_return_pct']:.2f}%")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['metrics']['max_drawdown_pct']:.2f}%")
print(f"Win Rate: {results['metrics']['win_rate_pct']:.2f}%")
```

### Multiple Strategies with Prefect

```python
from src.backtesting_flows import backtest_quick_wins_flow

results = backtest_quick_wins_flow(
    symbols=["AAPL", "MSFT", "GOOGL", "TSLA", "META"],
    start_date="2023-01-01",
    end_date="2024-12-31",
    strategies=["momentum", "mean_reversion", "sector_rotation"]
)

print(results["momentum"]["metrics"])
print(results["mean_reversion"]["metrics"])
```

### Parameter Optimization

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.strategies import MomentumStrategy

# Test multiple lookback periods
results_by_lookback = {}

for lookback in [10, 15, 20, 30, 50]:
    strategy = MomentumStrategy(lookback=lookback, threshold=0.10)
    engine = BacktestEngine()
    
    results = engine.run(
        strategies=[strategy],
        prices_df=prices_df,
        technical_df=technical_df,
        holdings_df=holdings_df
    )
    
    results_by_lookback[lookback] = results["metrics"]["sharpe_ratio"]

# Find optimal
optimal_lookback = max(results_by_lookback, key=results_by_lookback.get)
print(f"Optimal lookback: {optimal_lookback}")
```

---

## Key Design Principles

1. **Modularity**: Strategies are pluggable; add custom strategies by inheriting `BaseStrategy`
2. **Realism**: Commission, slippage, and position sizing constraints built-in
3. **Integration**: Uses existing ParquetDB for data and Prefect for orchestration
4. **Scalability**: Can backtest multiple strategies in parallel via Prefect
5. **Auditability**: All trades, signals, and snapshots recorded for analysis
6. **Extensibility**: Easy to add new metrics, risk measures, or strategy constraints

---

## Implementation Roadmap

**Phase 1 (Week 1):**
- Core engine and base strategy class
- Momentum and mean reversion strategies
- Basic performance metrics

**Phase 2 (Week 2):**
- Data loader and ParquetDB integration
- Sector rotation strategy
- Portfolio beta strategy
- Prefect flow integration

**Phase 3 (Week 3):**
- Parameter optimization framework
- Walk-forward validation
- Performance reporting and visualization
- Tearsheet generation

**Phase 4 (Week 4+):**
- Multi-strategy ensemble
- Risk controls and constraints
- Live/walk-forward mode
- Advanced metrics (information ratio, Calmar ratio)

---

## Performance Metrics Reference

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| Sharpe Ratio | (Return - RF) / StdDev | Higher = better risk-adjusted returns |
| Sortino Ratio | (Return - RF) / DownsideStdDev | Like Sharpe but penalizes only downside |
| Max Drawdown | Min(Cumulative Return) | Worst peak-to-trough decline |
| Win Rate | Winning Trades / Total Trades | % of profitable trades |
| Profit Factor | Gross Profit / Gross Loss | Higher = better, >1.5 is good |
| Information Ratio | (Strategy Return - Benchmark) / Tracking Error | Excess return per unit of risk |

---

## Common Pitfalls to Avoid

1. **Look-ahead bias**: Ensure data isn't used before available date
2. **Survivorship bias**: Include delisted/bankrupt companies in backtest
3. **Overfitting**: Test on out-of-sample data, use walk-forward validation
4. **Ignoring costs**: Always include realistic commission and slippage
5. **Single market regime**: Test across bull/bear markets, different volatility periods
6. **Ignoring liquidity**: Position sizing should account for actual trading volume
