# Portfolio Flows Documentation

## Overview

The portfolio flows module provides three comprehensive Prefect workflows for financial data aggregation and portfolio analysis:

1. **`aggregate_financial_data_flow`** - Scrapes and aggregates SEC data, pricing data, and saves to Parquet
2. **`portfolio_analysis_flow`** - Runs portfolio analysis on saved Parquet data
3. **`portfolio_end_to_end_flow`** - Complete end-to-end workflow combining both flows

## Architecture

### Data Flow Diagram

```
aggregate_financial_data_flow
├── For each ticker:
│   ├── fetch_sec_cik_task
│   ├── fetch_sec_filings_task
│   ├── parse_xbrl_data_task
│   └── fetch_pricing_data_task
└── aggregate_and_save_to_parquet_task
    └── Creates: financial_data_<timestamp>.parquet

portfolio_analysis_flow
├── load_portfolio_from_parquet_task
├── calculate_technical_indicators_task
├── calculate_portfolio_analysis_task
└── generate_portfolio_reports_task
    ├── Creates: portfolio_analysis_<timestamp>.html
    └── Creates: portfolio_analysis_<timestamp>.json

portfolio_end_to_end_flow
├── Runs: aggregate_financial_data_flow
└── Runs: portfolio_analysis_flow (using aggregated data)
```

## Flow Details

### 1. aggregate_financial_data_flow

**Purpose:** Gather financial data from multiple sources and save to Parquet format.

**Tasks:**
- `fetch_sec_cik_task` - Fetch company CIK from SEC (retries: 3)
- `fetch_sec_filings_task` - Retrieve SEC filing metadata (retries: 3)
- `parse_xbrl_data_task` - Parse XBRL fundamentals (retries: 2)
- `fetch_pricing_data_task` - Get current pricing data
- `aggregate_and_save_to_parquet_task` - Combine and save all data

**Input Parameters:**
- `tickers` (list): Stock ticker symbols. Default: `["AAPL", "MSFT", "GOOGL"]`
- `output_dir` (str): Output directory. Default: `DEFAULT_OUTPUT_DIR`

**Output:**
```python
{
    "parquet_file": "/path/to/financial_data_20240101_120000.parquet",
    "summary": {
        "total_records": 3,
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "records_with_prices": 3,
        "records_with_fundamentals": 2
    },
    "status": "success"
}
```

**Example Usage:**
```python
from src.portfolio_flows import aggregate_financial_data_flow

result = aggregate_financial_data_flow(
    tickers=["AAPL", "MSFT", "TSLA"],
    output_dir="./db"
)

print(result["parquet_file"])  # Path to saved Parquet
```

### 2. portfolio_analysis_flow

**Purpose:** Analyze portfolio data from Parquet and generate reports.

**Tasks:**
- `load_portfolio_from_parquet_task` - Load Parquet data
- `calculate_technical_indicators_task` - Calculate technical analysis
- `calculate_portfolio_analysis_task` - Compute portfolio metrics
- `generate_portfolio_reports_task` - Create HTML and JSON reports

**Input Parameters:**
- `parquet_file` (str): Path to Parquet file with portfolio data
- `output_dir` (str): Output directory for reports. Default: `DEFAULT_OUTPUT_DIR`

**Output:**
```python
{
    "reports": {
        "html_report": "/path/to/portfolio_analysis_20240101_120000.html",
        "json_report": "/path/to/portfolio_analysis_20240101_120000.json",
        "summary": {
            "total_records": 3,
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "records_with_prices": 3,
            "technical_indicators_calculated": 3
        }
    },
    "analysis_results": {...},
    "status": "success"
}
```

**Example Usage:**
```python
from src.portfolio_flows import portfolio_analysis_flow

result = portfolio_analysis_flow(
    parquet_file="./db/financial_data_20240101_120000.parquet",
    output_dir="./db"
)

print(result["reports"]["html_report"])
```

### 3. portfolio_end_to_end_flow

**Purpose:** Complete workflow from data collection to analysis and reporting.

**Orchestration:**
1. Calls `aggregate_financial_data_flow` to gather data
2. Calls `portfolio_analysis_flow` on the aggregated data
3. Returns combined results

**Input Parameters:**
- `tickers` (list): Stock ticker symbols. Default: `["AAPL", "MSFT", "GOOGL"]`
- `output_dir` (str): Output directory. Default: `DEFAULT_OUTPUT_DIR`

**Output:**
```python
{
    "status": "success",
    "aggregation": {
        "parquet_file": "...",
        "summary": {...},
        "status": "success"
    },
    "analysis": {
        "reports": {...},
        "analysis_results": {...},
        "status": "success"
    },
    "parquet_file": "...",
    "timestamp": "2024-01-01T12:00:00.000000"
}
```

**Example Usage:**
```python
from src.portfolio_flows import portfolio_end_to_end_flow

result = portfolio_end_to_end_flow(
    tickers=["AAPL", "MSFT", "GOOGL", "TSLA"],
    output_dir="./db"
)

print(f"Analysis complete: {result['status']}")
print(f"Parquet: {result['parquet_file']}")
print(f"HTML Report: {result['analysis']['reports']['html_report']}")
```

## Running the Flows

### Via Command Line

```bash
# Run aggregation flow
python -m prefect.cli flow run aggregate_financial_data_flow

# Run analysis flow (after aggregation)
python -m prefect.cli flow run portfolio_analysis_flow

# Run end-to-end flow
python -m prefect.cli flow run portfolio_end_to_end_flow
```

### Programmatically

```python
from src.portfolio_flows import portfolio_end_to_end_flow

# Execute the flow
result = portfolio_end_to_end_flow(
    tickers=["AAPL", "MSFT"],
    output_dir="./outputs"
)

# Check status
if result["status"] == "success":
    print(f"✓ Analysis complete")
    print(f"  Parquet: {result['parquet_file']}")
    print(f"  HTML Report: {result['analysis']['reports']['html_report']}")
else:
    print(f"✗ Error: {result['message']}")
```

### With Prefect Server

```bash
# Start Prefect server
prefect server start

# Deploy flows
prefect deploy src.portfolio_flows.py

# Monitor at http://localhost:4200
```

## Error Handling

All flows include comprehensive error handling:

- **Retries:** CIK and filing fetch tasks retry up to 3 times
- **Logging:** Detailed logging at each task execution
- **Graceful Degradation:** Flows continue if some tickers fail
- **Status Tracking:** All results include status field

### Common Issues

| Issue | Solution |
|-------|----------|
| "No CIK found" | Ticker may not exist or be recognized by SEC |
| "Empty DataFrame" | All tickers failed to fetch data; check API keys |
| "Parquet file not found" | Ensure aggregation flow completed successfully |
| API rate limits | Flows include 1-second delays between requests |

## Data Formats

### Parquet Schema

```
financial_data_<timestamp>.parquet
├── ticker (string): Stock symbol
├── cik (string): SEC CIK number
├── price (double): Current stock price
├── price_source (string): Data source
├── fundamentals (struct): XBRL fundamental data
│   ├── revenue
│   ├── net_income
│   ├── total_assets
│   └── ...
└── fetched_at (string): ISO timestamp
```

### HTML Report

Includes:
- Summary metrics (total records, tickers, price coverage)
- Table of analyzed tickers
- Timestamp and generation time

### JSON Report

Contains structured analysis results:
- Record counts and statistics
- Ticker list
- Technical indicator calculations
- Fundamental metrics

## Performance Considerations

- **Data Aggregation:** ~10-20 seconds per ticker
- **Analysis Calculation:** ~5 seconds per ticker
- **Report Generation:** ~2 seconds
- **Total End-to-End:** ~30-60 seconds for 3 tickers

## Configuration

### Environment Variables

```bash
# SEC API (uses default if not set)
SEC_API_URL=https://www.sec.gov/cgi-bin/

# Output directory
PORTFOLIO_OUTPUT_DIR=./db

# Price fetcher configuration
ALPHA_VANTAGE_API_KEY=your_key_here
```

### Logging

Configure logging via `utils.py`:

```python
import logging
from src.utils import get_logger

logger = get_logger(__name__)
```

## Testing

Run the comprehensive test suite:

```bash
# Run all portfolio flow tests
python -m pytest tests/test_portfolio_flows.py -v

# Run specific test
python -m pytest tests/test_portfolio_flows.py::TestPortfolioFlows::test_aggregate_financial_data_flow_basic -v

# Run with coverage
python -m pytest tests/test_portfolio_flows.py --cov=src.portfolio_flows
```

### Test Categories

1. **Basic Flow Tests:** Verify individual flow execution
2. **Multiple Ticker Tests:** Test with multiple tickers
3. **Integration Tests:** End-to-end workflow tests
4. **Error Handling:** Verify graceful error handling

## Output Examples

### Aggregation Flow Output

```
Starting financial data aggregation flow for ['AAPL', 'MSFT']
Processing AAPL
  Fetching CIK for ticker: AAPL
  Found CIK 320193 for AAPL
  Fetching SEC filings for AAPL (CIK: 320193)
  Found latest 10-K filing for AAPL
  Parsing XBRL data for AAPL
  Successfully parsed XBRL fundamentals for AAPL
  Fetching pricing data for AAPL
  Successfully fetched price for AAPL: $190.25
Processing MSFT
  [similar output for MSFT]
Aggregating financial and pricing data
Saved aggregated data to ./db/financial_data_20240101_120000.parquet
Financial data aggregation flow complete. Parquet: ./db/financial_data_20240101_120000.parquet
```

### Analysis Flow Output

```
Starting portfolio analysis flow for ./db/financial_data_20240101_120000.parquet
Loading portfolio from parquet: ./db/financial_data_20240101_120000.parquet
Loaded 2 records from parquet
Calculating technical indicators
Calculated technical indicators for 2 tickers
Calculating portfolio analysis
Portfolio analysis complete
Generating portfolio reports
Generated reports: ./db/portfolio_analysis_20240101_120001.html, ./db/portfolio_analysis_20240101_120001.json
Portfolio analysis flow complete
```

## Advanced Usage

### Custom Task Configuration

```python
from prefect import task

@task(name="custom_task", retries=5, retry_delay_seconds=10)
def my_custom_task():
    pass
```

### Flow Parameters

```python
from prefect import flow, get_run_logger

@flow(
    name="my_flow",
    description="My flow description",
    timeout_seconds=3600
)
def my_flow():
    pass
```

### Subflow Execution

```python
@flow
def parent_flow():
    result = aggregate_financial_data_flow()
    return result
```

## Monitoring and Debugging

### Prefect UI

Access at `http://localhost:4200` to:
- View flow runs and task execution
- Monitor logs in real-time
- Check task state and duration
- Diagnose failures

### Logging Output

```python
from prefect import get_run_logger

logger = get_run_logger()
logger.info("Task started")
logger.warning("Something might be wrong")
logger.error("An error occurred")
```

### Performance Profiling

Track timing:

```python
import time
start = time.time()
# ... code ...
duration = time.time() - start
logger.info(f"Operation took {duration:.2f}s")
```

## Best Practices

1. **Use Prefect Server:** Monitor flows in production
2. **Configure Retries:** Increase for unstable APIs
3. **Validate Data:** Check parquet files after aggregation
4. **Log Extensively:** Include context in error messages
5. **Test Separately:** Debug individual tasks before flows
6. **Schedule Regularly:** Use Prefect deployments for recurring runs

## Troubleshooting

### Parquet File Issues

```python
import pandas as pd

# Verify parquet file
df = pd.read_parquet("financial_data_20240101_120000.parquet")
print(df.info())
print(df.head())
```

### API Rate Limiting

Flows include 1-second delays. Increase if needed:

```python
import time
time.sleep(2)  # Wait 2 seconds between requests
```

### Missing Dependencies

```bash
# Install required packages
uv pip install pyarrow pandas prefect beautifulsoup4 requests
```

## Version History

- **v1.0.0** (2024-01-01): Initial release with three flows

## Contributing

To add new flows:

1. Create new task functions with `@task` decorator
2. Create flow function with `@flow` decorator
3. Add comprehensive docstrings
4. Include error handling and logging
5. Add unit tests in `tests/test_portfolio_flows.py`
6. Update this documentation

## Support

For issues or questions:

1. Check Prefect documentation: https://docs.prefect.io
2. Review logs in Prefect UI
3. Check task execution details
4. Verify API keys and configuration
