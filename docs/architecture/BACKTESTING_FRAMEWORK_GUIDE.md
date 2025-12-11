# Backtesting Framework - Complete Implementation Guide

## Overview

A production-ready backtesting framework integrated with **Prefect** workflows and **Dask** distributed computing for parallel strategy testing and parameter optimization.

**Key Features:**
- ✅ Event-based backtesting engine with realistic order execution
- ✅ 4 pre-built strategies (Momentum, Mean Reversion, Sector Rotation, Portfolio Beta)
- ✅ Prefect workflow integration for task orchestration
- ✅ Dask parallelization for distributed backtesting
- ✅ Comprehensive metrics (Sharpe, Sortino, Calmar, Information Ratio)
- ✅ Parameter optimization and grid search
- ✅ Walk-forward validation for robustness testing
- ✅ Trade analysis and performance reporting

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│          Backtesting Framework                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Prefect Flows Layer                             │  │
│  │  ├─ Single Strategy Backtests                   │  │
│  │  ├─ Multi-Strategy Parallel Backtests           │  │
│  │  └─ Dask-Distributed Parameter Optimization    │  │
│  └─────────────────────────────────────────────────┘  │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐  │
│  │ Backtesting Engine                              │  │
│  │  ├─ Signal Generation (daily)                   │  │
│  │  ├─ Order Execution (MARKET/LIMIT)              │  │
│  │  ├─ Position Management                         │  │
│  │  ├─ P&L Tracking & Portfolio State              │  │
│  │  └─ Metrics Calculation                         │  │
│  └─────────────────────────────────────────────────┘  │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐  │
│  │ Strategy Layer                                  │  │
│  │  ├─ MomentumStrategy                            │  │
│  │  ├─ MeanReversionStrategy                       │  │
│  │  ├─ SectorRotationStrategy                      │  │
│  │  ├─ PortfolioBetaStrategy                       │  │
│  │  └─ BaseStrategy (for custom strategies)        │  │
│  └─────────────────────────────────────────────────┘  │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐  │
│  │ Data Pipeline                                   │  │
│  │  ├─ ParquetDB Integration                       │  │
│  │  ├─ Price/Technical/Fundamental Loading         │  │
│  │  ├─ Data Validation & Gaps                      │  │
│  │  └─ Resampling (D/W/M)                          │  │
│  └─────────────────────────────────────────────────┘  │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐  │
│  │ Analysis & Reporting                            │  │
│  │  ├─ BacktestAnalyzer                            │  │
│  │  ├─ Performance Metrics                         │  │
│  │  ├─ Trade Analysis & Tearsheets                 │  │
│  │  └─ Risk Analysis                               │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Backtesting Engine (`engine.py`)

**Responsible for:**
- Daily signal generation from strategies
- Order execution with slippage and commission
- Position management and tracking
- Portfolio P&L calculation
- Metric computation

**Key Classes:**
```python
class BacktestEngine:
    """Core backtesting engine."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.001,  # 0.1%
        slippage_bps: float = 5.0,      # 5 basis points
        max_position_pct: float = 0.10,  # 10% max per position
    )
    
    def run(
        self,
        strategies: List[BaseStrategy],
        prices_df: pd.DataFrame,
        technical_df: pd.DataFrame,
        holdings_df: pd.DataFrame,
    ) -> Dict:
        """Run backtest and return results."""
```

### 2. Strategy Base Classes (`strategies.py`)

**4 Pre-built Strategies:**

#### MomentumStrategy
Generates buy/sell signals based on n-day momentum
```python
strategy = MomentumStrategy(lookback=20, threshold=0.10)
# Buys if momentum > 10%, sells if < -10%
```

#### MeanReversionStrategy
Generates signals based on z-score deviations
```python
strategy = MeanReversionStrategy(lookback=20, z_threshold=2.0)
# Buys if price < -2σ from mean, sells if > +2σ
```

#### SectorRotationStrategy
Rotates between best/worst performing sectors
```python
strategy = SectorRotationStrategy(lookback=60)
# Increases positions in best sector, decreases in worst
```

#### PortfolioBetaStrategy
Adjusts positioning to target portfolio beta
```python
strategy = PortfolioBetaStrategy(target_beta=1.0, lookback=60)
# Reduces high-beta holdings, increases low-beta holdings
```

### 3. Data Loader (`data_loader.py`)

Loads and validates data from ParquetDB
```python
loader = BacktestDataLoader()
prices_df, technical_df, fundamental_df = loader.load_backtest_data(
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2024-12-31"
)
```

### 4. Analysis & Reporting (`analyzer.py`)

Comprehensive backtest analysis
```python
analyzer = BacktestAnalyzer(results)
print(analyzer.summary())
print(analyzer.best_trades(n=5))
print(analyzer.by_symbol())
print(analyzer.risk_analysis())
```

---

## Prefect Integration

### Single Strategy Backtest
```python
from src.backtesting.backtesting_flows import backtest_single_strategy_flow

results = backtest_single_strategy_flow(
    symbols=["AAPL", "MSFT", "GOOGL"],
    strategy_name="momentum",
    strategy_params={"lookback": 20, "threshold": 0.10},
    start_date="2023-01-01",
    end_date="2024-12-31"
)
```

### Multiple Strategies in Parallel
```python
from src.backtesting.backtesting_flows import backtest_multiple_strategies_flow

results = backtest_multiple_strategies_flow(
    symbols=["AAPL", "MSFT"],
    strategies={
        "momentum": {"lookback": 20, "threshold": 0.10},
        "mean_reversion": {"lookback": 20, "z_threshold": 2.0},
        "sector_rotation": {"lookback": 60},
    }
)
# Returns: {"momentum": {...}, "mean_reversion": {...}, ...}
```

---

## Dask Distributed Computing

### Parameter Grid Search
```python
from src.backtesting.dask_backtesting_flows import parameter_optimization_flow

optimal_params, results_df = parameter_optimization_flow(
    symbols=["AAPL", "MSFT", "GOOGL"],
    strategy_name="momentum",
    param_grid={
        "lookback": [10, 15, 20, 25, 30],
        "threshold": [0.05, 0.10, 0.15, 0.20],
    },
    optimization_metric="sharpe_ratio"
)
# Tests 5×4=20 combinations in parallel across Dask workers
```

**How it works:**
1. Creates all parameter combinations
2. Submits each as a task to Dask scheduler
3. Distributes across available workers
4. Returns results as completed (not blocking on slow jobs)
5. Finds optimal parameters by specified metric

### Walk-Forward Validation
```python
from src.backtesting.dask_backtesting_flows import walk_forward_validation_flow

results_df = walk_forward_validation_flow(
    symbols=["AAPL", "MSFT", "GOOGL"],
    strategy_name="momentum",
    strategy_params={"lookback": 20, "threshold": 0.10},
    total_days=365,
    train_days=252,      # 1-year training windows
    test_days=30,        # Monthly test periods
)
# Validates strategy robustness across time periods
```

---

## Key Metrics

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| **Sharpe Ratio** | (Return - RF) / Volatility | Risk-adjusted return; higher is better |
| **Sortino Ratio** | (Return - RF) / Downside Volatility | Like Sharpe but penalizes only downside |
| **Calmar Ratio** | Annual Return / Max Drawdown | Return per unit of maximum risk taken |
| **Max Drawdown** | (Peak - Trough) / Peak | Worst peak-to-trough decline |
| **Win Rate** | Winning Trades / Total Trades | % of profitable trades |
| **Profit Factor** | Gross Profit / Gross Loss | Total profit divided by total loss |
| **Information Ratio** | Excess Return / Tracking Error | Excess return vs benchmark per unit of risk |

---

## Usage Examples

### Example 1: Single Strategy Backtest (Standalone)
```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.strategies import MomentumStrategy
from src.backtesting.data_loader import BacktestDataLoader
from src.backtesting.analyzer import BacktestAnalyzer

# Load data
loader = BacktestDataLoader()
prices_df, technical_df, _ = loader.load_backtest_data(
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2024-12-31"
)

holdings_df = pd.DataFrame({"sym": ["AAPL", "MSFT"], "sector": ["Tech", "Tech"]})

# Create strategy and engine
strategy = MomentumStrategy(lookback=20, threshold=0.10)
engine = BacktestEngine(initial_capital=100000.0)

# Run backtest
results = engine.run(
    strategies=[strategy],
    prices_df=prices_df,
    technical_df=technical_df,
    holdings_df=holdings_df
)

# Analyze
analyzer = BacktestAnalyzer(results)
print(analyzer.summary())
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
```

### Example 2: Parameter Optimization with Dask
```python
from src.backtesting.dask_backtesting_flows import parameter_optimization_flow

optimal_params, results_df = parameter_optimization_flow(
    symbols=["AAPL", "MSFT", "GOOGL"],
    strategy_name="momentum",
    param_grid={
        "lookback": [10, 15, 20, 25, 30],
        "threshold": [0.05, 0.10, 0.15],
    },
    optimization_metric="sharpe_ratio"
)

print(f"Optimal params: {optimal_params}")
print(f"Optimal Sharpe: {results_df.iloc[0]['sharpe_ratio']:.2f}")
```

### Example 3: Ensemble of Multiple Strategies
```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    SectorRotationStrategy
)

# Run multiple strategies together
strategies = [
    MomentumStrategy(lookback=20, threshold=0.10),
    MeanReversionStrategy(lookback=20, z_threshold=2.0),
    SectorRotationStrategy(lookback=60)
]

engine = BacktestEngine()
results = engine.run(
    strategies=strategies,  # All 3 running together
    prices_df=prices_df,
    technical_df=technical_df,
    holdings_df=holdings_df
)

# Signals from all strategies combined
print(f"Total trades: {len(results['trades'])}")
```

---

## Running Examples

```bash
# Single strategy backtest
python examples/examples_backtesting.py 1

# Multiple strategies
python examples/examples_backtesting.py 2

# Parameter optimization with Prefect
python examples/examples_backtesting.py 3

# Grid search with Dask
python examples/examples_backtesting.py 4

# Walk-forward validation
python examples/examples_backtesting.py 5

# Ensemble strategy
python examples/examples_backtesting.py 6

# Risk analysis
python examples/examples_backtesting.py 7
```

---

## Performance Optimization

### 1. Dask Cluster Setup
```bash
# Terminal 1: Start scheduler
dask-scheduler

# Terminal 2: Start workers
dask-worker tcp://127.0.0.1:8786 --nworkers 4 --nthreads 2

# Terminal 3: Start your application
python your_backtest.py
```

### 2. Prefect with Dask
The flows automatically use Dask if available, fallback to local execution otherwise.

### 3. Data Caching
Load data once, reuse across multiple backtests:
```python
prices_df, technical_df, _ = loader.load_backtest_data(...)

# Reuse same data
for strategy_params in strategies:
    results = engine.run(..., prices_df=prices_df, ...)
```

### 4. Parallel Strategy Testing
```bash
# Run multiple strategies in parallel via Prefect
uv run python -m prefect.main backtest_multiple_strategies_flow \
    --symbols="AAPL,MSFT,GOOGL" \
    --strategies="momentum,mean_reversion"
```

---

## Extending the Framework

### Create Custom Strategy
```python
from src.backtesting.strategies import BaseStrategy, Signal, SignalAction
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self, lookback: int = 20):
        super().__init__("my_strategy", {"lookback": lookback})
    
    def generate_signals(
        self, prices_df, technical_df, holdings_df, date
    ) -> list:
        signals = []
        
        for _, holding in holdings_df.iterrows():
            symbol = holding["sym"]
            
            # Your signal logic here
            sym_prices = prices_df[
                (prices_df["symbol"] == symbol) & 
                (prices_df.index <= date)
            ].sort_index()
            
            if len(sym_prices) >= self.parameters["lookback"]:
                # Generate signal
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=date,
                    action=SignalAction.BUY,
                    signal_type="my_signal",
                    strength=0.8,
                    target_position_pct=1.0,
                    reason="My strategy logic",
                    parameters=self.parameters
                ))
        
        return signals

# Use it
strategy = MyStrategy(lookback=15)
results = engine.run(strategies=[strategy], ...)
```

---

## Integration with Quick Wins Analytics

The backtesting framework validates your Quick Wins strategies:

```python
from src.backtesting.strategies import MomentumStrategy, MeanReversionStrategy
from src.quick_wins_flows import quick_wins_analytics_flow

# Backtest the momentum screening from Quick Wins
momentum_backtest = MomentumStrategy(lookback=20, threshold=0.10)

results = engine.run(
    strategies=[momentum_backtest],
    prices_df=prices_df,
    technical_df=technical_df,
    holdings_df=holdings_df
)

# Compare backtest results with live Quick Wins signals
print(f"Momentum Backtest Sharpe: {results['metrics']['sharpe_ratio']:.2f}")
```

---

## Troubleshooting

**Q: "No data in date range"**
- Ensure symbols have price data for the entire date range
- Check ParquetDB has data: `loader.load_backtest_data(...)`

**Q: Dask not connecting**
- Start Dask scheduler: `dask-scheduler`
- Start workers: `dask-worker tcp://127.0.0.1:8786`
- Or run locally (automatic fallback)

**Q: Backtests too slow**
- Use Dask for parameter optimization
- Run Prefect flows (parallel by default)
- Cache data across multiple backtests

**Q: NaN or invalid prices**
- Check data with `loader.validate_data(...)`
- Handle gaps with interpolation or skip period

---

## File Structure

```
src/backtesting/
├── __init__.py                    # Package exports
├── strategies.py                  # Strategy base class + implementations
├── engine.py                      # Core backtesting engine
├── data_loader.py                 # ParquetDB data loading
├── analyzer.py                    # Results analysis & reporting
├── metrics.py                     # Performance metrics calculation
├── backtesting_flows.py          # Prefect flows (single/multi-strategy)
└── dask_backtesting_flows.py     # Dask-integrated flows (optimization)

examples/
└── examples_backtesting.py        # 7 complete usage examples

tests/
└── test_backtesting.py            # Comprehensive unit tests

docs/
├── BACKTESTING_ENGINE_ARCHITECTURE.md  # Design doc
└── BACKTESTING_FRAMEWORK_GUIDE.md      # This file
```

---

## Next Steps

1. **Run Examples**: Test each example to understand the framework
2. **Backtest Quick Wins**: Validate momentum and mean reversion strategies
3. **Optimize Parameters**: Use Dask grid search to find best parameters
4. **Validate Robustness**: Run walk-forward tests on multiple time periods
5. **Create Custom Strategies**: Implement your own strategy logic
6. **Monitor in Production**: Integrate with portfolio monitoring dashboard

---

## Support & Resources

- **Architecture**: See `BACKTESTING_ENGINE_ARCHITECTURE.md`
- **Examples**: Run `examples/examples_backtesting.py`
- **Metrics**: See `src/backtesting/metrics.py` for formula details
- **Dask Docs**: https://docs.dask.org/
- **Prefect Docs**: https://docs.prefect.io/
