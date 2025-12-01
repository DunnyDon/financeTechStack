# Portfolio Flows Quick Reference

## Quick Start

### 1. Run End-to-End Flow (Recommended)

```python
from src.portfolio_flows import portfolio_end_to_end_flow

# Analyze AAPL, MSFT, and GOOGL
result = portfolio_end_to_end_flow(
    tickers=["AAPL", "MSFT", "GOOGL"],
    output_dir="./db"
)

print(f"Status: {result['status']}")
print(f"Parquet: {result['parquet_file']}")
print(f"HTML Report: {result['analysis']['reports']['html_report']}")
```

### 2. Two-Step Process

```python
from src.portfolio_flows import (
    aggregate_financial_data_flow,
    portfolio_analysis_flow
)

# Step 1: Aggregate data
agg = aggregate_financial_data_flow(tickers=["AAPL"], output_dir="./db")
parquet_file = agg["parquet_file"]

# Step 2: Analyze
analysis = portfolio_analysis_flow(
    parquet_file=parquet_file,
    output_dir="./db"
)

print(f"Reports: {analysis['reports']}")
```

## Task Overview

### Data Aggregation Tasks

| Task | Purpose | Retries |
|------|---------|---------|
| `fetch_sec_cik_task` | Get company CIK from SEC | 3x |
| `fetch_sec_filings_task` | Retrieve SEC 10-K filings | 3x |
| `parse_xbrl_data_task` | Parse XBRL fundamentals | 2x |
| `fetch_pricing_data_task` | Get current stock price | - |
| `aggregate_and_save_to_parquet_task` | Save all data to Parquet | - |

### Analysis Tasks

| Task | Purpose | Output |
|------|---------|--------|
| `load_portfolio_from_parquet_task` | Load Parquet data | DataFrame |
| `calculate_technical_indicators_task` | Calculate indicators | Dict |
| `calculate_portfolio_analysis_task` | Analyze portfolio | Analysis dict |
| `generate_portfolio_reports_task` | Create reports | HTML + JSON |

## Flow Return Values

### aggregate_financial_data_flow

```python
{
    "parquet_file": "/path/to/financial_data_YYYYMMDD_HHMMSS.parquet",
    "summary": {
        "total_records": <count>,
        "tickers": [list],
        "records_with_prices": <count>,
        "records_with_fundamentals": <count>
    },
    "status": "success" | "error"
}
```

### portfolio_analysis_flow

```python
{
    "reports": {
        "html_report": "/path/to/portfolio_analysis_YYYYMMDD_HHMMSS.html",
        "json_report": "/path/to/portfolio_analysis_YYYYMMDD_HHMMSS.json",
        "summary": {...}
    },
    "analysis_results": {...},
    "status": "success" | "error"
}
```

### portfolio_end_to_end_flow

```python
{
    "status": "success" | "error",
    "aggregation": {...},  # Result of aggregate flow
    "analysis": {...},     # Result of analysis flow
    "parquet_file": "...",
    "timestamp": "ISO timestamp"
}
```

## Common Patterns

### Analyze Multiple Ticker Sets

```python
from src.portfolio_flows import portfolio_end_to_end_flow

portfolios = {
    "tech": ["AAPL", "MSFT", "GOOGL"],
    "finance": ["JPM", "BAC", "GS"],
    "energy": ["XOM", "CVX", "COP"]
}

for name, tickers in portfolios.items():
    result = portfolio_end_to_end_flow(
        tickers=tickers,
        output_dir=f"./outputs/{name}"
    )
    print(f"{name}: {result['status']}")
```

### Schedule Daily Analysis

```bash
# With Prefect deployment
prefect deploy src.portfolio_flows.py

# Then configure schedule in Prefect UI
```

Or programmatically:

```python
from prefect import flow
from prefect.schedules import cron

@flow(name="daily_portfolio_flow")
def daily_portfolio_flow():
    return portfolio_end_to_end_flow(
        tickers=["AAPL", "MSFT", "GOOGL"]
    )
```

### Error Handling

```python
from src.portfolio_flows import portfolio_end_to_end_flow

result = portfolio_end_to_end_flow(tickers=["AAPL"])

if result["status"] == "success":
    print("✓ Analysis complete")
    html = result["analysis"]["reports"]["html_report"]
    print(f"  Report: {html}")
else:
    print(f"✗ Error: {result.get('message', 'Unknown error')}")
```

## Monitoring

### Prefect Server

```bash
# Start server
prefect server start

# Access UI
open http://localhost:4200
```

### View Logs

```python
from prefect import get_run_logger

# Inside a task/flow
logger = get_run_logger()
logger.info("Task executing")
```

## Testing

```bash
# Run all flow tests
python -m pytest tests/test_portfolio_flows.py -v

# Run specific test
python -m pytest tests/test_portfolio_flows.py::TestPortfolioFlows::test_aggregate_financial_data_flow_basic -v

# With coverage
python -m pytest tests/test_portfolio_flows.py --cov
```

## Output Files

After running flows, check `./db/`:

```
db/
├── financial_data_20240101_120000.parquet      # Aggregated data
├── portfolio_analysis_20240101_120000.html     # Analysis report (HTML)
└── portfolio_analysis_20240101_120000.json     # Analysis report (JSON)
```

### Analyzing Parquet File

```python
import pandas as pd

df = pd.read_parquet("./db/financial_data_20240101_120000.parquet")

# View structure
print(df.info())

# View data
print(df.head())

# View columns
print(df.columns.tolist())

# Filter by ticker
aapl = df[df["ticker"] == "AAPL"]
print(aapl)
```

## Environment Setup

```bash
# Configure output directory
export PORTFOLIO_OUTPUT_DIR=./db

# Configure API keys
export ALPHA_VANTAGE_API_KEY=your_key_here

# Run flow
python -c "from src.portfolio_flows import portfolio_end_to_end_flow; portfolio_end_to_end_flow()"
```

## Tips & Tricks

### 1. Check What's in Parquet Before Analysis

```python
import pandas as pd

# Verify aggregation worked
df = pd.read_parquet("./db/financial_data_YYYYMMDD_HHMMSS.parquet")
print(f"Records: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print(f"Tickers: {df['ticker'].unique().tolist()}")
print(f"Has prices: {df['price'].notna().sum()} of {len(df)}")
```

### 2. Re-analyze Without Re-aggregating

```python
from src.portfolio_flows import portfolio_analysis_flow

# Skip aggregation, just analyze existing parquet
result = portfolio_analysis_flow(
    parquet_file="./db/financial_data_YYYYMMDD_HHMMSS.parquet",
    output_dir="./db"
)
```

### 3. Inspect Generated Reports

```python
import json

# View JSON report
with open("./db/portfolio_analysis_YYYYMMDD_HHMMSS.json") as f:
    report = json.load(f)
    print(json.dumps(report, indent=2))

# Open HTML report
import webbrowser
webbrowser.open("./db/portfolio_analysis_YYYYMMDD_HHMMSS.html")
```

### 4. Debug Task Execution

```python
# Add logging to flow
from prefect import get_run_logger

# Inside any flow or task
logger = get_run_logger()
logger.info(f"Variable value: {some_var}")
logger.error(f"Error occurred: {error}")
```

## Performance Tips

1. **Batch Analysis:** Analyze multiple tickers in one flow call
2. **Reuse Parquet:** Use `portfolio_analysis_flow` directly instead of re-aggregating
3. **Schedule Off-Peak:** Run at night or weekends to avoid API rate limits
4. **Monitor Duration:** Check Prefect UI for slow tasks

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No CIK found" | Verify ticker exists; try `AAPL`, `MSFT`, `GOOGL` |
| Empty DataFrame | Check API keys and internet connection |
| Slow execution | Reduce number of tickers or check internet speed |
| Missing reports | Ensure output directory exists and is writable |
| Import errors | Run `uv sync` to install dependencies |

## Examples

### Example 1: Analyze Tech Stocks

```python
from src.portfolio_flows import portfolio_end_to_end_flow

result = portfolio_end_to_end_flow(
    tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "TESLA"],
    output_dir="./outputs/tech"
)

print(f"Analyzed {len(result['analysis']['analysis_results']['tickers'])} tickers")
```

### Example 2: Generate Report for Client

```python
from src.portfolio_flows import portfolio_end_to_end_flow

result = portfolio_end_to_end_flow(
    tickers=["JPM", "BAC", "WFC", "GS"],
    output_dir="./client_reports/2024-01"
)

html_report = result['analysis']['reports']['html_report']
print(f"Report generated: {html_report}")
# Share HTML file with client
```

### Example 3: Batch Processing

```python
from src.portfolio_flows import portfolio_end_to_end_flow

tickers_list = [
    ["AAPL", "MSFT"],
    ["JPM", "BAC"],
    ["XOM", "CVX"],
]

for i, tickers in enumerate(tickers_list):
    result = portfolio_end_to_end_flow(
        tickers=tickers,
        output_dir=f"./batch_{i+1}"
    )
    print(f"Batch {i+1}: {result['status']}")
```

## See Also

- Full Documentation: `docs/PORTFOLIO_FLOWS.md`
- Flow Implementation: `src/portfolio_flows.py`
- Tests: `tests/test_portfolio_flows.py`
- Prefect Docs: https://docs.prefect.io
