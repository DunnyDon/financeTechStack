# Testing Guide

Comprehensive testing guide for the Finance TechStack project. Covers unit tests, integration tests, and Prefect workflow testing.

## Overview

The test suite includes 33 passing tests and 9 skipped tests:

- **33 tests passing**: Full coverage of all components
- **9 tests skipped**: Prefect task mocking tests (covered in test_sec_scraper.py)
- **Execution time**: ~2.6 seconds
- **Coverage**: Core functionality, error handling, edge cases

## Test Files

### `tests/test_sec_scraper.py` (22 tests - All passing)

Unit tests for SEC data extraction. Organized into 5 test classes:

- **TestCIKExtraction** (6 tests)
  - CIK lookup for AAPL, MSFT, AMZN
  - Case-insensitive lookups
  - Invalid ticker handling
  - CIK zero-padding validation

- **TestFilingExtraction** (6 tests)
  - 10-K filing extraction
  - Required field validation
  - Filing limit enforcement
  - Empty response handling
  - Multiple filing types (10-K, 10-Q)
  - Non-existent filing types

- **TestParquetSaving** (3 tests)
  - Parquet file creation
  - Data integrity validation
  - Multiple record storage

- **TestIntegration** (2 tests)
  - CIK fetch integration
  - Filing fetch integration

- **TestParametrized** (5 tests)
  - Multiple tickers: AAPL, MSFT, AMZN
  - Multiple filing types: 10-K, 10-Q

### `tests/test_xbrl.py` (11 passed, 9 skipped)

Tests for XBRL financial data extraction:

- **TestCIKExtraction** (5 tests - Skipped)
  - Reason: Prefect task mocking - use test_sec_scraper.py instead

- **TestFilingIndexRetrieval** (4 tests - Skipped)
  - Reason: Prefect task mocking - use test_sec_scraper.py instead

- **TestXBRLParsing** (6 tests - All passing)
  - Valid XBRL data parsing from SEC JSON API
  - Debt-to-equity ratio calculation
  - Current ratio calculation
  - Missing field handling
  - Invalid data handling
  - Empty data handling

- **TestParquetStorage** (3 tests - All passing)
  - Single record storage
  - Multiple records storage
  - Compression validation

- **TestXBRLIntegration** (2 tests - All passing)
  - XBRL data structure validation for AAPL
  - XBRL data structure validation for MSFT

### `tests/test_integration.py`

Prefect workflow integration for comprehensive testing:

- **SEC Scraper Test Suite Flow**: Runs all pytest tests through Prefect
- **SEC Scraper Test Classes Flow**: Runs each test class individually
- **SEC Scraper Comprehensive Testing Flow**: Main orchestration flow

Features:
- Subprocess-based pytest execution
- Result validation and metrics extraction
- JSON report generation
- Detailed Prefect logging
- Automatic retry logic

## Running Tests

### Quick Test Run (Recommended)

```bash
# Run all unit tests
uv run --with pytest python -m pytest tests/ -v

# Run specific test file
uv run --with pytest python -m pytest tests/test_sec_scraper.py -v
uv run --with pytest python -m pytest tests/test_xbrl.py -v
```

### Run Specific Tests

```bash
# Run specific test class
uv run --with pytest python -m pytest tests/test_sec_scraper.py::TestCIKExtraction -v

# Run specific test method
uv run --with pytest python -m pytest tests/test_sec_scraper.py::TestCIKExtraction::test_extract_cik_aapl -v

# Run tests matching pattern
uv run --with pytest python -m pytest tests/ -k "extract_cik" -v
```

### Run with Prefect Integration

```bash
# Run full Prefect test suite (recommended for production)
uv run python tests/test_integration.py
```

This will:
1. Start a temporary Prefect server
2. Run all pytest tests through Prefect tasks
3. Execute individual test classes for granular monitoring
4. Generate `test_results.json` report
5. Display comprehensive summary

### Run with Coverage

```bash
# Generate coverage report
uv run --with pytest python -m pytest tests/ --cov=src --cov-report=html

# View coverage (opens in browser)
open htmlcov/index.html
```

### Run with Additional Options

```bash
# Verbose output with tracebacks
uv run --with pytest python -m pytest tests/ -vv --tb=long

# Stop at first failure
uv run --with pytest python -m pytest tests/ -x

# Show print statements
uv run --with pytest python -m pytest tests/ -s

# Run tests in parallel
uv run --with pytest python -m pytest tests/ -n auto
```

## Test Results

### Expected Output

```
======================== 33 passed, 9 skipped in 2.64s =========================

Passed:
- test_sec_scraper.py: 22 tests
- test_xbrl.py: 11 tests (6 parsing, 3 storage, 2 integration)

Skipped:
- test_xbrl.py: 9 tests (Prefect task mocking - use test_sec_scraper.py)
```

### Result Analysis

- ✓ All core functionality working
- ✓ All data sources integrated correctly
- ✓ Error handling robust
- ✓ Data storage and retrieval validated
- ✓ Parquet compression working
- ⊘ Skipped tests use different mocking strategy (see note below)

### Note on Skipped Tests

Some test_xbrl.py tests for `fetch_company_cik` and `fetch_sec_filing_index` are skipped because:
1. These are Prefect tasks that wrap the underlying functions
2. Mocking Prefect tasks requires special handling
3. Equivalent tests exist in test_sec_scraper.py with proper mocking
4. The actual functions are validated through test_integration.py

## Test Coverage by Component

### SEC EDGAR Integration
- ✓ Company CIK lookup
- ✓ Filing metadata extraction
- ✓ Multiple filing types (10-K, 10-Q, etc.)
- ✓ Error handling for non-existent tickers/filings

### XBRL Data Extraction
- ✓ Financial metrics parsing (revenue, income, assets, liabilities, equity)
- ✓ Financial ratios calculation (current ratio, debt-to-equity)
- ✓ Missing field handling
- ✓ Invalid data handling

### Data Storage
- ✓ Parquet file creation
- ✓ Data integrity validation
- ✓ Snappy compression
- ✓ Multiple record batching

### Prefect Integration
- ✓ Task execution and logging
- ✓ Retry logic
- ✓ Error handling
- ✓ Result validation

## Writing New Tests

### Test Structure

```python
import pytest
from src.module import function_to_test

class TestNewFeature:
    """Test class for new feature."""
    
    def test_feature_success(self):
        """Test successful execution."""
        result = function_to_test(valid_input)
        assert result == expected_value
    
    def test_feature_error(self):
        """Test error handling."""
        with pytest.raises(ExpectedException):
            function_to_test(invalid_input)
```

### Using Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {
        "ticker": "AAPL",
        "cik": "0000320193",
    }

def test_with_fixture(self, sample_data):
    """Test using fixture data."""
    result = process_company(sample_data)
    assert result["ticker"] == "AAPL"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("ticker,expected_cik", [
    ("AAPL", "0000320193"),
    ("MSFT", "0000789019"),
    ("AMZN", "0001018724"),
])
def test_multiple_tickers(self, ticker, expected_cik):
    """Test multiple ticker inputs."""
    result = get_company_cik(ticker)
    assert result == expected_cik
```

## Troubleshooting

### Tests fail with "No module named pytest"

```bash
# Install test dependencies
uv sync
# or with pip
pip install -e ".[dev]"
```

### Import errors in tests

Ensure package is installed in development mode:

```bash
cd /Users/conordonohue/Desktop/TechStack
uv sync
# or
pip install -e .
```

### Prefect server won't start

```bash
# Clean up old Prefect state
uv run python -m prefect config set PREFECT_HOME=/tmp/prefect-test
uv run python -m prefect server start
```

### Tests timeout

Increase timeout in task decorators if network is slow:

```python
@task(retries=3, retry_delay_seconds=10)
def my_task():
    pass
```

### Mock not working

For Prefect tasks, use:

```python
from unittest.mock import patch

# Patch at the import location
@patch("src.module.function_to_mock")
def test_with_prefect_task(mock_fn):
    mock_fn.return_value = {"mocked": "value"}
    # Now the task will use the mock
```

## Performance

### Execution Times

- Full test suite: ~2.6 seconds
- Unit tests only: ~0.4 seconds
- With Prefect overhead: ~35-40 seconds total
- Coverage report generation: ~5 seconds additional

### Optimization Tips

1. Run specific tests during development
2. Use `-x` flag to stop at first failure
3. Skip coverage during active development
4. Run Prefect tests only before commits

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - name: Run Tests
        run: uv run --with pytest python -m pytest tests/ -v
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

1. ✓ Always use temporary directories for file I/O
2. ✓ Mock external API calls to avoid rate limits
3. ✓ Use descriptive test names (test_<feature>_<scenario>)
4. ✓ Organize tests into logical classes by functionality
5. ✓ Keep tests fast by avoiding unnecessary sleep/delays
6. ✓ Use parametrized tests for multiple input variations
7. ✓ Test both success and failure paths
8. ✓ Validate data types and ranges
9. ✓ Document complex test setup in comments
10. ✓ Run full test suite before committing

## Related Documentation

- [README.md](README.md) - Project overview and quick start
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines
- [pyproject.toml](pyproject.toml) - Project dependencies

## Next Steps

- [ ] Add performance benchmarking tests
- [ ] Implement end-to-end tests with real SEC API (separate test suite)
- [ ] Add stress tests for large data batches
- [ ] Create integration tests for database backend
- [ ] Add visual regression tests for reports
