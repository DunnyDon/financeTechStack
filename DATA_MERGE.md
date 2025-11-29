# Data Merge Quick Start

## Overview

The `data_merge.py` module provides utilities to combine Alpha Vantage and XBRL financial data by ticker symbol.

## Basic Usage

### 1. Read Data from Multiple Sources

```python
from src.data_merge import read_alpha_vantage_data, read_xbrl_data

# Read latest Alpha Vantage data
av_data = read_alpha_vantage_data()
print(av_data.head())

# Read latest XBRL data
xbrl_data = read_xbrl_data()
print(xbrl_data.head())
```

### 2. Merge Datasets

```python
from src.data_merge import merge_fundamental_data

# Combine both datasets
merged = merge_fundamental_data(av_data, xbrl_data)
print(f"Total tickers: {len(merged)}")
print(f"Total columns: {len(merged.columns)}")
```

### 3. Enrich with Calculated Metrics

```python
from src.data_merge import enrich_with_calculated_metrics

# Add calculated fields
enriched = enrich_with_calculated_metrics(merged)
print(enriched.columns)
# Shows: profit_score, health_score, value_score, enriched_at, ...
```

### 4. Save to Parquet

```python
from src.data_merge import save_merged_data_to_parquet

# Save with compression
output_file = save_merged_data_to_parquet(enriched)
print(f"Saved to: {output_file}")
```

## Analysis Functions

### Get Analysis for Specific Ticker

```python
from src.data_merge import get_ticker_analysis

# Get all available data for a ticker
aapl_data = get_ticker_analysis(enriched, "AAPL")
print(aapl_data)

# Output: Dictionary with all metrics for AAPL
# {
#   'ticker': 'AAPL',
#   'name': 'Apple Inc',
#   'sector': 'Technology',
#   'pe_ratio': 28.5,
#   'revenue': 394328000000,
#   'net_income': 96995000000,
#   'current_ratio': 1.5,
#   'debt_to_equity': 0.4,
#   ...
# }
```

### Compare Metrics Across Tickers

```python
from src.data_merge import compare_tickers

# Compare P/E ratios
pe_comparison = compare_tickers(enriched, ["AAPL", "MSFT", "GOOGL"], "pe_ratio")
print(pe_comparison)

# Compare margins
margin_comparison = compare_tickers(enriched, ["AAPL", "MSFT", "GOOGL"], "profit_margin")
print(margin_comparison)
```

## Complete Workflow Example

```python
from src.data_merge import (
    read_alpha_vantage_data,
    read_xbrl_data,
    merge_fundamental_data,
    enrich_with_calculated_metrics,
    save_merged_data_to_parquet,
    get_ticker_analysis,
    compare_tickers,
)

# Step 1: Load data from both sources
av_data = read_alpha_vantage_data()
xbrl_data = read_xbrl_data()

# Step 2: Merge datasets
merged = merge_fundamental_data(av_data, xbrl_data)

# Step 3: Enrich with calculations
enriched = enrich_with_calculated_metrics(merged)

# Step 4: Save merged data
output_file = save_merged_data_to_parquet(enriched)
print(f"✓ Saved to {output_file}")

# Step 5: Analyze specific ticker
aapl = get_ticker_analysis(enriched, "AAPL")
print(f"\nApple Inc:")
print(f"  P/E Ratio: {aapl.get('pe_ratio_numeric', 'N/A')}")
print(f"  Profit Margin: {aapl.get('profit_margin', 'N/A')}")
print(f"  ROE: {aapl.get('roe', 'N/A')}")

# Step 6: Compare across companies
tech_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN"]
print("\nP/E Ratio Comparison:")
pe_comp = compare_tickers(enriched, tech_stocks, "pe_ratio_numeric")
print(pe_comp)
```

## Prefect Integration

### Running as Prefect Flow

```python
from prefect import flow
from src.data_merge import (
    read_alpha_vantage_data,
    read_xbrl_data,
    merge_fundamental_data,
    enrich_with_calculated_metrics,
    save_merged_data_to_parquet,
)

@flow(name="Merge Financial Data")
def merge_flow():
    """Orchestrate data merging workflow."""
    # Read data (automatically handles logging)
    av_data = read_alpha_vantage_data()
    xbrl_data = read_xbrl_data()
    
    # Merge
    merged = merge_fundamental_data(av_data, xbrl_data)
    
    # Enrich
    enriched = enrich_with_calculated_metrics(merged)
    
    # Save
    output = save_merged_data_to_parquet(enriched)
    return output

# Run the flow
result = merge_flow()
```

## Data Schema

### Available Columns (after merge)

**From Alpha Vantage:**
- ticker, name, sector, industry
- market_cap, pe_ratio, eps
- revenue, gross_profit_margin, profit_margin, operating_margin
- roe, roa, debt_to_equity
- book_value, price_to_book, dividend_yield

**From XBRL:**
- ticker
- revenue, net_income, gross_profit, operating_income
- total_assets, total_liabilities, shareholders_equity
- current_assets, current_liabilities
- current_ratio, debt_to_equity, quick_ratio

**Calculated Metrics (enrichment):**
- profit_score (avg of all profit margins)
- health_score (avg of financial ratios)
- value_score (inverse of P/E ratio)
- enriched_at (timestamp)

## Filtering and Analysis

### Filter by Sector

```python
# Get all tech companies
tech = enriched[enriched['sector'] == 'Technology']
print(f"Tech stocks in dataset: {len(tech)}")
```

### Filter by Valuation

```python
# Find undervalued stocks (P/E < 20)
undervalued = enriched[enriched['pe_ratio_numeric'] < 20]
print(undervalued[['ticker', 'pe_ratio_numeric', 'revenue']])
```

### Filter by Profitability

```python
# Find highly profitable companies (margin > 20%)
profitable = enriched[enriched['profit_margin'] > 0.20]
print(profitable[['ticker', 'profit_margin', 'roe']])
```

### Statistical Summary

```python
# Calculate statistics
stats = enriched[['pe_ratio_numeric', 'profit_margin', 'roe']].describe()
print(stats)
```

## Common Queries

### Get Top Companies by Metric

```python
# Top 5 by P/E ratio (lowest = best value)
top_value = enriched.nsmallest(5, 'pe_ratio_numeric')[['ticker', 'pe_ratio_numeric']]

# Top 5 by ROE (highest = best return)
top_return = enriched.nlargest(5, 'roe')[['ticker', 'roe']]

# Top 5 by market cap
top_cap = enriched.nlargest(5, 'market_cap')[['ticker', 'market_cap']]
```

### Find Companies Meeting Criteria

```python
# Quality screen: High ROE + Low P/E
quality = enriched[
    (enriched['roe'] > 0.15) & 
    (enriched['pe_ratio_numeric'] < 20)
][['ticker', 'pe_ratio_numeric', 'roe']]

# Growth screen: High growth (proxy: high revenue)
growth = enriched[
    enriched['revenue'] > enriched['revenue'].quantile(0.75)
][['ticker', 'revenue', 'profit_margin']]
```

## Troubleshooting

### No Data Returned
```python
# Check if files exist
import glob
av_files = glob.glob("db/fundamentals_*.parquet")
xbrl_files = glob.glob("db/xbrl_data_*.parquet")
print(f"Alpha Vantage files: {av_files}")
print(f"XBRL files: {xbrl_files}")
```

### Missing Columns
```python
# Check what columns are available
print("Available columns:")
print(enriched.columns.tolist())

# Check data types
print("\nData types:")
print(enriched.dtypes)
```

### NaN Values
```python
# Find columns with missing data
print(enriched.isnull().sum())

# Replace NaN with 0 (if appropriate)
enriched = enriched.fillna(0)

# Or drop rows with too many NaN values
enriched = enriched.dropna(thresh=len(enriched.columns) * 0.5)
```

## Performance Tips

1. **Filter early**: Reduce dataset size before analysis
2. **Use columns parameter**: Only load needed columns
3. **Cache results**: Save merged data to avoid re-merging
4. **Use Prefect flows**: Automatic caching and monitoring
5. **Batch operations**: Process multiple tickers efficiently

## Next Steps

1. Load merged data into analysis tool
2. Build dashboards with Streamlit or Plotly
3. Create trading signals from metrics
4. Export to Excel/CSV for reporting
5. Schedule regular updates with Prefect
