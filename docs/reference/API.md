# API Reference

## Workflows (Prefect Flows)

### `enhanced_analytics_flow(send_email_report: bool = False) → Dict`

Complete portfolio analysis with optional email delivery.

**Parameters:**
- `send_email_report` (bool): Send HTML email report to configured recipient

**Returns:**
- `email_sent` (bool): Whether email was successfully sent
- `pnl_analysis` (Dict): Position and portfolio P&L
- `technical_signals` (Dict): Technical indicator analysis
- `fundamental_metrics` (Dict): Fundamental analysis
- `insights` (Dict): Trading signals and recommendations
- `timestamp` (str): Analysis timestamp

**Example:**
```python
from src.analytics_flows import enhanced_analytics_flow

result = enhanced_analytics_flow(send_email_report=True)
print(result['insights'])  # Trading signals
```

---

### `aggregate_financial_data_flow(tickers: List[str], force_refresh: bool = False) → Dict`

Fetch and aggregate prices, SEC filings, fundamentals, FX rates.

**Parameters:**
- `tickers` (List[str]): Ticker symbols to fetch
- `force_refresh` (bool): Ignore cache, fetch fresh data

**Returns:**
- `output_file` (str): Path to Parquet file with aggregated data
- `row_count` (int): Number of records in output
- `errors` (List[str]): Any API errors encountered

**Example:**
```python
from src.portfolio_flows import aggregate_financial_data_flow

result = aggregate_financial_data_flow(
    tickers=["AAPL", "MSFT", "GOOGL"],
    force_refresh=False
)
print(f"Data saved: {result['output_file']}")
```

---

### `portfolio_analysis_flow(parquet_file: str) → Dict`

Analyze aggregated portfolio data with technical indicators and P&L.

**Parameters:**
- `parquet_file` (str): Path to Parquet file with portfolio data

**Returns:**
- `pnl_summary` (Dict): Portfolio P&L metrics
- `portfolio_metrics` (Dict): Returns, Sharpe ratio, max drawdown
- `technical_signals` (Dict): Buy/sell/hold signals per position
- `top_performers` (List): Best and worst performers

**Example:**
```python
from src.portfolio_flows import portfolio_analysis_flow

result = portfolio_analysis_flow("db/portfolio_2024.parquet")
print(result['pnl_summary'])
```

---

## Core Classes

### `Holdings`
Portfolio position management.

**Methods:**
- `all_holdings` → List[Dict]: All positions
- `by_broker` → Dict[str, List]: Grouped by broker
- `by_currency` → Dict[str, List]: Grouped by currency
- `get_total_value(prices: Dict) → float`: Total portfolio value
- `calculate_pnl(prices: Dict) → Dict`: P&L per position

**Example:**
```python
from src.portfolio_holdings import Holdings

h = Holdings("holdings.csv")
print(f"Total positions: {len(h.all_holdings)}")
```

---

### `PriceFetcher`
Fetch current prices from multiple sources.

**Methods:**
- `fetch_price(ticker: str) → float`: Latest price
- `fetch_prices(tickers: List[str]) → Dict[str, float]`: Batch fetch
- `fetch_historical(ticker: str, days: int = 365) → pd.DataFrame`: Price history

**Example:**
```python
from src.portfolio_prices import PriceFetcher

fetcher = PriceFetcher()
prices = fetcher.fetch_prices(["AAPL", "MSFT"])
print(prices)  # {"AAPL": 150.25, "MSFT": 310.50}
```

---

### `TechnicalAnalyzer`
Calculate technical indicators.

**Methods:**
- `calculate_rsi(prices: pd.Series, period: int = 14) → pd.Series`: Relative Strength Index
- `calculate_macd(prices: pd.Series) → Tuple[pd.Series, pd.Series, pd.Series]`: MACD, signal, histogram
- `calculate_bollinger_bands(prices: pd.Series, period: int = 20) → Tuple[pd.Series, pd.Series, pd.Series]`: Upper, middle, lower bands
- `calculate_all_indicators(prices: pd.Series) → pd.DataFrame`: All indicators

**Example:**
```python
from src.portfolio_technical import TechnicalAnalyzer
import pandas as pd

analyzer = TechnicalAnalyzer()
prices = pd.Series([150, 151, 149, 152, 153])
rsi = analyzer.calculate_rsi(prices)
print(rsi)
```

---

### `FundamentalAnalyzer`
Aggregate fundamental metrics.

**Methods:**
- `get_fundamentals(ticker: str) → Dict`: P/E, ROE, ROA, dividend yield, etc.
- `calculate_ratios(financial_data: Dict) → Dict`: Calculated financial ratios
- `get_comparison(tickers: List[str]) → pd.DataFrame`: Compare metrics across tickers

**Example:**
```python
from src.portfolio_fundamentals import FundamentalAnalyzer

analyzer = FundamentalAnalyzer()
fundamentals = analyzer.get_fundamentals("AAPL")
print(f"P/E: {fundamentals['pe_ratio']}")
```

---

### `ParquetDB`
Data storage and retrieval.

**Methods:**
- `save(data: pd.DataFrame, table_name: str) → str`: Save to Parquet, returns file path
- `load(table_name: str) → pd.DataFrame`: Load Parquet file
- `append(data: pd.DataFrame, table_name: str) → str`: Append to existing table
- `query(table_name: str, filters: Dict) → pd.DataFrame`: Query with filters

**Example:**
```python
from src.parquet_db import ParquetDB
import pandas as pd

db = ParquetDB()
df = pd.DataFrame({"ticker": ["AAPL", "MSFT"], "price": [150, 310]})
path = db.save(df, "prices")
print(f"Saved to: {path}")
```

---

### `Cache`
Simple in-memory caching with TTL.

**Methods:**
- `get(key: str) → Any`: Retrieve cached value
- `set(key: str, value: Any, ttl: int = 3600) → None`: Cache value with TTL (seconds)
- `delete(key: str) → None`: Remove from cache
- `clear() → None`: Clear all cache

**Example:**
```python
from src.cache import Cache

cache = Cache()
cache.set("AAPL_price", 150.25, ttl=3600)
price = cache.get("AAPL_price")
```

---

## Helper Functions

### `fetch_company_cik(ticker: str) → Optional[str]`
Get SEC company identifier from ticker.

```python
from src.xbrl import fetch_company_cik

cik = fetch_company_cik("AAPL")
print(cik)  # "0000320193"
```

---

### `fetch_xbrl_filings(ticker: str, filing_types: List[str] = ["10-K"], limit: int = 5) → List[Dict]`
Fetch SEC XBRL filings with fundamentals.

```python
from src.xbrl import fetch_xbrl_filings

filings = fetch_xbrl_filings("AAPL", filing_types=["10-K"])
for filing in filings:
    print(f"{filing['form_type']} - {filing['filing_date']}")
```

---

### `get_fx_rate(from_currency: str, to_currency: str) → float`
Get currency conversion rate.

```python
from src.fx_rates import get_fx_rate

rate = get_fx_rate("EUR", "USD")
print(f"1 EUR = {rate} USD")
```

---

## Data Models

### Portfolio Data (Parquet)
Stored with schema:
```python
{
    "ticker": str,
    "shares": float,
    "entry_price": float,
    "current_price": float,
    "currency": str,
    "broker": str,
    "date": datetime,
    "pe_ratio": float,
    "roe": float,
    "rsi": float,
    "macd": float,
    "pnl": float,
}
```

### Technical Signals
```python
{
    "rsi": float,           # 0-100
    "macd": float,          # MACD line
    "macd_signal": float,   # Signal line
    "bb_upper": float,      # Bollinger Band upper
    "bb_lower": float,      # Bollinger Band lower
    "signal": str,          # "BUY", "SELL", "HOLD"
}
```

### Configuration (config.csv)
```csv
report_email,your-email@example.com
sender_email,gmail@gmail.com
sender_password,app-password
smtp_host,smtp.gmail.com
smtp_port,587
alpha_vantage_key,YOUR_KEY
```
