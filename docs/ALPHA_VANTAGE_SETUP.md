# Alpha Vantage Setup Guide

This guide explains how to use the Alpha Vantage API integration for fundamental equity analysis.

## Setup

### 1. Get Your Free Alpha Vantage API Key

1. Visit: https://www.alphavantage.co/
2. Click "GET FREE API KEY"
3. Enter your email and receive your key
4. You'll get an API key immediately

### 2. Configure Your API Key

**Option A: Using config.csv (Recommended)**
1. Copy `config.csv.template` to `config.csv`:
   ```bash
   cp config.csv.template config.csv
   ```
2. Edit `config.csv` and replace `your_api_key_here` with your actual API key:
   ```csv
   api_key,value
   alpha_vantage_key,YOUR_ACTUAL_API_KEY_HERE
   ```

**Option B: Using Environment Variable**
Set the environment variable instead:
```bash
export ALPHA_VANTAGE_KEY=your_actual_api_key_here
```

### 3. Verify .gitignore

The `config.csv` file is already in `.gitignore` so your API key won't be committed to GitHub.

## Usage

### Fetch Fundamental Data

```bash
# Run fundamental analysis for multiple companies
uv run python alpha_vantage.py
```

### Use in Your Code

```python
from alpha_vantage import fetch_fundamentals

# Fetch fundamentals for specific tickers
results = fetch_fundamentals(["AAPL", "MSFT", "GOOGL"])

# Results are saved to: db/fundamentals_<timestamp>.parquet
```

### With Prefect Flow

```python
from alpha_vantage import fetch_fundamentals

# Run as Prefect flow with monitoring
results = fetch_fundamentals.serve()
```

## Available Metrics

The integration fetches these fundamental metrics for each company:

- **Company Info**: Name, Sector, Industry
- **Valuation**: Market Cap, P/E Ratio, Book Value, Price-to-Book
- **Profitability**: EPS, Revenue, Gross Margin, Profit Margin, Operating Margin
- **Returns**: ROE (Return on Equity), ROA (Return on Assets)
- **Leverage**: Debt-to-Equity Ratio
- **Income**: Dividend Yield

## Rate Limits

**Alpha Vantage Free Tier:**
- 5 requests per minute
- 500 requests per day
- The scraper automatically waits 12 seconds between requests

**For higher limits**, upgrade to a premium plan.

## Reading the Data

```python
import pandas as pd

# Read fundamental data
df = pd.read_parquet("db/fundamentals_<timestamp>.parquet")

# View the data
print(df.head())

# Filter by sector
tech_stocks = df[df['sector'] == 'Technology']

# Analyze valuation
print(df[['ticker', 'pe_ratio', 'price_to_book']])
```

## Troubleshooting

### "Config file not found"
```bash
cp config.csv.template config.csv
# Then edit config.csv with your API key
```

### "Alpha Vantage API key not found"
Make sure either:
1. `config.csv` contains your API key, or
2. The `ALPHA_VANTAGE_KEY` environment variable is set

### "API call frequency error"
Alpha Vantage is rate-limiting your requests. Wait a few minutes and try again.

### "N/A" values in results
Some metrics may not be available for all companies, especially smaller ones or non-US companies.

## Combining with SEC Filings Data

You can combine SEC filing metadata with fundamental data:

```python
import pandas as pd

# Load both datasets
filings_df = pd.read_parquet("db/sec_filings_*.parquet")
fundamentals_df = pd.read_parquet("db/fundamentals_*.parquet")

# Merge on ticker (requires extracting ticker from CIK)
# Create a mapping of CIK to ticker first
```

## Next Steps

1. ✅ Configure your API key
2. ✅ Run the fundamental analysis scraper
3. ✅ Combine with SEC filings data
4. ✅ Build analysis dashboards
5. ✅ Create trading signals based on fundamentals

## References

- Alpha Vantage Docs: https://www.alphavantage.co/documentation/
- Fundamental Analysis Guide: https://www.investopedia.com/terms/f/fundamental_analysis.asp
