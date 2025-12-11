<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Critical Development Guidelines

### Package Management & Execution
- **Always use `uv`** for package management and dependencies
- Run Python code with `uv run python`
- Run pytest with `uv run pytest` or `uv run --with pytest python -m pytest`
- Never attempt to use `timeout` command (not available on macOS)

### Code Organization
- **Source code:** Place all production code in the `src/` folder
- **Documentation:** Place all documentation in the `docs/` folder
- **Clear & concise:** Keep documentation brief, focused, and actionable

## Setup Checklist

- [x] Verify that the copilot-instructions.md file in the .github directory is created.
- [x] Clarify Project Requirements
- [x] Scaffold the Project
- [x] Customize the Project
- [x] Install Required Extensions
- [x] Compile the Project
- [x] Create and Run Task
- [x] Launch the Project
- [x] Ensure Documentation is Complete

## Project Information

**Project Type:** Python Script with Prefect Workflow Orchestration  
**Language:** Python 3.13+  
**Status:** Complete and Tested  
**Data Format:** Apache Parquet (with Snappy compression)

## Project Overview

SEC Filings Scraper is a production-ready Python application that scrapes SEC filings from EDGAR using Prefect for workflow orchestration. The project includes comprehensive testing with Prefect integration and stores data efficiently in Parquet format.

### Key Components

1. **main.py** - Prefect flows for scraping SEC filings
   - `fetch_company_cik()` - Get company identifiers
   - `fetch_sec_filings()` - Retrieve filing metadata
   - `save_filings_to_parquet()` - Store data in Parquet format
   - `scrape_sec_filings()` - Main orchestration flow

2. **test_sec_scraper.py** - 22 unit tests covering:
   - CIK extraction and validation
   - Filing data parsing
   - Parquet data storage
   - Error handling and edge cases

3. **test_integration.py** - Prefect test workflows
   - Full test suite execution
   - Individual test class runs
   - Coverage analysis
   - Report generation

4. **Documentation**
   - README.md - Project overview and usage
   - TESTING.md - Comprehensive testing guide

## Running the Project

```bash
# Scrape SEC filings
uv run python main.py

# Run tests (quick)
uv run --with pytest python -m pytest test_sec_scraper.py -v

# Run tests with Prefect
uv run python test_integration.py

# Interactive test menu
uv run python run_tests.py

# Start Prefect server for monitoring
uv run python -m prefect server start
```

## Data Management

- **Output Format:** Apache Parquet
- **Storage Location:** `db/sec_filings_<timestamp>.parquet`
- **Compression:** Snappy
- **Data Structure:** Accession number, filing date, report date, form type, CIK

## Testing Status

✓ All 22 tests passing  
✓ Prefect integration complete  
✓ Coverage reports available  
✓ CI/CD ready

## Dependencies

**Core:**
- prefect>=3.6.4
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- pandas>=2.0.0
- pyarrow>=14.0.0

**Development:**
- pytest>=7.4.0
- pytest-asyncio>=0.21.0

## Architecture Notes

- Uses SEC's official company_tickers.json for reliable CIK lookup
- Implements rate limiting with 1-second delays between requests
- Prefect tasks include automatic retries (3x for CIK/filing fetches)
- All data stored with compression for efficiency
- Comprehensive error handling and logging throughout
