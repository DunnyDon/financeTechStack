# Usage Guide

## Core Workflows

### 1. Portfolio Analytics & Email Report

Generate comprehensive portfolio analysis with email delivery:

```python
from src.analytics_flows import enhanced_analytics_flow

# Run full analytics
result = enhanced_analytics_flow(send_email_report=True)

print(f"Email sent: {result['email_sent']}")
print(f"P&L: {result['pnl_analysis']}")
print(f"Signals: {result['insights']}")
```

**Report includes:**
- Position-level P&L and portfolio performance
- Technical indicators (MACD, RSI, Bollinger Bands, Moving Averages)
- Fundamental metrics (P/E, ROE, ROA, dividend yields)
- Trading signals (buy/sell/hold)
- HTML formatted email delivery

### 2. Fetch Financial Data

Aggregate prices, SEC filings, fundamentals, and FX rates:

```python
from src.portfolio_flows import aggregate_financial_data_flow

# Run full aggregation workflow
state = aggregate_financial_data_flow(
    tickers=["AAPL", "MSFT", "GOOGL"],
    force_refresh=False
)

# Returns parquet file with aggregated data
print(f"Data saved to: {state['output_file']}")
```

**What it fetches:**
- Current prices (yfinance, Alpha Vantage, CoinGecko)
- SEC 10-K/10-Q filings via CIK lookup
- XBRL fundamental metrics
- FX rates for currency conversions
- All stored in Parquet format

### 3. Portfolio Analysis

Calculate technical indicators and P&L metrics:

```python
from src.portfolio_flows import portfolio_analysis_flow

# Analyze holdings
result = portfolio_analysis_flow(
    parquet_file="db/portfolio_data.parquet"
)

print(f"P&L: {result['pnl_summary']}")
print(f"Metrics: {result['portfolio_metrics']}")
print(f"Signals: {result['technical_signals']}")
```

## Component-Level Usage

### Load Holdings

```python
from src.portfolio_holdings import Holdings

holdings = Holdings("holdings.csv")
print(holdings.all_holdings)  # All positions
print(holdings.by_broker)      # Grouped by broker
print(holdings.by_currency)    # Grouped by currency
```

### Fetch Prices

```python
from src.portfolio_prices import PriceFetcher

fetcher = PriceFetcher()

# Single ticker
price = fetcher.fetch_price("AAPL")
print(f"AAPL: ${price}")

# Multiple tickers
prices = fetcher.fetch_prices(["AAPL", "MSFT", "GOOGL"])
```

### Technical Analysis

```python
from src.portfolio_technical import TechnicalAnalyzer
import pandas as pd

analyzer = TechnicalAnalyzer()

# Load price data
prices = pd.read_csv("price_history.csv", index_col="date", parse_dates=True)

# Calculate indicators
signals = analyzer.calculate_all_indicators(prices)
print(signals[["RSI", "MACD", "BB_Signal"]])
```

### Fundamental Analysis

```python
from src.portfolio_fundamentals import FundamentalAnalyzer

analyzer = FundamentalAnalyzer()

# Get fundamentals for ticker
fundamentals = analyzer.get_fundamentals("AAPL")
print(f"P/E: {fundamentals['pe_ratio']}")
print(f"ROE: {fundamentals['roe']}")
print(f"Dividend: {fundamentals['dividend_yield']}")
```

### SEC/XBRL Data

```python
from src.xbrl import fetch_xbrl_filings

# Fetch latest 10-K for Apple
data = fetch_xbrl_filings(
    ticker="AAPL",
    filing_types=["10-K"],
    limit=1
)

for item in data:
    print(f"Form: {item['form_type']}")
    print(f"Filed: {item['filing_date']}")
    print(f"Metrics: {item['fundamentals']}")
```

## Scheduled Execution

### Run Daily

```bash
# Create cron job for daily 4 PM portfolio analysis
0 16 * * * cd /path/to/TechStack && uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"
```

### Monitor with Prefect

Start Prefect UI to monitor workflow executions:

```bash
uv run prefect server start
# Visit http://localhost:4200 to view flows
```

## Caching & Performance

Data is cached to avoid redundant API calls:

```python
from src.cache import Cache

cache = Cache()

# Check cache before API call
if price := cache.get("AAPL_price"):
    print(f"Cached: ${price}")
else:
    # Fetch and cache
    price = fetcher.fetch_price("AAPL")
    cache.set("AAPL_price", price, ttl=3600)
```

## Error Handling

All workflows include automatic retry logic (3 attempts):

```python
from src.portfolio_flows import fetch_pricing_data_task

# Will retry up to 3 times on failure
try:
    result = fetch_pricing_data_task("AAPL")
except Exception as e:
    print(f"Failed after retries: {e}")
```

## Performance Tips

1. **Use caching** - Enabled by default, respects TTLs
2. **Batch requests** - Pass multiple tickers at once
3. **Limit API calls** - Use `force_refresh=False` to use cached data
4. **Parallel execution** - Prefect handles task parallelization automatically
5. **Compress storage** - Parquet with Snappy compression is used by default
