# SEC Filings Scraper

A Prefect-based Python script for scraping SEC (Securities and Exchange Commission) filings from EDGAR (Electronic Data Gathering, Organization, and Retrieval system).

## Features

- **Multi-company support**: Scrape filings for multiple stock tickers simultaneously
- **Flexible filing types**: Support for 10-K, 10-Q, 8-K, and other SEC filing types
- **Prefect workflows**: Organized flows with task-level error handling and retries
- **Parquet data storage**: Efficient columnar data format with compression
- **Comprehensive testing**: 22 unit tests with Prefect integration
- **Rate limiting**: Built-in delays to respect SEC API rate limits
- **Comprehensive logging**: Detailed Prefect logs for monitoring and debugging

## Installation

### Prerequisites
- Python 3.13 or higher
- pip or uv package manager

### Setup

1. Clone or navigate to this repository
2. Install dependencies:
   ```bash
   # Using pip with virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   
   # Or using uv
   uv sync
   ```

## Usage

### Basic Example

Run the default scraper for Apple and Microsoft:

```bash
uv run python main.py
```

This will:
1. Fetch CIK numbers for AAPL and MSFT
2. Retrieve the latest 5 10-K filings
3. Save filing metadata to `db/sec_filings_<timestamp>.parquet`

### Custom Usage

Modify `main.py` to customize the scraper:

```python
# Scrape different companies
filings = scrape_sec_filings(
    tickers=["GOOGL", "AMZN", "TSLA"],
    filing_type="10-Q",  # Quarterly reports
    limit=10
)
```

### Available Filing Types
- `10-K`: Annual report
- `10-Q`: Quarterly report
- `8-K`: Current report
- `S-1`: Registration statement
- And many others

## Testing

The project includes comprehensive testing with pytest and Prefect integration.

### Quick Test Run
```bash
uv run --with pytest python -m pytest test_sec_scraper.py -v
```

### Run Tests with Prefect
```bash
uv run python test_integration.py
```

### Interactive Test Menu
```bash
uv run python run_tests.py
```

For detailed testing documentation, see [TESTING.md](TESTING.md).

### Test Coverage
- ✓ 22 unit tests covering all major functionality
- ✓ CIK lookup validation for multiple tickers
- ✓ Filing data extraction and parsing
- ✓ Parquet data storage and integrity
- ✓ Error handling and edge cases

## Project Structure

```
.
├── main.py                 # Main script with Prefect flows and tasks
├── test_sec_scraper.py    # Unit tests (22 test cases)
├── test_integration.py    # Prefect test integration flows
├── run_tests.py           # Interactive test execution menu
├── pyproject.toml         # Project configuration and dependencies
├── README.md              # This file
├── TESTING.md             # Detailed testing documentation
├── db/                    # Directory for Parquet data files
└── .github/               # GitHub configuration
    └── copilot-instructions.md
```

## Data Storage

### Parquet Format
Data is saved in Apache Parquet format with Snappy compression:
- **Efficient**: Columnar storage format
- **Compressed**: Reduces file size by ~90%
- **Fast**: Optimized for analytical queries
- **Location**: `db/sec_filings_<timestamp>.parquet`

## Dependencies

- **prefect**: Workflow orchestration and monitoring
- **requests**: HTTP client for API requests
- **beautifulsoup4**: HTML parsing
- **pandas**: Data manipulation and CSV export
- **lxml**: XML/HTML parsing backend

## API Rate Limits

The SEC EDGAR API has rate limits. The scraper includes 1-second delays between requests. For bulk operations, consider:
- Spacing out requests over time
- Using Prefect's scheduling capabilities
- Implementing caching for CIK lookups

## Notes

- **User-Agent**: The scraper includes a User-Agent header to identify requests to SEC servers
- **Data Accuracy**: Filing data is sourced directly from SEC EDGAR
- **No Financial Advice**: This tool is for research purposes only

## Next Steps

- Configure Prefect server for workflow monitoring
- Add database support for storing filing metadata
- Implement document parsing for specific sections
- Add email notifications for new filings

## License

MIT
