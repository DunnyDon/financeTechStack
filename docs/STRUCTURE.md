# Project Structure Guide

## Directory Organization

```
TechStack/
├── src/                           # Source code directory
│   ├── __init__.py               # Python package marker
│   ├── config.py                 # Configuration loader (API keys, env vars)
│   ├── main.py                   # SEC EDGAR scraper (deprecated - metadata only)
│   ├── alpha_vantage.py          # Alpha Vantage financial data fetcher
│   ├── xbrl.py                   # XBRL parser for SEC filings
│   └── data_merge.py             # Data merging and enrichment utilities
│
├── tests/                         # Test suite directory
│   ├── __init__.py               # Python package marker
│   ├── run_tests.py              # Interactive test menu
│   ├── test_sec_scraper.py       # SEC scraper unit tests (22 tests)
│   ├── test_integration.py       # Prefect workflow integration tests
│   └── test_xbrl.py              # XBRL extraction tests (20 tests)
│
├── db/                           # Data storage directory
│   └── *.parquet                 # Parquet data files (in .gitignore)
│
├── config.csv                    # API configuration (user populates, in .gitignore)
├── config.csv.template           # Configuration template reference
├── pyproject.toml                # Project metadata and dependencies
├── .gitignore                    # Git ignore patterns
├── README.md                     # Project overview
├── TESTING.md                    # Testing documentation
├── ALPHA_VANTAGE_SETUP.md       # Alpha Vantage API setup guide
├── PROJECT_SUMMARY.md            # Detailed project summary
└── uv.lock                       # Dependency lock file
```

## Module Descriptions

### `src/config.py`
**Purpose:** Secure configuration management for API keys
- Loads API credentials from `config.csv`
- Falls back to environment variables
- Validates that placeholder values aren't used
- Used by: alpha_vantage.py, xbrl.py

**Key Functions:**
- `ConfigLoader.get()` - Get config value with fallback
- `ConfigLoader.get_alpha_vantage_key()` - Get Alpha Vantage API key

### `src/main.py`
**Status:** Deprecated (metadata only, not actionable)
- Fetches SEC filing metadata (accession numbers, dates, form types)
- No longer recommended for use
- Kept for reference/legacy compatibility

### `src/alpha_vantage.py`
**Purpose:** Fetch real-time fundamental financial data
- Connects to Alpha Vantage API
- Extracts 18+ financial metrics per company
- Includes Prefect task/flow orchestration
- Rate limited to 5 req/min (free tier)

**Key Functions:**
- `fetch_fundamental_data()` - Fetch fundamentals for a ticker
- `save_fundamentals_to_parquet()` - Save to Parquet with compression
- `fetch_fundamentals()` - Prefect flow for multiple tickers

**Data Extracted:**
- Valuation: P/E ratio, book value, price-to-book, market cap
- Profitability: EPS, margins (gross, operating, profit), ROE, ROA
- Financial health: Debt-to-equity, dividend yield

### `src/xbrl.py`
**Purpose:** Parse XBRL financial data from SEC filings
- Fetches 10-K/10-Q documents from SEC EDGAR
- Parses XML to extract financial metrics
- Includes calculated ratios (current ratio, debt-to-equity)
- Rate limited with 2-second delays

**Key Functions:**
- `fetch_company_cik()` - Get CIK from SEC official API
- `fetch_sec_filing_index()` - Get filing metadata
- `fetch_xbrl_document()` - Download XBRL from SEC
- `parse_xbrl_fundamentals()` - Extract financial data from XML
- `save_xbrl_data_to_parquet()` - Save to Parquet format
- `fetch_xbrl_filings()` - Prefect flow for orchestration

**Data Extracted:**
- Income statement: Revenue, net income, operating income
- Balance sheet: Assets, liabilities, equity
- Calculated: Current ratio, debt-to-equity, working capital

### `src/data_merge.py` ⭐ NEW
**Purpose:** Combine Alpha Vantage and XBRL data for comprehensive analysis
- Reads data from multiple Parquet sources
- Merges on ticker symbol (case-insensitive)
- Enriches with calculated metrics
- Provides analysis functions

**Key Functions:**
- `read_alpha_vantage_data()` - Load Alpha Vantage Parquet
- `read_xbrl_data()` - Load XBRL Parquet
- `merge_fundamental_data()` - Combine both sources
- `enrich_with_calculated_metrics()` - Add derived metrics
- `save_merged_data_to_parquet()` - Save combined data
- `get_ticker_analysis()` - Get all data for one ticker
- `compare_tickers()` - Compare metric across multiple tickers

**Example Usage:**
```python
from src.data_merge import (
    read_alpha_vantage_data,
    read_xbrl_data,
    merge_fundamental_data,
    get_ticker_analysis
)

av_data = read_alpha_vantage_data()
xbrl_data = read_xbrl_data()
merged = merge_fundamental_data(av_data, xbrl_data)
aapl_analysis = get_ticker_analysis(merged, "AAPL")
```

## Test Suite

### `tests/test_xbrl.py` (20 tests, all passing ✅)
- **TestCIKExtraction** (5 tests): CIK lookup from SEC
- **TestFilingIndexRetrieval** (4 tests): SEC filing metadata
- **TestXBRLParsing** (6 tests): XBRL data extraction and calculations
- **TestParquetStorage** (3 tests): Parquet file operations
- **TestXBRLIntegration** (2 tests): End-to-end workflows

### `tests/test_sec_scraper.py` (22 tests)
- Tests for SEC metadata scraper (legacy)
- Various CIK extraction scenarios
- Filing data parsing
- Parquet storage verification

### `tests/test_integration.py`
- Prefect workflow integration tests
- Multiple test execution modes
- Coverage analysis
- JSON reporting

## Running Tests

### Quick Run
```bash
# Run XBRL tests
uv run --with pytest python -m pytest tests/test_xbrl.py -v

# Run all tests
uv run --with pytest python -m pytest tests/ -v

# Run specific test class
uv run --with pytest python -m pytest tests/test_xbrl.py::TestXBRLParsing -v
```

### Using Test Menu
```bash
uv run python tests/run_tests.py
# Interactive menu with options for different test scenarios
```

### Coverage Analysis
```bash
uv run --with pytest python -m pytest tests/ --cov=src --cov-report=html
```

## Data Flow

### Alpha Vantage Pipeline
```
ticker
  ↓
fetch_fundamental_data() [Alpha Vantage API]
  ↓
{revenue, pe_ratio, margins, ROE, ROA, ...}
  ↓
save_fundamentals_to_parquet()
  ↓
db/fundamentals_YYYYMMDD_HHMMSS.parquet
```

### XBRL Pipeline
```
ticker
  ↓
fetch_company_cik() [SEC official API]
  ↓
fetch_sec_filing_index() [SEC EDGAR API]
  ↓
fetch_xbrl_document() [SEC EDGAR archive]
  ↓
parse_xbrl_fundamentals() [XML parsing]
  ↓
{revenue, net_income, assets, current_ratio, ...}
  ↓
save_xbrl_data_to_parquet()
  ↓
db/xbrl_data_YYYYMMDD_HHMMSS.parquet
```

### Merged Pipeline
```
db/fundamentals_*.parquet + db/xbrl_data_*.parquet
  ↓
read_alpha_vantage_data()
read_xbrl_data()
  ↓
merge_fundamental_data()
  ↓
enrich_with_calculated_metrics()
  ↓
save_merged_data_to_parquet()
  ↓
db/merged_fundamentals_YYYYMMDD_HHMMSS.parquet
```

## Import Patterns

### From Source Code
```python
# Relative imports (when using as package)
from src.config import config
from src.alpha_vantage import fetch_fundamentals
from src.xbrl import fetch_xbrl_filings
from src.data_merge import merge_fundamental_data

# Or direct imports from tests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import config
```

### From Tests
```python
# Tests automatically add src/ to path
from xbrl import fetch_company_cik
from alpha_vantage import fetch_fundamental_data
```

## Configuration

### Setup Steps
1. Copy template: `cp config.csv.template config.csv`
2. Add your Alpha Vantage API key to `config.csv`
3. File is in `.gitignore` so credentials stay secure

### Example config.csv
```csv
api_key,value
alpha_vantage_key,YOUR_API_KEY_HERE
```

## Database Files

All data stored in `db/` directory (in `.gitignore`):

- `fundamentals_*.parquet` - Alpha Vantage data
- `xbrl_data_*.parquet` - XBRL extracted data
- `merged_fundamentals_*.parquet` - Combined data
- `sec_filings_*.parquet` - SEC metadata (legacy)

Format: Apache Parquet with Snappy compression
- ~90% smaller than CSV equivalents
- Fast binary format for analysis
- Preserves data types

## Next Steps

1. **Run Alpha Vantage scraper**: `uv run python src/alpha_vantage.py`
2. **Run XBRL scraper**: `uv run python src/xbrl.py`
3. **Merge data**: Use `src/data_merge.py` functions
4. **Analyze**: Load merged data with pandas for analysis
5. **Build dashboards**: Use merged data for visualization

## Troubleshooting

### Import Errors
- Ensure `src/` and `tests/` have `__init__.py` files
- Check that imports use relative paths with fallback
- Verify sys.path includes src/ directory

### API Key Issues
- Check `config.csv` has correct API key
- Verify key isn't a placeholder value
- Try environment variable: `export ALPHA_VANTAGE_KEY=...`

### Rate Limiting
- Alpha Vantage: 5 req/min (free tier) - wait 12 seconds between calls
- SEC EDGAR: No official limit, but use 1-2 second delays
- XBRL parsing: Use 2-second delays between requests

### File Organization
- All source code in `src/`
- All tests in `tests/`
- All data in `db/`
- Configuration at root level
