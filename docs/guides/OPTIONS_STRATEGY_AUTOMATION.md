# Options Strategy Automation Guide

## Overview

Automated generation and analysis of multi-leg options strategies with Greeks-based recommendations and risk management. Includes Iron Condors, Strangles, Straddles, Covered Calls, and hedge recommendations.

## Features

### 1. **Iron Condor Strategy**
- **Structure:** Sell OTM put spread + Sell OTM call spread
- **Best For:** High IV environments (percentile >70) with neutral market view
- **Profit:** Defined (max credit received)
- **Loss:** Defined (width of spreads minus credit)
- **Greeks:** Delta-neutral, positive theta decay, short vega

### 2. **Strangle Strategy**
- **Long Strangle:** Buy OTM call + OTM put (volatility expansion play)
- **Short Strangle:** Sell OTM call + OTM put (mean reversion play)
- **Best For:** Anticipating large moves (long) or stable environment (short)
- **Asymmetric Payoff:** Unlimited upside/downside for long strangle

### 3. **Straddle Strategy**
- **Long Straddle:** Buy ATM call + ATM put (pure vol play)
- **Short Straddle:** Sell ATM call + ATM put (vol contraction play)
- **Best For:** Around earnings or volatility inflection points
- **Greeks:** High gamma, high vega exposure

### 4. **Covered Call Strategy**
- **Structure:** Long stock + Short call
- **Best For:** Income generation, slightly bullish outlook
- **Downside Protection:** Cost reduced by call premium
- **Max Profit:** Strike price + call premium

### 5. **Greeks-Based Hedging**
- **Delta Hedges:** Put spreads/call spreads to neutralize directional exposure
- **Vega Hedges:** Short strangles to reduce vega exposure or long strangles for vega protection
- **Portfolio-Level:** Recommendations based on aggregate Greeks

## Quick Start

```python
from src.options_strategy_automation import OptionsStrategyAutomation

# Initialize automator
automator = OptionsStrategyAutomation(risk_tolerance='moderate')

# Generate Iron Condor for SPY
strategy = automator.generate_iron_condor(
    underlying='SPY',
    current_price=450.0,
    volatility_percentile=75,
    days_to_expiration=45,
    put_strike_pct=0.02,  # 2% OTM
    call_strike_pct=0.02
)

# View strategy details
print(f"Net Credit: ${abs(strategy.net_debit_credit):.2f}")
print(f"Greeks: {strategy.aggregate_greeks}")

# Analyze P&L across price range
import numpy as np
price_range = np.linspace(430, 470, 50)
analysis = automator.analyze_strategy_performance(strategy, price_range)

# Save to Parquet
filepath = automator.save_to_parquet('db/options_strategies')
```

## Strategy Selection Guide

### By Market Condition

| Volatility | Outlook | Recommended Strategy |
|-----------|---------|---------------------|
| High (>70%) | Neutral | Iron Condor |
| High (>70%) | Bullish | Covered Call |
| High (>70%) | Bearish | Short Call Spread |
| Normal (30-70%) | Bullish | Call Spread |
| Normal (30-70%) | Bearish | Put Spread |
| Normal (30-70%) | Neutral | Long Strangle |
| Low (<30%) | Bullish | Long Call Spread |
| Low (<30%) | Bearish | Long Put Spread |
| Low (<30%) | Neutral | Long Straddle |

### By Risk Profile

**Conservative:** Covered calls, put spreads, credit spreads
**Moderate:** Iron condors, strangles, balanced hedges
**Aggressive:** Long straddles, naked puts, debit spreads

## Greeks Reference

### Delta (Δ)
- **Meaning:** Change in option price per $1 stock move
- **Range:** 0 to 1 for calls, -1 to 0 for puts
- **Use:** Measure directional exposure

### Gamma (Γ)
- **Meaning:** Change in delta per $1 stock move
- **Interpretation:** Acceleration of P&L changes
- **High Gamma:** Requires frequent rebalancing (ATM options)

### Theta (Θ)
- **Meaning:** Daily P&L decay from time passage
- **Long Options:** Negative theta (lose money daily)
- **Short Options:** Positive theta (gain money daily)

### Vega (ν)
- **Meaning:** Change in option price per 1% change in IV
- **Long Vol:** Positive vega (profit if IV increases)
- **Short Vol:** Negative vega (profit if IV decreases)

## Position Sizing

```python
# Size based on maximum acceptable loss
portfolio_value = 100000
max_loss_pct = 2.0  # Risk 2% of portfolio
max_loss = portfolio_value * (max_loss_pct / 100)

strategy = automator.generate_iron_condor(
    underlying='SPY',
    current_price=450.0,
    volatility_percentile=75
)

# Calculate contracts: max_loss / spread_width
spread_width = 5.0
contracts = int(max_loss / (spread_width * 100))

print(f"Position size: {contracts} contracts")
print(f"Max loss: ${contracts * spread_width * 100:.2f}")
```

## Hedge Recommendations

### For Long Portfolio (Positive Delta)
- **Put Spread:** Buy protective puts, sell lower puts to reduce cost
- **Collar:** Own stock, buy puts, sell calls
- **Dynamic:** Adjust as delta changes

### For Short Portfolio (Negative Delta)
- **Call Spread:** Buy protective calls, sell higher calls
- **Reverse Collar:** Short stock, sell calls, buy puts

### For Volatility Exposure
- **Long Vol:** Buy strangles/straddles
- **Short Vol:** Sell iron condors, covered calls
- **Variance:** Monitor and adjust based on realized vs IV

## Example Strategies

### 1. Income Strategy on Tech Stocks
```python
# High IV tech = covered call opportunity
strategy = automator.generate_covered_call(
    underlying='NVDA',
    current_price=875.0,
    shares_owned=100,
    call_strike_pct=0.05,  # Sell 5% OTM
    days_to_expiration=30
)
```

### 2. Earnings Volatility Play
```python
# Before earnings: expect large move
strategy = automator.generate_straddle(
    underlying='META',
    current_price=345.0,
    volatility_percentile=40,  # IV likely to expand
    days_to_expiration=14,
    direction='long'
)
```

### 3. Mean Reversion on Oversold Stock
```python
# After large drop: expect bounce
strategy = automator.generate_strangle(
    underlying='TSLA',
    current_price=245.0,
    volatility_percentile=85,  # High IV = short strangle credit
    days_to_expiration=45,
    direction='short'  # Sell premium
)
```

### 4. Portfolio Hedge
```python
# Protect long portfolio without selling holdings
recommendations = automator.generate_hedge_recommendations(
    portfolio_delta=500.0,  # 500 shares delta exposure
    portfolio_vega=150.0,   # Positive vega (long vol exposure)
    portfolio_value=100000,
    max_hedge_cost_pct=2.0
)

for hedge in recommendations['delta_hedges']:
    print(f"Strategy: {hedge['type']}")
    print(f"Cost: ${hedge['estimated_cost']:.2f}")
```

## Performance Analysis

### P&L Analysis at Expiration
```python
import numpy as np

# Analyze across price range
price_range = np.linspace(420, 480, 100)
analysis = automator.analyze_strategy_performance(strategy, price_range)

# Find breakevens
breakeven_prices = analysis[analysis['P&L'] == 0]['Price'].values
max_profit_price = analysis.loc[analysis['P&L'].idxmax(), 'Price']

print(f"Max profit at: ${max_profit_price:.2f}")
print(f"Breakeven points: {breakeven_prices}")
```

### Greeks Monitoring
```python
# Monitor Greeks over time
greeks = strategy.aggregate_greeks
print(f"Portfolio Delta: {greeks['delta']:.2f}")
print(f"Portfolio Gamma: {greeks['gamma']:.4f}")
print(f"Portfolio Theta: {greeks['theta']:.4f}")
print(f"Portfolio Vega: {greeks['vega']:.4f}")

# Check if portfolio is balanced
assert abs(greeks['delta']) < 100, "Delta too high!"
assert greeks['theta'] > 0, "Negative theta exposure!"
```

## Risk Management

### 1. **Position Limits**
- Max loss per trade: 2% of portfolio
- Max number of positions: 20
- Max sector concentration: 25%

### 2. **Greeks Limits**
- Max delta: ±200 (portfolio level)
- Max vega: ±500
- Max gamma: ±50
- Max theta: ±20 (should be positive for income strategies)

### 3. **Time Decay Management**
- Close spreads at 21 DTE (days to expiration)
- Roll to next month when theta decay slows
- Exit losing trades at 50% max loss

### 4. **Volatility Management**
- Don't sell premiums in low IV environments
- Don't buy options in high IV environments
- Use IV rank/percentile as entry guide

## Data Persistence

Strategies are automatically saved to Parquet:

```python
# Save strategies
filepath = automator.save_to_parquet('db/options_strategies')

# Load and analyze
import pandas as pd
df = pd.read_parquet(filepath)

# See all strategies
print(df[['Strategy', 'Underlying', 'Delta', 'Theta', 'Vega']])
```

## Advanced Features

### Custom Greeks Calculations
- Uses simplified Black-Scholes model
- Estimates intrinsic and time value separately
- Scales IV percentile for realistic option pricing

### Implied Volatility Integration
- Tracks IV percentile vs historical
- Recommends strategies based on IV levels
- Helps identify reversion opportunities

### Strategy Recommendation Engine
```python
# Get recommendation for market conditions
from src.options_strategy_automation import recommend_strategy_for_market_condition

strategy_name = recommend_strategy_for_market_condition(
    volatility_percentile=82,  # High IV
    market_direction='neutral',
    time_horizon_days=30
)

print(f"Recommended: {strategy_name}")  # Output: Iron Condor
```

## Common Patterns

### Pattern 1: Income Generation
```python
# Generate steady income on holdings
automator.generate_covered_call(
    underlying='MSFT',
    current_price=420.0,
    shares_owned=200,
    call_strike_pct=0.05,
    days_to_expiration=30
)
```

### Pattern 2: Directional Play with Limited Risk
```python
# Bull call spread: limited risk, lower cost
automator.generate_strangle(
    underlying='AAPL',
    current_price=185.0,
    volatility_percentile=35,  # Buy low IV
    direction='long'
)
```

### Pattern 3: Volatility Contraction
```python
# Short premium in high IV
automator.generate_iron_condor(
    underlying='SPY',
    current_price=450.0,
    volatility_percentile=82,  # High IV
    days_to_expiration=45
)
```

## Troubleshooting

### Issue: Strategy costs too much
- **Solution:** Increase spread width, reduce days to expiration, or change strike selection

### Issue: Delta too high after entry
- **Solution:** Sell further OTM options or use delta-neutral hedges

### Issue: Theta decay is negative
- **Solution:** You're long premium - consider selling premium instead

### Issue: Options are illiquid
- **Solution:** Increase strike distance from current price or use more liquid underlyings

## Integration with Portfolio

```python
# Get hedge recommendations for existing portfolio
portfolio_greeks = {
    'delta': 450,
    'vega': 200,
    'theta': 15
}

recommendations = automator.generate_hedge_recommendations(
    portfolio_delta=portfolio_greeks['delta'],
    portfolio_vega=portfolio_greeks['vega'],
    portfolio_value=200000
)

# Implement hedges
for recommendation in recommendations['delta_hedges']:
    print(f"Add: {recommendation['type']} - Cost: ${recommendation['estimated_cost']}")
```

## API Reference

### OptionsStrategyAutomation

**Methods:**
- `generate_iron_condor()` - Iron condor strategy
- `generate_strangle()` - Strangle strategy (long or short)
- `generate_covered_call()` - Covered call for income
- `generate_straddle()` - Straddle strategy (long or short)
- `generate_hedge_recommendations()` - Portfolio hedge suggestions
- `analyze_strategy_performance()` - P&L across price range
- `save_to_parquet()` - Persist strategies

### Utility Functions

- `recommend_strategy_for_market_condition()` - Get strategy based on conditions

## Testing

Comprehensive test coverage (50+ tests):

```bash
pytest tests/test_options_strategy_automation.py -v
```

Tests cover:
- Strategy generation and structure validation
- Greeks calculations and aggregation
- P&L analysis across prices
- Parquet persistence
- Edge cases and error handling

## See Also

- Technical Analysis Guide
- Risk Management Framework
- Portfolio Analytics Guide
