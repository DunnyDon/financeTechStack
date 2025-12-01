# Portfolio Security & Holdings Analysis Engine

Complete portfolio analysis engine for technical analysis, fundamental analysis, and P&L tracking.

## Features

### Holdings Management
- ✅ Load and parse portfolio from CSV
- ✅ Filter by broker, asset type, exchange
- ✅ Portfolio summaries and statistics
- ✅ Multi-currency support (USD, EUR, AUD, etc.)

### Price Fetching
- ✅ Real-time quotes from yfinance (stocks, ETFs, commodities)
- ✅ Alpha Vantage integration for additional sources
- ✅ Cryptocurrency prices from CoinGecko
- ✅ Caching to reduce API calls
- ✅ Multi-source fallback

### Technical Analysis
- ✅ **Bollinger Bands**: Volatility and overbought/oversold levels
- ✅ **RSI**: Relative Strength Index (momentum indicator)
- ✅ **MACD**: Moving Average Convergence Divergence
- ✅ **Moving Averages**: SMA and EMA (short/long term)
- ✅ **Volume Analysis**: OBV, volume MA, relative volume
- ✅ Automatic indicator calculation for all holdings

### Fundamental Analysis
- ✅ Integration with existing SEC/XBRL data
- ✅ Financial metrics extraction
- ✅ Financial ratio calculations:
  - Net Margin
  - Debt-to-Equity
  - Current Ratio
  - ROE (Return on Equity)
  - ROA (Return on Assets)

### Portfolio Analytics & P&L Tracking
- ✅ **Unrealized P&L** per position
- ✅ **Portfolio-level P&L** with percentages
- ✅ **P&L by asset type** (equities, funds, crypto, commodities)
- ✅ **P&L by broker**
- ✅ **Top/worst performers** ranking
- ✅ **Position weights** and allocation
- ✅ **Win rate** and profitability tracking

### Reporting
- ✅ HTML reports with interactive tables
- ✅ JSON export for further analysis
- ✅ Prefect orchestration with logging
- ✅ Automatic report generation with timestamps

## Quick Start

### Prerequisites

```bash
# Install additional dependencies
pip install yfinance  # For price fetching
# CoinGecko is free, no API key needed
# Alpha Vantage: Set ALPHA_VANTAGE_API_KEY env var
```

### Basic Usage

```python
from src.portfolio_main import generate_portfolio_report

# Generate full portfolio report
report = generate_portfolio_report("holdings.csv")
print(f"HTML Report: {report['html_report']}")
print(f"JSON Data: {report['json_file']}")
```

### Load and Analyze Holdings

```python
from src.portfolio_holdings import Holdings

# Load holdings
holdings = Holdings("holdings.csv")

# Get summary
summary = holdings.get_summary()
print(f"Total holdings: {summary['total_holdings']}")
print(f"Cost basis: €{summary['total_cost_basis']:.2f}")

# Get by asset type
equities = holdings.get_equities()
funds = holdings.get_funds()
crypto = holdings.get_crypto()
```

### Fetch Current Prices

```python
from src.portfolio_prices import PriceFetcher

fetcher = PriceFetcher()

# Fetch single price
price = fetcher.fetch_price("AAPL", asset_type="eq")
print(f"AAPL: €{price['price']:.2f}")

# Fetch historical data
historical = fetcher.fetch_historical("AAPL", period="1y")
print(f"Retrieved {len(historical)} days of data")

# Crypto pricing
btc = fetcher.fetch_crypto_price("Bitcoin")
print(f"Bitcoin: ${btc['price_usd']:.2f}")
```

### Technical Analysis

```python
from src.portfolio_technical import TechnicalAnalyzer
from src.portfolio_prices import PriceFetcher
import pandas as pd

fetcher = PriceFetcher()
historical = fetcher.fetch_historical("AAPL", period="1y")

analyzer = TechnicalAnalyzer()

# Bollinger Bands
bb = analyzer.bollinger_bands(historical["Close"])
print(f"BB Width: {bb['bb_width'].iloc[-1]:.2f}")
print(f"BB Position: {bb['bb_pct'].iloc[-1]:.2%}")  # 0-1, where 1=upper band

# RSI
rsi_values = analyzer.rsi(historical["Close"])
print(f"RSI: {rsi_values.iloc[-1]:.1f}")  # 0-100

# MACD
macd = analyzer.macd(historical["Close"])
print(f"MACD: {macd['macd'].iloc[-1]:.4f}")
print(f"Signal: {macd['signal'].iloc[-1]:.4f}")
print(f"Histogram: {macd['histogram'].iloc[-1]:.4f}")

# All indicators at once
indicators = analyzer.calculate_all(historical)
print(indicators[["Close", "rsi", "bb_upper", "bb_lower", "macd"]].tail())
```

### Portfolio Analytics & P&L

```python
from src.portfolio_analytics import PortfolioAnalytics
from src.portfolio_holdings import Holdings
from src.portfolio_prices import fetch_multiple_prices

# Load holdings
holdings = Holdings("holdings.csv")
holdings_df = holdings.all_holdings

# Get prices
symbols, asset_types = holdings_df["sym"].unique(), dict(zip(holdings_df["sym"], holdings_df["asset"]))
prices = fetch_multiple_prices(symbols, asset_types)

# Analytics
analytics = PortfolioAnalytics(holdings_df, prices)

# Overall portfolio summary
summary = analytics.portfolio_summary()
print(f"Total Value: €{summary['total_current_value']:.2f}")
print(f"Total Cost: €{summary['total_cost_basis']:.2f}")
print(f"P&L: €{summary['total_unrealized_pnl']:.2f} ({summary['total_pnl_percent']:.2f}%)")
print(f"Win Rate: {summary['win_rate']:.1f}%")

# By asset type
by_type = analytics.pnl_by_asset_type()
for asset_type, data in by_type.items():
    print(f"{asset_type}: €{data['current_value']:.2f} ({data['pnl_percent']:.2f}%)")

# By broker
by_broker = analytics.pnl_by_broker()
for broker, data in by_broker.items():
    print(f"{broker}: €{data['current_value']:.2f} ({data['pnl_percent']:.2f}%)")

# Top/worst performers
top = analytics.top_performers(5)
print("\nTop 5 Performers:")
print(top[["sym", "unrealized_pnl", "pnl_percent"]])

worst = analytics.worst_performers(5)
print("\nWorst 5 Performers:")
print(worst[["sym", "unrealized_pnl", "pnl_percent"]])

# Position weights
weights = analytics.position_weights()
print("\nTop Position Weights:")
print(weights.head(10))

# Unrealized P&L detail
pnl_detail = analytics.calculate_unrealized_pnl()
print(pnl_detail[["sym", "qty", "bep", "current_price", "unrealized_pnl", "pnl_percent"]])
```

### Fundamental Analysis

```python
from src.portfolio_fundamentals import FundamentalAnalyzer
from src.portfolio_holdings import Holdings

holdings = Holdings("holdings.csv")

analyzer = FundamentalAnalyzer(holdings.all_holdings)

# Get fundamentals for specific ticker
fundamentals = analyzer.get_ticker_fundamentals("AAPL")
if fundamentals:
    print(f"Revenue: {fundamentals.get('revenue')}")
    print(f"Net Income: {fundamentals.get('net_income')}")

# Calculate ratios
ratios = analyzer.calculate_ratios(fundamentals)
print(f"Net Margin: {ratios.get('net_margin'):.2f}%")
print(f"ROE: {ratios.get('roe'):.2f}%")
print(f"Debt/Equity: {ratios.get('debt_to_equity'):.2f}")

# Analyze entire portfolio
fundamentals_df = analyzer.analyze_portfolio_fundamentals()
print(f"Retrieved fundamentals for {len(fundamentals_df)} equities")
print(fundamentals_df[["symbol", "revenue", "net_margin", "roe", "debt_to_equity"]])
```

### Generate Reports

```python
from src.portfolio_main import generate_portfolio_report

# Generate full report
report = generate_portfolio_report("holdings.csv")

print(f"HTML Report: {report['html_report']}")
print(f"JSON Data: {report['json_file']}")

# Summary
summary = report['summary']
print(f"\nPortfolio Summary:")
print(f"Total Value: €{summary['total_current_value']:.2f}")
print(f"P&L: €{summary['total_unrealized_pnl']:.2f} ({summary['total_pnl_percent']:.2f}%)")
```

## Using with Prefect

All major operations are Prefect tasks that can be orchestrated:

```bash
# Start Prefect server
prefect server start

# Run portfolio analysis flow
prefect flow-run create analyze_portfolio -p holdings_file=holdings.csv

# View in Prefect UI
# Open http://localhost:4200
```

## Holdings CSV Format

Your `holdings.csv` should have these columns:

| Column | Description | Example |
|--------|---|---|
| brokerName | Broker name | DEGIRO, REVOLUT, Kraken |
| brokerID | Broker ID | DEG, REVOLUT |
| account | Account ID | SKTRADE, REVO001REB001 |
| sym | Symbol/Ticker | AAPL, MSFT, GOOGL |
| secName | Security name | Apple Inc, Microsoft Corp |
| qty | Quantity held | 10.5, 100, 0.09148 |
| bep | Break-even price | 145.50, 200.00, 31130.41 |
| ccy | Currency | usd, eur, aud |
| asset | Asset type | eq (equity), fund, crypto, commodity |
| exchange | Exchange | nyse, nasdaq, lse, asx, paris |

## Technical Indicators Explained

### Bollinger Bands
- **Upper/Lower Bands**: Standard deviation ±2 from 20-day MA
- **BB Width**: Distance between bands (volatility measure)
- **BB %**: Position between bands (0=lower, 1=upper) - overbought/oversold
- **Interpretation**:
  - Price at upper band = potential overbought
  - Price at lower band = potential oversold
  - Widening bands = increasing volatility
  - Narrowing bands = decreasing volatility

### RSI (Relative Strength Index)
- **Range**: 0-100
- **Interpretation**:
  - Below 30 = oversold (potential buy)
  - Above 70 = overbought (potential sell)
  - 30-70 = neutral
- **Use**: Identify potential reversals

### MACD (Moving Average Convergence Divergence)
- **MACD Line**: 12-day EMA - 26-day EMA
- **Signal Line**: 9-day EMA of MACD
- **Histogram**: MACD - Signal (momentum)
- **Interpretation**:
  - MACD crosses above signal = bullish
  - MACD crosses below signal = bearish
  - Histogram growing = strengthening trend

### Moving Averages
- **SMA (Simple)**: Average of last N prices
- **EMA (Exponential)**: Recent prices weighted more
- **Use**: Identify trend direction
  - Price above MA = uptrend
  - Price below MA = downtrend
  - Short MA above long MA = bullish
  - Short MA below long MA = bearish

## Performance Metrics

### P&L Metrics
- **Unrealized P&L**: (Current Price - Break-even) × Quantity
- **P&L %**: (Unrealized P&L / Cost Basis) × 100
- **Return %**: ((Current Price - BEP) / BEP) × 100
- **Win Rate**: % of positions with positive P&L

### Financial Ratios
- **Net Margin**: Net Income / Revenue
- **Debt/Equity**: Total Debt / Shareholders' Equity
- **Current Ratio**: Current Assets / Current Liabilities
- **ROE**: Net Income / Shareholders' Equity
- **ROA**: Net Income / Total Assets

## Architecture

```
portfolio_holdings.py
    ↓ (loads)
holdings.csv
    ↓ (fetch prices)
portfolio_prices.py (yfinance, Alpha Vantage, CoinGecko)
    ↓ (analyze)
portfolio_technical.py (Bollinger Bands, RSI, MACD, MA, Volume)
portfolio_fundamentals.py (SEC/XBRL data, ratios)
portfolio_analytics.py (P&L, metrics, allocation)
    ↓ (orchestrate)
portfolio_main.py (Prefect flows)
    ↓ (generate)
HTML Report + JSON Export
```

## API Sources

### yfinance
- **URL**: https://finance.yahoo.com
- **Coverage**: Stocks, ETFs, commodities, indices
- **Rate Limit**: No limit (uses Yahoo Finance)
- **Cost**: Free

### Alpha Vantage
- **URL**: https://www.alphavantage.co
- **Coverage**: Stocks, forex, crypto
- **Rate Limit**: Free: 5 calls/min, Premium: Higher
- **Cost**: Free tier available, paid plans available
- **Setup**: Set `ALPHA_VANTAGE_API_KEY` env var

### CoinGecko
- **URL**: https://www.coingecko.com/en/api
- **Coverage**: 10,000+ cryptocurrencies
- **Rate Limit**: 10-50 calls/min (free)
- **Cost**: Free (commercial API available)

## Examples

### Compare technical indicators across portfolio

```python
from src.portfolio_main import analyze_portfolio
import pandas as pd

# Get portfolio data
portfolio = analyze_portfolio("holdings.csv")

# Create technical analysis for top 10 holdings by weight
holdings = portfolio['holdings']
top_holdings = sorted(holdings, key=lambda x: x.get('current_value', 0), reverse=True)[:10]

for holding in top_holdings:
    symbol = holding['sym']
    # [Fetch and analyze technical indicators]
```

### Track P&L over time

```python
import json
from datetime import datetime

# Save current portfolio state
report = generate_portfolio_report("holdings.csv")

# Load and compare with historical data
with open(report['json_file'], 'r') as f:
    current = json.load(f)

# Compare with previous reports for trend analysis
# [Build historical P&L tracking]
```

### Generate watchlist from technical signals

```python
# Find positions where:
# - RSI < 30 (oversold)
# - Price touching lower Bollinger Band
# - MACD histogram positive (momentum)
# - Volume above 20-day MA

watchlist = []
for position in positions:
    if indicators['rsi'] < 30 and indicators['bb_pct'] < 0.2 and indicators['histogram'] > 0:
        watchlist.append(position)
```

## Testing

```bash
# Run portfolio analysis tests
python -m pytest tests/test_portfolio.py -v

# Profile performance
python -m cProfile -s cumtime portfolio_main.py
```

## Troubleshooting

### No prices fetched
- Check internet connection
- yfinance may be down (try manually: `yfinance.download('AAPL')`)
- Alpha Vantage may be rate limited (free tier is 5 calls/min)
- Set correct API key: `export ALPHA_VANTAGE_API_KEY=your_key`

### Cryptocurrency prices not fetching
- Check symbol mapping in `portfolio_prices.py`
- CoinGecko may have API rate limiting (10-50 calls/min free)
- Common symbols: Bitcoin, Ethereum, Ripple, etc.

### SEC/XBRL data not available
- Not all companies have SEC filings
- Ensure ticker is correct US-listed company
- Data lags filing dates (may be 40+ days behind)

### Performance issues with large portfolios
- Cache prices to avoid repeated API calls (automatic)
- Use Prefect parallel task execution
- Consider batch processing in docker-compose

## Next Steps

- [ ] Add real-time price streaming
- [ ] Implement portfolio rebalancing suggestions
- [ ] Add tax loss harvesting analysis
- [ ] Create correlation matrix of holdings
- [ ] Add Monte Carlo simulation for returns
- [ ] Integrate with broker APIs for automatic updates
- [ ] Create mobile-friendly dashboard
- [ ] Add alerts for technical signal triggers
- [ ] Implement dividend tracking
- [ ] Add sector/market comparison benchmarks

## License

MIT
