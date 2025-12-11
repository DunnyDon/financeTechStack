# Enhanced Backtesting Guide

## Overview

The Enhanced Backtesting Engine provides production-grade backtesting capabilities with:
- **Technical Indicator Support**: RSI, MACD, Bollinger Bands
- **Parameter Optimization**: Grid search for finding optimal entry/exit thresholds
- **Monte Carlo Simulation**: Risk assessment with 10,000+ iterations
- **Drawdown Analysis**: Maximum drawdown, recovery time, underwater plots
- **Performance Metrics**: Sharpe ratio, Sortino ratio, Calmar ratio, win rate, profit factor

## Quick Start

```python
from src.backtesting_engine import EnhancedBacktestingEngine
import pandas as pd

# Initialize engine
engine = EnhancedBacktestingEngine(min_capital=10000.0)

# Load OHLCV data
prices_df = pd.read_csv('prices.csv', index_col=0, parse_dates=True)

# Run backtest with RSI strategy
result = engine.backtest_strategy(
    symbol='AAPL',
    prices_df=prices_df,
    signal_type='rsi',
    entry_threshold=30,
    exit_threshold=70,
    stop_loss=0.05,
    take_profit=0.10
)

# Access results
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
print(f"Max Drawdown: {result.drawdowns['max_drawdown']:.2%}")
```

## Signal Types

### RSI (Relative Strength Index)
- **Entry Threshold**: When RSI falls below this value (e.g., 30 = oversold)
- **Exit Threshold**: When RSI rises above this value (e.g., 70 = overbought)
- **Typical Range**: 20-40 for entry, 60-80 for exit

### MACD (Moving Average Convergence Divergence)
- **Entry**: When histogram becomes positive
- **Exit**: When histogram becomes negative
- **Advantage**: Captures trend changes more smoothly

### Bollinger Bands
- **Entry**: When price closes below lower band
- **Exit**: When price closes above upper band
- **Advantage**: Mean reversion strategy

## Parameter Optimization

Find optimal parameters using grid search:

```python
result = engine.optimize_parameters(
    symbol='AAPL',
    prices_df=prices_df,
    signal_type='rsi',
    param_ranges={
        'entry_threshold': [20, 25, 30, 35],
        'exit_threshold': [60, 65, 70, 75]
    }
)

print(f"Best Sharpe: {result['best_sharpe']:.2f}")
print(f"Best Parameters: {result['best_params']}")
```

## Monte Carlo Simulation

Assess strategy robustness with Monte Carlo:

```python
returns = result.returns
mc_result = engine.monte_carlo_simulation(
    returns=returns,
    num_simulations=1000,
    periods=252  # 1 year of trading
)

print(f"5th Percentile: {mc_result['percentile_5']:.2f}")
print(f"95th Percentile: {mc_result['percentile_95']:.2f}")
print(f"95% Confidence Interval: {mc_result['confidence_interval_95']}")
```

## Performance Metrics

| Metric | Description | Interpretation |
|--------|-------------|-----------------|
| Sharpe Ratio | Return per unit of risk | Higher is better (>1 is good) |
| Sortino Ratio | Return per downside risk | Higher is better (>1 is good) |
| Calmar Ratio | Return / Max Drawdown | Higher is better |
| Win Rate | % of profitable trades | Target >50% |
| Profit Factor | Gains / Losses | Target >2.0 |
| Max Drawdown | Largest peak-to-trough decline | Lower is better |

## Risk Management

### Stop Loss & Take Profit
```python
result = engine.backtest_strategy(
    symbol='AAPL',
    prices_df=prices_df,
    stop_loss=0.05,      # Exit if down 5%
    take_profit=0.15     # Exit if up 15%
)
```

### Drawdown Analysis
```python
drawdowns = result.drawdowns
print(f"Max DD: {drawdowns['max_drawdown']:.2%}")
print(f"Recovery Time: {drawdowns['recovery_time']}")
```

## Data Requirements

- **Columns**: Open, High, Low, Close, Volume
- **Index**: DatetimeIndex (daily frequency recommended)
- **Minimum Rows**: 100+ for reliable indicators
- **Format**: pandas DataFrame

## Output Files

Results are saved to `db/backtesting/`:
- `trades_*.parquet` - Individual trade records
- `metrics_*.parquet` - Performance metrics summary

## Performance Considerations

- Parameter optimization tests multiple combinations (can be slow)
- Monte Carlo with 1000+ simulations is CPU-intensive
- Use Dask for portfolio-level backtests across many symbols
- Typical backtest on 252 daily candles: <1 second

## Common Issues

**Low Sharpe Ratio**: Try different signal type or adjust thresholds
**Max Drawdown > 20%**: Reduce position size or tighten stop loss
**Win Rate < 40%**: Signal may be contrarian; verify profitability
**Recovery Time > 1 Year**: Consider more conservative risk management
