# Crypto Advanced Analytics

## Overview

Advanced analytics for cryptocurrency portfolio management:
- **On-Chain Metrics**: Active addresses, whale watch, exchange flows
- **Market Structure**: Liquidity analysis, orderbook depth, volume profile
- **Correlation Analysis**: Cross-asset correlation matrices
- **Volatility Analysis**: Term structure, regime detection, mean reversion signals
- **Portfolio Risk**: Value at Risk, Expected Shortfall, diversification metrics

## Quick Start

```python
from src.crypto_analytics import CryptoAdvancedAnalytics
import pandas as pd

# Initialize analytics engine
analytics = CryptoAdvancedAnalytics()

# Fetch on-chain metrics
metrics = analytics.fetch_on_chain_metrics('BTC', metric_type='whale_watch')
print(f"Large Transactions (24h): {metrics['metrics']['large_transactions_24h']}")
print(f"Top 10 Concentration: {metrics['metrics']['top_10_address_concentration']:.1%}")

# Analyze market structure
structure = analytics.analyze_market_structure('ETH', price=2500, volume_24h=15e9)
print(f"Liquidity Score: {structure['liquidity_score']:.0f}/100")
print(f"Market Strength: {structure['market_strength']}")

# Calculate portfolio risk
holdings = {'BTC': 1, 'ETH': 10, 'SOL': 100}
prices = {'BTC': 50000, 'ETH': 2500, 'SOL': 100}
correlation = analytics.analyze_correlation_matrix(
    ['BTC', 'ETH', 'SOL'],
    price_data={sym: pd.Series([prices[sym]]) for sym in holdings}
)

risk = analytics.calculate_crypto_portfolio_risk(holdings, prices, correlation)
print(f"Portfolio Value: ${risk['portfolio_value']:,.0f}")
print(f"Annual Volatility: {risk['annual_volatility']:.1%}")
print(f"Value at Risk (95%): ${risk['var_95']:,.0f}")
```

## On-Chain Metrics

### Active Addresses
Tracks blockchain activity and adoption:

```python
metrics = analytics.fetch_on_chain_metrics('BTC', 'active_addresses')

data = metrics['metrics']
print(f"Active 24h: {data['active_addresses_24h']:,}")
print(f"Active 7d: {data['active_addresses_7d']:,}")
print(f"New Addresses: {data['new_addresses_24h']:,}")
print(f"Exchange Netflow: {data['exchange_netflow']:.2f} BTC")
```

**Interpretation**:
- **Rising Active Addresses**: Increasing adoption (bullish)
- **Falling Addresses**: Declining interest (bearish)
- **Exchange Inflow**: Potential selling pressure (bearish)
- **Exchange Outflow**: Accumulation, less selling (bullish)

### Whale Watch
Monitors large holder activity:

```python
metrics = analytics.fetch_on_chain_metrics('ETH', 'whale_watch')

data = metrics['metrics']
print(f"Large Txns (24h): {data['large_transactions_24h']}")
print(f"Whale Concentration: {data['top_10_address_concentration']:.1%}")
print(f"Accumulation Pressure: {data['whale_accumulation_pressure']:+.2f}")
```

**Interpretation**:
- **Low Concentration**: Decentralized distribution (healthy)
- **High Concentration**: Centralized risk (risky)
- **Positive Accumulation**: Whales buying (potentially bullish)
- **Negative Accumulation**: Whales selling (potentially bearish)

### Transaction Volume
Network utilization metrics:

```python
metrics = analytics.fetch_on_chain_metrics('SOL', 'transaction_volume')

data = metrics['metrics']
print(f"Volume (24h): ${data['transaction_volume_24h']/1e9:.1f}B")
print(f"Transaction Count: {data['transaction_count_24h']:,}")
print(f"Avg Tx Value: ${data['average_transaction_value']:,.0f}")
print(f"Median Fee: ${data['median_transaction_fee']:.2f}")
```

## Market Structure Analysis

### Liquidity Assessment

```python
structure = analytics.analyze_market_structure(
    'BTC',
    price=50000,
    volume_24h=30e9
)

print(f"Liquidity Score: {structure['liquidity_score']:.0f}/100")
# 80-100: Excellent
# 60-80: Good
# 40-60: Fair
# <40: Poor

print(f"Bid-Ask Spread: {structure['bid_ask_spread']:.3%}")
print(f"Volume/MCap: {structure['volume_market_cap_ratio']:.2%}")
```

**Liquidity Indicators**:
- **Tight Spread**: Easy to trade without slippage
- **Deep Orderbook**: Can execute large orders
- **High Vol/MCap**: Healthy trading activity

### Orderbook Depth Analysis

```python
orderbook = structure['orderbook_depth']

print(f"Total Value: ${orderbook['total_value']/1e6:.1f}M")

for level, data in orderbook['by_level'].items():
    print(f"\n{level} from mid:")
    print(f"  Bid: {data['bid_volume']:,.0f}")
    print(f"  Ask: {data['ask_volume']:,.0f}")
    print(f"  Imbalance: {data['imbalance']:+.1%}")
```

**Imbalance Interpretation**:
- **Negative (More Bids)**: Potential upside (bullish)
- **Positive (More Asks)**: Potential downside (bearish)
- **Balanced**: Fair-value near midpoint

### Volume Profile

```python
profile = structure['volume_profile']

print(f"24h Volume: ${profile['total_volume_24h']/1e9:.2f}B")
print(f"Concentration: {profile['volume_concentration']:.1%}")
print(f"High Volume Nodes: {profile['high_volume_nodes']}")
```

## Correlation Analysis

### Asset Correlations

```python
# Multi-asset correlation
price_data = {
    'BTC': pd.Series([50000, 51000, 49000, 52000]),
    'ETH': pd.Series([2500, 2600, 2400, 2700]),
    'SOL': pd.Series([100, 105, 98, 108])
}

correlation = analytics.analyze_correlation_matrix(
    ['BTC', 'ETH', 'SOL'],
    price_data
)

print(correlation)
#        BTC   ETH   SOL
# BTC  1.00  0.95  0.78
# ETH  0.95  1.00  0.82
# SOL  0.78  0.82  1.00
```

**Interpretation**:
- **1.0**: Perfect positive correlation (move together)
- **0.0**: No correlation (independent)
- **-1.0**: Perfect negative correlation (opposite moves)

**Portfolio Implications**:
- High correlation (>0.8): Less diversification benefit
- Low correlation (<0.3): Better risk reduction
- Mixed: Balanced diversification

## Volatility Analysis

### Term Structure

```python
vol_data = {
    'vol_7d': 0.05,   # 5%
    'vol_30d': 0.08,  # 8%
    'vol_90d': 0.07   # 7%
}

vol_analysis = analytics.analyze_volatility_term_structure('BTC', vol_data)

print(f"7d Vol: {vol_analysis['volatility_7d']:.1%}")
print(f"30d Vol: {vol_analysis['volatility_30d']:.1%}")
print(f"Trend: {vol_analysis['vol_trend']}")
print(f"Regime: {vol_analysis['vol_regime']}")
print(f"Mean Reversion Signal: {vol_analysis['vol_mean_reversion_signal']}")
```

**Volatility Regimes**:
- **High** (>8%): Elevated risk, potential opportunities
- **Normal** (3-8%): Typical trading conditions
- **Low** (<3%): Low activity, potential breakout

**Mean Reversion Signals**:
- **Elevated Vol**: Consider reducing exposure (sell high vol)
- **Depressed Vol**: Consider increasing exposure (buy low vol)
- **Normal**: Maintain current positions

### Volatility Trend

```python
# Increasing volatility
vol_data = {'vol_7d': 0.10, 'vol_30d': 0.08, 'vol_90d': 0.06}
analysis = analytics.analyze_volatility_term_structure('ETH', vol_data)
print(analysis['vol_trend'])  # "increasing" - volatility expanding
print(analysis['vol_slope'])  # +0.33 - strong increase

# Decreasing volatility  
vol_data = {'vol_7d': 0.04, 'vol_30d': 0.06, 'vol_90d': 0.08}
analysis = analytics.analyze_volatility_term_structure('SOL', vol_data)
print(analysis['vol_trend'])  # "decreasing" - volatility contracting
```

## Portfolio Risk Metrics

### Value at Risk (VaR)

```python
holdings = {'BTC': 1, 'ETH': 10}
prices = {'BTC': 50000, 'ETH': 2500}
correlation = pd.DataFrame(
    [[1.0, 0.8], [0.8, 1.0]],
    index=['BTC', 'ETH'],
    columns=['BTC', 'ETH']
)

risk = analytics.calculate_crypto_portfolio_risk(
    holdings,
    prices,
    correlation
)

print(f"Portfolio Value: ${risk['portfolio_value']:,.0f}")
print(f"Portfolio Volatility: {risk['portfolio_volatility']:.1%}")
print(f"Annual Volatility: {risk['annual_volatility']:.1%}")
print(f"VaR (95%): ${risk['var_95']:,.0f}")  # 5% chance of loss this large
print(f"VaR (99%): ${risk['var_99']:,.0f}")  # 1% chance of loss this large
```

**Interpretation**:
- **VaR 95%**: 5% chance of losing more than this on any given day
- **VaR 99%**: 1% chance of losing more than this on any given day
- Use 99% for conservative risk management

### Expected Shortfall (CVaR)

```python
cvar = risk['cvar_95']
print(f"Expected Shortfall (95%): ${cvar:,.0f}")
# Average loss if worst 5% scenarios occur
```

**When to Use**:
- More conservative than VaR
- Accounts for tail risk
- Better for risk-averse portfolios

### Concentration Risk

```python
print(f"Largest Position: {risk['largest_position']}")
print(f"Weight: {risk['concentration_risk']:.1%}")
print(f"Diversification Ratio: {risk['diversification_ratio']:.2f}")

# Diversification > 1.0 indicates benefit from diversification
# Higher = more diversified portfolio
```

## Practical Examples

### Example 1: Whale Monitoring

```python
# Track large holder activity for trading signals
whale_metrics = analytics.fetch_on_chain_metrics('BTC', 'whale_watch')

if whale_metrics['metrics']['whale_accumulation_pressure'] > 0.5:
    print("Whales accumulating - potential upside")
    # Consider increasing exposure
elif whale_metrics['metrics']['whale_accumulation_pressure'] < -0.5:
    print("Whales distributing - potential downside")
    # Consider reducing exposure
```

### Example 2: Liquidity-Based Entry

```python
# Enter positions with good liquidity
market_structure = analytics.analyze_market_structure('ETH', 2500, 15e9)

if market_structure['liquidity_score'] > 70:
    print("Good liquidity - favorable for entry")
    # Execute trade
else:
    print("Poor liquidity - wait or increase slippage limits")
```

### Example 3: Risk-Adjusted Position Sizing

```python
# Size positions based on portfolio volatility
portfolio_vol = risk['annual_volatility']
target_vol = 0.20  # 20% annual volatility target

# Reduce position if portfolio vol too high
if portfolio_vol > target_vol:
    reduction_factor = target_vol / portfolio_vol
    print(f"Reduce positions by {(1-reduction_factor)*100:.0f}%")
```

## Data Storage

Results saved to `db/crypto_analytics/`:
- `analysis_YYYYMMDD.parquet` - Complete analysis snapshot
- Includes on-chain metrics, market structure, risk metrics

```python
analytics.save_crypto_analysis(analysis_data)
```

## Limitations & Considerations

- On-chain data is simulated (use Glassnode API for production)
- Correlations are backward-looking (not predictive)
- VaR assumes normal distribution (crypto returns are fat-tailed)
- Volatility regimes can shift rapidly in crypto markets
- Whale addresses don't always indicate true market direction

## See Also

- [README](../../README.md) - Project overview
- [ARCHITECTURE_OVERVIEW](../architecture/ARCHITECTURE_OVERVIEW.md) - System design
- [QUICK_START](./QUICK_START.md) - 5-minute setup guide
